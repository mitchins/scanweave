#!/usr/bin/env python3
"""Independent checks for the M1-D synthetic donor-repair PDF evidence."""
import json
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
import pypdfium2 as pdfium
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "qualification/evidence/m1d_reconstruction"
FIXTURE = ROOT / "qualification/fixtures/m1d_damage"
TRUTH = ROOT / "qualification/evaluator/m1d_damage_ground_truth.png"


def run(argv, env=None):
    return subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=env).stdout


def mask_iou(a, b):
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / max(1, union))


def render(pdf, output):
    run(["pdftoppm", "-f", "1", "-singlefile", "-r", "300", "-png", str(pdf), str(output)])
    return np.asarray(Image.open(str(output) + ".png").convert("L"))


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    faithful = EVIDENCE / "faithful.pdf"
    clearscan = EVIDENCE / "clearscan.pdf"
    source_path = EVIDENCE / "source.png"
    assert faithful.exists() and clearscan.exists() and source_path.exists()
    assert TRUTH.exists(), "run qualification/experiments/m1d_reconstruction_fixture.py first"

    source = np.asarray(Image.open(source_path).convert("L"))
    truth = np.asarray(Image.open(TRUTH).convert("L"))
    faithful_render = render(faithful, EVIDENCE / "faithful-render")
    clear_render = render(clearscan, EVIDENCE / "clearscan-render")
    positions = json.loads((FIXTURE / "positions.json").read_text())
    target = next(o for o in positions["observations"] if o["id"] == "s00")
    x0, y0, x1, y1 = map(int, target["bbox"])
    damaged_mask = source[y0:y1, x0:x1] < 128
    pristine_mask = truth[y0:y1, x0:x1] < 128
    repaired_mask = clear_render[y0:y1, x0:x1] < 128
    representative = next(o for o in positions["observations"] if o["id"] == "s02")
    dx0, dy0, dx1, dy1 = map(int, representative["bbox"])
    donor_crop = Image.fromarray(source[dy0:dy1, dx0:dx1]).resize(
        (x1-x0, y1-y0), Image.Resampling.LANCZOS)
    donor_mask = np.asarray(donor_crop) < 128
    faithful_mask = faithful_render[y0:y1, x0:x1] < 128
    source_crop = source[y0:y1, x0:x1]
    faithful_source_iou = mask_iou(faithful_mask, source_crop < 128)
    clear_source_iou = mask_iou(repaired_mask, source_crop < 128)
    damaged_iou = mask_iou(damaged_mask, pristine_mask)
    donor_iou = mask_iou(donor_mask, pristine_mask)
    repaired_iou = mask_iou(repaired_mask, pristine_mask)
    assert faithful_source_iou > clear_source_iou, "faithful output does not retain the damaged source shape"
    assert repaired_iou > damaged_iou, (damaged_iou, repaired_iou)

    report_path = EVIDENCE / "reconstruction.json"
    report = json.loads(report_path.read_text())
    reconstruction = report["reconstruction"]
    repaired = [o for o in reconstruction["occurrences"] if o["repaired"]]
    assert len(repaired) == 1 and repaired[0]["symbol_id"] == "s00"
    assert repaired[0]["text"] == "e"
    control_ids = {f"s{i:02}" for i in range(12, 27)}
    assert all(not o["repaired"] for o in reconstruction["occurrences"]
               if o["symbol_id"] in control_ids)
    primary = next(p for p in reconstruction["prototypes"]
                   if "s02" in p["members"])
    assert not control_ids.intersection(primary["members"]), "negative controls contaminated primary prototype"

    import sys
    sys.path.insert(0, str(ROOT / "qualification"))
    from tools_env import ots_bin, qpdf_bin, qpdf_env
    qpdf_output = {name: run([qpdf_bin(), "--check", str(EVIDENCE / f"{name}.pdf")], env=qpdf_env()).strip()
                   for name in ("faithful", "clearscan")}
    ots_out = EVIDENCE / "font-sanitized.ttf"
    ots_output = run([ots_bin(), str(EVIDENCE / "font.ttf"), str(ots_out)]).strip()
    font = TTFont(str(EVIDENCE / "font.ttf"), recalcBBoxes=False, recalcTimestamp=False)
    font_ok = all(tag in font for tag in ("cmap", "glyf", "head", "hhea", "hmtx", "maxp"))
    assert font_ok
    font.close()

    texts = {}
    native_search = {}
    for name in ("faithful", "clearscan"):
        doc = pdfium.PdfDocument(str(EVIDENCE / f"{name}.pdf"))
        page = doc[0]
        textpage = page.get_textpage()
        texts[name] = textpage.get_text_range()
        search = textpage.search("e", match_case=False, match_whole_word=False)
        native_search[name] = bool(search.get_next())
        assert native_search[name]
        assert all(ch in texts[name] for ch in ("6", "8", "0", "O"))
        doc.close()
    assert texts["faithful"] == texts["clearscan"], "restoration changed extracted OCR text"
    poppler_text = {name: run(["pdftotext", str(EVIDENCE / f"{name}.pdf"), "-"])
                    for name in ("faithful", "clearscan")}
    assert "e" in poppler_text["faithful"] and "e" in poppler_text["clearscan"]
    assert source_path.stat().st_size > 0
    coverage = report["coverage"]["text_ink_px_vector"] / max(1, report["coverage"]["text_ink_px_total"])
    result = {
        "observations": len(reconstruction["observations"]),
        "prototypes": len(reconstruction["prototypes"]),
        "repaired_occurrences": len(repaired),
        "repaired_symbols": [o["symbol_id"] for o in repaired],
        "false_substitutions": sorted(control_ids.intersection(
            o["symbol_id"] for o in repaired)),
        "damaged_vs_pristine_binary_iou": damaged_iou,
        "selected_prototype_vs_pristine_binary_iou": donor_iou,
        "reconstructed_vs_pristine_binary_iou": repaired_iou,
        "faithful_output_vs_damaged_source_binary_iou": faithful_source_iou,
        "clearscan_output_vs_damaged_source_binary_iou": clear_source_iou,
        "vector_ink_coverage": coverage,
        "faithful_pdf_bytes": faithful.stat().st_size,
        "clearscan_pdf_bytes": clearscan.stat().st_size,
        "embedded_font_bytes": (EVIDENCE / "font.ttf").stat().st_size,
        "fonttools_valid": font_ok,
        "ots_sanitizer": ots_output,
        "qpdf": qpdf_output,
        "native_pdfium_search_e": native_search,
        "poppler_text": poppler_text,
        "faithful_and_clearscan_differ": faithful.read_bytes() != clearscan.read_bytes(),
    }
    report["evaluation"] = result
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
