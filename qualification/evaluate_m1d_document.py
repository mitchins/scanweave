#!/usr/bin/env python3
"""Matched-renderer qualification for the 12-page cross-page repair proof."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
import pypdfium2 as pdfium
from fontTools.ttLib import TTFont

CLEARSCAN_PDF = 'clearscan.pdf'
FAITHFUL_PDF = 'faithful.pdf'
TRUTH_PDF = 'truth.pdf'
DOCUMENT_DONOR_PREFIX = '__doc_donor:'
FONT_TTF = 'font.ttf'


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "qualification/fixtures/m1d_document"
EVIDENCE = ROOT / "qualification/evidence/m1d_document"


def run(argv, env=None):
    return subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=env).stdout.strip()


def iou(a, b):
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / max(1, union))


def render(pdf, stem, dpi):
    run(["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-r", str(dpi),
         "-png", str(pdf), str(stem)])
    return np.asarray(Image.open(str(stem) + ".png").convert("L"))


def render_all(pdf, stem, dpi, pages):
    run(["pdftoppm", "-f", "1", "-l", str(pages), "-r", str(dpi),
         "-png", str(pdf), str(stem)])
    return [np.asarray(Image.open(f"{stem}-{i:02}.png").convert("L"))
            for i in range(1, pages + 1)]


def main():
    results = {}
    for dpi in (300, 600):
        folder = EVIDENCE / f"dpi{dpi}"
        manifest = json.loads((FIXTURE / f"document-{dpi}.json").read_text())
        page0 = manifest["pages"][0]
        source = np.asarray(Image.open(ROOT / page0["image"]).convert("L"))
        truth_raster = np.asarray(Image.open(ROOT / page0["truth_image"]).convert("L"))
        reports = {name: json.loads((folder / f"{name}-report.json").read_text())
                   for name in ("clearscan", "faithful")}
        clear_pages = render_all(folder / CLEARSCAN_PDF, folder / "clearscan-render", dpi, 12)
        faithful_pages = render_all(folder / FAITHFUL_PDF, folder / "faithful-render", dpi, 12)
        truth_pages = render_all(folder / TRUTH_PDF, folder / "truth-render", dpi, 12)
        baseline_pages = render_all(folder / "raster-baseline.pdf", folder / "raster-render", dpi, 12)
        # Independent PDFium renders at output resolution and 4x zoom validate
        # that the outlines survive another renderer and remain vector-sharp.
        pdfium_clear_doc = pdfium.PdfDocument(str(folder / CLEARSCAN_PDF))
        pdfium_truth_doc = pdfium.PdfDocument(str(folder / TRUTH_PDF))
        pdfium_clear = np.asarray(
            pdfium_clear_doc[0].render(scale=dpi / 72).to_pil().convert("L")
        )
        pdfium_truth = np.asarray(
            pdfium_truth_doc[0].render(scale=dpi / 72).to_pil().convert("L")
        )
        pdfium_zoom = np.asarray(
            pdfium_clear_doc[0].render(scale=4 * dpi / 72).to_pil().convert("L")
        )
        pdfium_zoom_truth = np.asarray(
            pdfium_truth_doc[0].render(scale=4 * dpi / 72).to_pil().convert("L")
        )
        Image.fromarray(pdfium_clear).save(folder / "pdfium-clearscan-render.png")
        Image.fromarray(pdfium_zoom).save(folder / "pdfium-clearscan-zoom4x.png")
        pdfium_clear_doc.close()
        pdfium_truth_doc.close()
        source_page = clear_pages[0]
        faithful_page = faithful_pages[0]
        truth_page = truth_pages[0]
        baseline_page = baseline_pages[0]
        rec = reports["clearscan"]["page_reports"][0]["reconstruction"]
        repaired = [o for o in rec["occurrences"] if o["repaired"]]
        observations_by_id = {
            (page["page_id"], observation["id"]): observation
            for page in manifest["pages"] for observation in page["observations"]
        }
        false_substitutions = []
        unsafe_font_mixes = []
        for page in reports["clearscan"]["page_reports"]:
            prototypes_by_id = {
                prototype["prototype_id"]: prototype
                for prototype in page["reconstruction"]["prototypes"]
            }
            for prototype in page["reconstruction"]["prototypes"]:
                styles = set()
                for member in prototype["members"]:
                    parts = member.removeprefix(DOCUMENT_DONOR_PREFIX).split(":", 1)
                    if len(parts) == 2 and (parts[0], parts[1]) in observations_by_id:
                        styles.add(observations_by_id[(parts[0], parts[1])]["source"])
                if len(styles) > 1:
                    unsafe_font_mixes.append({"prototype": prototype["prototype_id"], "styles": sorted(styles)})
            for occurrence in page["reconstruction"]["occurrences"]:
                if not (occurrence["repaired"] or occurrence["reused"]):
                    continue
                prototype = prototypes_by_id.get(occurrence["prototype_id"])
                if not prototype:
                    false_substitutions.append({"symbol": occurrence["symbol_id"], "reason": "missing_prototype"})
                    continue
                rep = prototype["representative_symbol_id"].removeprefix(DOCUMENT_DONOR_PREFIX).split(":", 1)
                donor = observations_by_id.get(tuple(rep)) if len(rep) == 2 else None
                if not donor or donor["text"] != occurrence["text"]:
                    false_substitutions.append({"symbol": occurrence["symbol_id"], "reason": "identity_mismatch"})
                elif donor["source"] != next(
                    (o["source"] for p in manifest["pages"] for o in p["observations"]
                     if o["id"] == occurrence["symbol_id"]), donor["source"]
                ):
                    false_substitutions.append({"symbol": occurrence["symbol_id"], "reason": "style_mismatch"})
        accepted = sorted(["e", "a"] if dpi == 300 else ["e", "a", "8"])
        assert sorted(o["text"] for o in repaired) == accepted
        assert len(repaired) == len(accepted)
        proto_by_id = {p["prototype_id"]: p for p in rec["prototypes"]}
        glyphs = {}
        pdfium_glyphs = {}
        for target_index, target_id in enumerate(("p00-s00", "p00-s01", "p00-s02")):
            occ = next(o for o in rec["occurrences"] if o["symbol_id"] == target_id)
            target = next(o for o in page0["observations"] if o["id"] == target_id)
            x0, y0, x1, y1 = map(int, target["bbox"])
            region = (slice(y0, y1), slice(x0, x1))
            pristine = truth_page[region] < 128
            # Keep direct raster measurements separate from end-to-end PDF
            # measurements. Comparing raw PIL pixels to a PDF renderer mixed
            # two sampling pipelines and produced a false fallback anomaly.
            raw_source_iou = iou(source[region] < 128, truth_raster[region] < 128)
            pdf_source_iou = iou(baseline_page[region] < 128, pristine)
            glyph = {
                "direct_scan_vs_pristine_raster_iou": raw_source_iou,
                "A1_raster_pdf_vs_A0_pristine_pdf_iou": pdf_source_iou,
                "A2_faithful_pdf_vs_A0_pristine_pdf_iou": iou(faithful_page[region] < 128, pristine),
                "A3_best_donor_pdf_vs_A0_pristine_pdf_iou": iou(source_page[region] < 128, pristine),
                "A2_faithful_pdf_vs_A1_raster_pdf_iou": iou(faithful_page[region] < 128, baseline_page[region] < 128),
                "A3_improvement_vs_A1": iou(source_page[region] < 128, pristine) - pdf_source_iou,
            }
            if occ["repaired"]:
                proto = proto_by_id[occ["prototype_id"]]
                rep = proto["representative_symbol_id"].removeprefix(DOCUMENT_DONOR_PREFIX)
            else:
                rep = f"p01:p01-s{target_index:02}"
            donor_page, donor_id = rep.split(":", 1)
            donor_record = next(p for p in manifest["pages"] if p["page_id"] == donor_page)
            donor_obs = next(o for o in donor_record["observations"] if o["id"] == donor_id)
            dx0, dy0, dx1, dy1 = map(int, donor_obs["bbox"])
            donor = np.asarray(Image.open(ROOT / donor_record["image"]).convert("L"))[dy0:dy1, dx0:dx1]
            donor = np.asarray(Image.fromarray(donor).resize((x1-x0, y1-y0), Image.Resampling.LANCZOS))
            glyph["selected_donor_vs_pristine_iou"] = iou(donor < 128, truth_raster[region] < 128)
            glyph["donor_crop_vs_pristine_raster_iou"] = iou(donor < 128, truth_raster[region] < 128)
            glyph["repair_accepted_by_pristine_eval"] = (
                glyph["A3_best_donor_pdf_vs_A0_pristine_pdf_iou"] > pdf_source_iou
                if occ["repaired"] else glyph["A3_best_donor_pdf_vs_A0_pristine_pdf_iou"] >= pdf_source_iou - 0.01
            )
            glyph["repaired"] = occ["repaired"]
            if occ["repaired"]:
                assert glyph["repair_accepted_by_pristine_eval"], (dpi, occ, glyph)
            assert rep.split(":", 1)[0] != "p00", "repair must use another page's evidence"
            glyphs[occ["text"]] = glyph
            fx0, fy0, fx1, fy1 = (4 * x0, 4 * y0, 4 * x1, 4 * y1)
            pdfium_glyphs[occ["text"]] = {
                "nominal_iou_vs_pristine": iou(
                    pdfium_clear[region] < 128, pdfium_truth[region] < 128
                ),
                "zoom4x_iou_vs_pristine": iou(
                    pdfium_zoom[fy0:fy1, fx0:fx1] < 128,
                    pdfium_zoom_truth[fy0:fy1, fx0:fx1] < 128,
                ),
            }

        # Score repeated, intact occurrences in the exact renderer coordinate
        # system used for the final PDF and its raster baseline.
        reused_metrics = []
        for page_index, page_report in enumerate(reports["clearscan"]["page_reports"]):
            page_fixture = manifest["pages"][page_index]
            src_img = np.asarray(Image.open(ROOT / page_fixture["image"]).convert("L"))
            tru_img = np.asarray(Image.open(ROOT / page_fixture["truth_image"]).convert("L"))
            for occurrence in page_report["reconstruction"]["occurrences"]:
                if not occurrence.get("reused", False):
                    continue
                ob = next(o for o in page_fixture["observations"] if o["id"] == occurrence["symbol_id"])
                ax, ay, bx, by = map(int, ob["bbox"])
                region = (slice(ay, by), slice(ax, bx))
                truth_render_mask = truth_pages[page_index][region] < 128
                reused_metrics.append({
                    "page": page_index,
                    "text": occurrence["text"],
                    "source_vs_pristine_iou": iou(src_img[region] < 128, tru_img[region] < 128),
                    "clearscan_vs_pristine_iou": iou(clear_pages[page_index][region] < 128, truth_render_mask),
                    "raster_vs_pristine_iou": iou(baseline_pages[page_index][region] < 128, truth_render_mask),
                    "similarity": occurrence["similarity"],
                })
        unsafe_reuses = [m for m in reused_metrics
                         if m["clearscan_vs_pristine_iou"] + 0.02 < m["raster_vs_pristine_iou"]]
        # Keep failed qualification visible in the machine-readable result;
        # the reconstruction is experimental and must not be promoted when
        # the matched-renderer appearance gate fails.

        # Protected text is still source-owned on page 1; it never enters the
        # donor pool or vector coverage. OCR text remains identical across modes.
        protected_ids = {f"p00-amount{i:02}" for i in range(7)}
        for report in reports.values():
            page_occ = report["page_reports"][0]["occurrences"]
            assert all(next(o for o in page_occ if o["symbol_id"] == sid)["owner"] == "invisible"
                       for sid in protected_ids)
        assert not any(o["repaired"] for o in reports["clearscan"]["page_reports"][11]["reconstruction"]["occurrences"]
                       if o["symbol_id"] == "p11-s06"), "OCR misrecognition authorized repair"

        texts = {}
        for name in ("faithful", "clearscan"):
            doc = pdfium.PdfDocument(str(folder / f"{name}.pdf"))
            assert len(doc) == 12
            texts[name] = [doc[i].get_textpage().get_text_range() for i in range(12)]
            assert all("".join(text.split()) for text in texts[name])
            assert "c" in texts[name][11]
            doc.close()
        assert ["".join(t.split()) for t in texts["faithful"]] == [
            "".join(t.split()) for t in texts["clearscan"]
        ]
        search = {name: {char: all(bool(pdfium.PdfDocument(str(folder / f"{name}.pdf"))[i]
                       .get_textpage().search(char, match_case=False, match_whole_word=False).get_next())
                       for i in range(12)) for char in ("e", "a", "8")}
                  for name in ("faithful", "clearscan")}

        sys.path.insert(0, str(ROOT / "qualification"))
        from tools_env import ots_bin, qpdf_bin, qpdf_env
        qpdf = {name: run([qpdf_bin(), "--check", str(folder / f"{name}.pdf")], env=qpdf_env())
                for name in ("clearscan", "faithful", "truth", "raster-baseline")}
        ots = run([ots_bin(), str(folder / FONT_TTF), str(folder / "font-sanitized.ttf")])
        font = TTFont(str(folder / FONT_TTF), recalcBBoxes=False, recalcTimestamp=False)
        font_valid = all(tag in font for tag in ("cmap", "glyf", "head", "hhea", "hmtx", "maxp"))
        font.close()
        assert font_valid
        report = reports["clearscan"]
        coverage = report["coverage"]["text_ink_px_vector"] / max(1, report["coverage"]["text_ink_px_total"])
        result = {"dpi": dpi, "pages": 12, "repaired_occurrences": len(repaired),
                  "repaired_characters": sorted(o["text"] for o in repaired), "glyphs": glyphs,
                  "pdfium_independent_render": pdfium_glyphs,
                  "reused_occurrences": len(reused_metrics),
                  "reused_occurrence_mean_pristine_iou": float(np.mean([m["clearscan_vs_pristine_iou"] for m in reused_metrics])) if reused_metrics else None,
                  "reused_occurrences_below_raster_iou_by_0_02": sum(m["clearscan_vs_pristine_iou"] + 0.02 < m["raster_vs_pristine_iou"] for m in reused_metrics),
                  "reused_outline_appearance_gate_passed": bool(reused_metrics) and not unsafe_reuses,
                  "reused_source_mask_ious": [o["source_mask_iou"] for page in reports["clearscan"]["page_reports"]
                                               for o in page["reconstruction"]["occurrences"]
                                               if o.get("decision") == "rejected_unchanged_source_fidelity"],
                  "false_substitutions": false_substitutions,
                  "unsafe_font_mixes": unsafe_font_mixes,
                  "vector_ink_coverage": coverage,
                  "reused_occurrences_unsafe_vs_raster": len(unsafe_reuses),
                  "pdf_bytes": {n: (folder / f"{n}.pdf").stat().st_size for n in ("clearscan", "faithful", "truth", "raster-baseline")},
                  "comparison_arms": {
                      "A0_pristine_oracle": TRUTH_PDF,
                      "A1_degraded_searchable_raster": "raster-baseline.pdf",
                      "A2_existing_faithful": FAITHFUL_PDF,
                      "A3_best_donor": CLEARSCAN_PDF,
                      "A4_evidence_fused": "not implemented; no fusion arm was run",
                      "A5_calibrated_acceptance": "not implemented; auto falls back to A1 at the unchanged 0.98 policy",
                  },
                  "font_bytes": (folder / FONT_TTF).stat().st_size,
                  "compression_vs_faithful_bytes": (folder / FAITHFUL_PDF).stat().st_size - (folder / CLEARSCAN_PDF).stat().st_size,
                  "fonttools_valid": font_valid, "ots": ots, "qpdf": qpdf,
                  "pdfium_text_equal": True, "pdfium_search": {name: all(v.values()) for name,v in search.items()}}
        result["compression_vs_searchable_raster_baseline_bytes"] = (
            result["pdf_bytes"]["raster-baseline"] - result["pdf_bytes"]["clearscan"]
        )
        (folder / "evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
        results[str(dpi)] = result
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
