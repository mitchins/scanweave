#!/usr/bin/env python3
"""Matched-coordinate diagnosis of the 300-DPI local raster fallback."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "qualification"))
from tools_env import qpdf_bin, qpdf_env

FIXTURE = ROOT / "qualification/fixtures/m1d_document/document-300.json"
OUT = ROOT / "qualification/evidence/m1d_document/dpi300"


def iou(a, b):
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / max(1, union))


def main():
    page = json.loads(FIXTURE.read_text())["pages"][0]
    obs = next(o for o in page["observations"] if o["id"] == "p00-s02")
    x0, y0, x1, y1 = map(int, (316, 47, 351, 99))
    src = np.asarray(Image.open(ROOT / page["image"]).convert("RGB"))
    crop = src[y0:y1, x0:x1]
    extracted = []
    with tempfile.TemporaryDirectory(prefix="m1d5-fallback-") as td:
        prefix = str(Path(td) / "im")
        subprocess.run(["pdfimages", "-f", "1", "-l", "1", "-png",
                        str(OUT / "clearscan.pdf"), prefix], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for file in Path(td).glob("im-*.png"):
            arr = np.asarray(Image.open(file).convert("RGB"))
            if arr.shape == crop.shape and np.array_equal(arr, crop):
                extracted.append({"file": file.name, "exact_source_crop": True,
                                  "sha256_rgb": hashlib.sha256(arr.tobytes()).hexdigest()})
        # Inspect decoded page content to confirm the crop's PDF point placement.
        qdf = Path(td) / "clear-qdf.pdf"
        subprocess.run([qpdf_bin(), "--qdf",
                        "--object-streams=disable", str(OUT / "clearscan.pdf"),
                        str(qdf)], check=True, env=qpdf_env(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        content = qdf.read_bytes().decode("latin-1")
        page_match = re.search(r"%% Page 1.*?\nendobj", content, re.S)
        page_block = page_match.group(0) if page_match else ""
        content_ref = re.search(r"/Contents\s+(\d+) 0 R", page_block)
        image_ref = re.search(r"/Im0\s+(\d+) 0 R", page_block)
        content_block = ""
        image_block = ""
        if content_ref and image_ref:
            content_match = re.search(
                rf"(?m)^{content_ref.group(1)} 0 obj\n(.*?)\nendobj", content, re.S
            )
            image_match = re.search(
                rf"(?m)^{image_ref.group(1)} 0 obj\n(.*?)\nendobj", content, re.S
            )
            content_block = content_match.group(1) if content_match else ""
            image_block = image_match.group(1) if image_match else ""
        expected_draw = "q\n8.4 0 0 12.48 75.84 33.84 cm\n/Im0 Do\nQ"
        content_has_transform = expected_draw in content_block
        im0_has_expected_dimensions = bool(
            re.search(r"/Width\s+35\b", image_block)
            and re.search(r"/Height\s+52\b", image_block)
        )
        decoded_im0 = b""
        if image_ref:
            original_id = re.search(
                rf"%% Original object ID: (\d+) 0\n{image_ref.group(1)} 0 obj",
                content,
            )
            if not original_id:
                raise RuntimeError("could not map QDF /Im0 object to its original PDF object")
            decoded_im0 = subprocess.run(
                [qpdf_bin(), f"--show-object={original_id.group(1)}",
                 "--filtered-stream-data", str(OUT / "clearscan.pdf")],
                check=True, env=qpdf_env(), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout

    masks = {}
    for label in ("raster", "faithful", "clearscan", "truth"):
        image = np.asarray(Image.open(OUT / f"{label}-render-01.png").convert("L"))
        masks[label] = image[43:103, 308:359] < 128
    source_mask = np.asarray(Image.open(ROOT / page["image"]).convert("L"))[43:103, 308:359] < 128
    pristine_mask = np.asarray(Image.open(ROOT / page["truth_image"]).convert("L"))[43:103, 308:359] < 128
    # Translation is diagnostic only: the acceptance score retains original placement.
    shifted = masks["clearscan"][1:, :]  # move painted crop up by one output pixel
    target = masks["truth"][:-1, :]
    pdfium_masks = {}
    for label in ("raster-baseline", "clearscan", "truth"):
        doc = pdfium.PdfDocument(str(OUT / f"{label}.pdf"))
        image = np.asarray(doc[0].render(scale=300 / 72).to_pil().convert("L"))
        pdfium_masks[label] = image[43:103, 308:359] < 128
        doc.close()
    result = {
        "case": "p00-s02 / OCR '8' / 300 DPI",
        "source_patch_bbox_px": [x0, y0, x1, y1],
        "pdf_patch_bbox_pt": [75.84, 11.28, 84.24, 23.76],
        "pdf_transform_found": content_has_transform,
        "transform_bound_to_page1_im0": content_has_transform,
        "page1_im0_dimensions_match_crop": im0_has_expected_dimensions,
        "embedded_image_matches_source_crop": bool(extracted),
        "referenced_im0_decoded_pixels_match_source_crop": decoded_im0 == crop.tobytes(),
        "embedded_image_matches": extracted,
        "raw_scan_vs_pristine_raster_iou": iou(source_mask, pristine_mask),
        "poppler_pdf_vs_A0_iou": {name: iou(mask, masks["truth"])
                                   for name, mask in masks.items()},
        "pdfium_pdf_vs_A0_iou": {name: iou(mask, pdfium_masks["truth"])
                                 for name, mask in pdfium_masks.items()},
        "clearscan_to_pristine_after_diagnostic_up_one_px": iou(shifted, target),
        "source_patch_is_intact_in_pdf": bool(extracted) and decoded_im0 == crop.tobytes() and content_has_transform and im0_has_expected_dimensions,
        "interpretation": "the oracle score mixes no representations here; the remaining gap is in local XObject rasterization/placement relative to whole-page raster rendering; registration correction is diagnostic only",
    }
    (OUT / "fallback-diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["source_patch_is_intact_in_pdf"]:
        raise SystemExit("local fallback patch did not match source bytes or expected transform")


if __name__ == "__main__":
    main()
