#!/usr/bin/env python3
"""Verify M1-E immutable inputs and frozen Adobe denominators."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "qualification/competitors/adobe_xi"
manifest = json.loads((BASE / "results/run-manifest.json").read_text())
assert manifest["scanweave_head"] == "28c91b12a7212f0ee94daca3bef8c31e4c8044f1"
checks = {}
def verify(rel, expected):
    data = (BASE / rel).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    checks[rel] = {"expected_sha256": expected, "actual_sha256": actual, "bytes": len(data), "match": actual == expected}
    assert actual == expected, f"frozen evidence changed: {rel}"
for key in ("dpi300", "dpi600", "dpi300-12"):
    item = manifest["inputs"][key]
    verify(item["path"], item["sha256"])
for rel, expected in {
    "results/dpi300/adobe-clearscan-run1.pdf": "6d2150c05e1102cd90a3cdc48f87aeff08af118bf63a5390a787f909589258fb",
    "results/dpi600/adobe-clearscan-run1.pdf": "86e26797a02d2e6688c38f8cf6c3f668842da854bcdc177437ce002b3382e6e2",
    "results/dpi300-12/adobe-clearscan.pdf": "3482de33d73dce352bd5ba9b29afc0f848a1400f4fee43fe3b432c0656246e2d",
}.items():
    verify(rel, expected)
out = {"manifest_sha256": hashlib.sha256((BASE / "results/run-manifest.json").read_bytes()).hexdigest(),
       "comparison_results_sha256": hashlib.sha256((BASE / "results/comparison-results.json").read_bytes()).hexdigest(),
       "scanweave_head": manifest["scanweave_head"], "local_commits_ahead": manifest["local_commits_ahead"],
       "checks": checks}
target = Path(__file__).resolve().parent / "results/preflight.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
