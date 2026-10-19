#!/usr/bin/env python3
"""Measure a ClearScan product PDF against the preserved M1-G synthetic oracle."""
import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from PIL import ImageDraw


def run(args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout


def iou(a, b):
    ma, mb = a < 170, b < 170
    union = np.logical_or(ma, mb).sum()
    return float(np.logical_and(ma, mb).sum() / max(1, union))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, required=True)
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--oracle-dir", type=Path, required=True)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    report = json.loads(a.report.read_text())
    manifest = json.loads((a.input_dir / "document.json").read_text())
    poppler_dir = a.out / "poppler"
    pdfium_dir = a.out / "pdfium"
    poppler_dir.mkdir(exist_ok=True)
    pdfium_dir.mkdir(exist_ok=True)
    run(["pdftoppm", "-r", str(a.dpi), "-png", str(a.pdf), str(poppler_dir / "page")])

    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(a.pdf))
    pdfium_text = "".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    pdfium_images = []
    for i in range(len(doc)):
        im = doc[i].render(scale=a.dpi / 72).to_pil().convert("L")
        im.save(pdfium_dir / f"page-{i + 1}.png")
        pdfium_images.append(np.asarray(im))
    doc.close()

    by_char = defaultdict(lambda: defaultdict(list))
    all_glyphs = []
    replaced = set()
    expected_ocr, expected_truth = [], []
    for pi, page in enumerate(manifest["pages"]):
        # Source asset names are authoritative in the bundle manifest.
        src_name = next(x["asset_path"] for x in manifest["sources"] if x["source_id"] == page["source_id"])
        src = np.asarray(Image.open(a.input_dir / src_name).convert("L"))
        truth_doc = json.loads((a.oracle_dir / f"page{pi:02}.truth.json").read_text())
        truth = np.asarray(Image.open(a.oracle_dir / f"page{pi:02}.png").convert("L"))
        ocr = json.loads((a.input_dir / page["ocr_page_path"]).read_text())
        expected_ocr.extend(s["text"] for s in ocr["spans"])
        records = report["page_reports"][pi]["reconstruction"]["occurrences"]
        replaced.update(x["symbol_id"] for x in records if x.get("repaired") or x.get("reused"))
        pop = np.asarray(Image.open(poppler_dir / f"page-{pi + 1}.png").convert("L"))
        py = pdfium_images[pi]
        for rec in truth_doc["records"]:
            x0, y0, x1, y1 = [int(v) for v in rec["bbox"]]
            sl = (slice(max(0, y0 - 4), min(pop.shape[0], y1 + 4)),
                  slice(max(0, x0 - 4), min(pop.shape[1], x1 + 4)))
            before, after, after_py = iou(src[sl], truth[sl]), iou(pop[sl], truth[sl]), iou(py[sl], truth[sl])
            glyph = {"page": page["page_id"], "symbol_id": rec["id"], "text": rec["text"],
                     "source_iou": before, "poppler_iou": after, "pdfium_iou": after_py,
                     "replaced": rec["id"] in replaced}
            all_glyphs.append(glyph)
            for key, value in (("source", before), ("poppler", after), ("pdfium", after_py)):
                by_char[rec["text"]][key].append(value)
            if glyph["replaced"]:
                by_char[rec["text"]]["replaced_poppler"].append(after)
                by_char[rec["text"]]["replaced_pdfium"].append(after_py)
            expected_truth.append(rec["text"])

    pdftotext = run(["pdftotext", str(a.pdf), "-"])
    norm = lambda s: re.sub(r"\s+", "", s)
    per_char = {ch: {k: float(np.mean(v)) for k, v in vals.items()}
                | {"n": len(vals["source"]), "replaced_n": len(vals.get("replaced_poppler", []))}
                for ch, vals in sorted(by_char.items())}
    crops_dir = a.out / "crops_800"
    crops_dir.mkdir(exist_ok=True)
    sample_by_char = {}
    for glyph in all_glyphs:
        if glyph["replaced"] and glyph["text"] not in sample_by_char:
            sample_by_char[glyph["text"]] = glyph
    sample_pages = {p["page_id"]: i for i, p in enumerate(manifest["pages"])}
    for ch, glyph in sample_by_char.items():
        pi = sample_pages[glyph["page"]]
        truth = np.asarray(Image.open(a.oracle_dir / f"page{pi:02}.png").convert("L"))
        source_name = next(x["asset_path"] for x in manifest["sources"] if x["source_id"] == manifest["pages"][pi]["source_id"])
        src = np.asarray(Image.open(a.input_dir / source_name).convert("L"))
        rec = next(r for r in json.loads((a.oracle_dir / f"page{pi:02}.truth.json").read_text())["records"] if r["id"] == glyph["symbol_id"])
        x0, y0, x1, y1 = [int(v) for v in rec["bbox"]]
        box = (max(0, x0 - 4), max(0, y0 - 4), min(src.shape[1], x1 + 4), min(src.shape[0], y1 + 4))
        panels = [Image.fromarray(img[box[1]:box[3], box[0]:box[2]]).resize(((box[2]-box[0])*8, (box[3]-box[1])*8), Image.Resampling.NEAREST)
                  for img in (src, truth,
                              np.asarray(Image.open(poppler_dir / f"page-{pi + 1}.png").convert("L")),
                              pdfium_images[pi])]
        width = max(p.width for p in panels)
        canvas = Image.new("L", (width, sum(p.height for p in panels) + 4 * 20), 255)
        draw = ImageDraw.Draw(canvas)
        y = 0
        for label, panel in zip(("Source", "Pristine", "Poppler", "PDFium"), panels):
            draw.text((0, y), label, fill=0)
            y += 20
            canvas.paste(panel, (0, y))
            y += panel.height
        canvas.save(crops_dir / f"{ord(ch):04x}-{ch}.png")
    output = {
        "dpi": a.dpi,
        "pdf": str(a.pdf),
        "pdf_sha256": hashlib.sha256(a.pdf.read_bytes()).hexdigest(),
        "pdf_bytes": a.pdf.stat().st_size,
        "pages": len(manifest["pages"]),
        "observations": sum(len(p["reconstruction"]["observations"]) for p in report["page_reports"]),
        "canonical_prototypes_page_sum": sum(len(p["reconstruction"]["prototypes"]) for p in report["page_reports"]),
        "accepted_replacements": len(replaced),
        "occurrences": len(all_glyphs),
        "vector_ink_pixels": report["coverage"]["text_ink_px_vector"],
        "text_ink_pixels": report["coverage"]["text_ink_px_total"],
        "vector_ink_fraction": report["coverage"]["text_ink_px_vector"] / max(1, report["coverage"]["text_ink_px_total"]),
        "raster_bytes": report["raster_encoded_bytes"],
        "font_bytes": report["font_bytes"],
        "image_xobjects": report["image_xobjects"],
        "image_references": report["image_references"],
        "serialized_bytes": report["pdf_bytes"],
        "searchable_raster_bytes": next(c["pdf_bytes"] for c in report["candidates"] if c["name"] == "raster_baseline"),
        "raster_ink_pixels_suppressed": sum(p.get("raster_ink_pixels_suppressed", 0) for p in report["page_reports"]),
        "antialias_fringe_pixels_suppressed": sum(p.get("antialias_fringe_pixels_suppressed", 0) for p in report["page_reports"]),
        "runtime_ms": report["stage_timings"]["total_ms"],
        "peak_rss_kb": None,
        "search": {
            "pdftotext_chars": len(pdftotext), "pdfium_chars": len(pdfium_text),
            "matches_ocr_poppler": norm(pdftotext) == norm("".join(expected_ocr)),
            "matches_ocr_pdfium": norm(pdfium_text) == norm("".join(expected_ocr)),
        },
        "mean_glyph_iou": {k: float(np.mean([g["source_iou" if k == "source" else k + "_iou"] for g in all_glyphs]))
                            for k in ("source", "poppler", "pdfium")},
        "per_character": per_char,
        "glyphs": all_glyphs,
    }
    (a.out / "metrics.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k not in ("glyphs", "per_character")}, indent=2))


if __name__ == "__main__":
    main()
