#!/usr/bin/env python3
"""Compact public-PDF resource accounting for the M1-F ablation set."""
import json
from pathlib import Path
from measure_pdf import inspect
ROOT = Path(__file__).resolve().parents[3]
FILES = {
    "A_baseline_clearscan_300": "qualification/competitors/adobe_xi/results/dpi300/scanweave-clearscan.pdf",
    "C_gray_reuse_clearscan_300": "qualification/experiments/m1f/results/dpi300/clearscan/gray.pdf",
    "A_baseline_clearscan_600": "qualification/competitors/adobe_xi/results/dpi600/scanweave-clearscan.pdf",
    "C_gray_reencoded_clearscan_600": "qualification/experiments/m1f/results/dpi600/clearscan-grayscale-reencoded.pdf",
    "A_baseline_faithful_12": "qualification/competitors/adobe_xi/results/dpi300-12/scanweave-faithful.pdf",
    "B_reuse_faithful_12": "qualification/experiments/m1f/results/dpi300-12/faithful/reuse.pdf",
    "Adobe_ClearScan_300": "qualification/competitors/adobe_xi/results/dpi300/adobe-clearscan-run1.pdf",
    "Adobe_ClearScan_600": "qualification/competitors/adobe_xi/results/dpi600/adobe-clearscan-run1.pdf",
    "Adobe_ClearScan_12": "qualification/competitors/adobe_xi/results/dpi300-12/adobe-clearscan.pdf",
}
keys = ["path", "sha256", "pdf_bytes", "pages", "image_uses", "unique_image_objects", "unique_encoded_resource_keys", "unique_decoded_sample_keys", "image_stream_bytes", "unique_encoded_image_stream_bytes", "duplicate_encoded_image_stream_bytes", "font_program_stream_bytes", "font_references", "content_streams", "content_stream_bytes", "remaining_overhead_bytes", "extracted_text_sha256"]
results = {}
for name, rel in FILES.items():
    data = inspect(ROOT / rel)
    results[name] = {k: data[k] for k in keys}
    results[name]["path"] = rel
    results[name]["image_color_models"] = sorted({x["colorspace"] for x in data["images"]})
    results[name]["image_encoding_filters"] = sorted({x["filter"] for x in data["images"]})
out = ROOT / "qualification/experiments/m1f/results/measurement-summary.json"
out.write_text(json.dumps(results, indent=2) + "\n")
print(out)
