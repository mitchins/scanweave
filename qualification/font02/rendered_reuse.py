"""Read-only FONT-02 rendered-substitution evaluator; never used by conversion.

Source decisions and rendered arrays must be frozen before this evaluator reads
pristine images. Face labels are deliberately absent from the quality decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def coverage_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict:
    """Measure equal-coordinate coverage, normalized by reference ink mass."""
    if reference.shape != candidate.shape or reference.ndim != 2:
        raise ValueError("Coverage arrays must have identical two-dimensional geometry")
    if not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise ValueError("Coverage must be finite")
    mass = max(1.0, float(reference.sum()))
    a, b = reference > 0.5, candidate > 0.5
    return {
        "mse": float(np.square(reference - candidate).sum() / mass),
        "iou": float((a & b).sum() / max(1, (a | b).sum())),
        "area": float(candidate.sum()) / mass - 1,
    }


def renderer_outcome(baseline: dict, candidate: dict) -> dict:
    """Apply the protocol frozen before oracle scoring; do not tune to results."""
    mse_increase = candidate["mse"] - baseline["mse"]
    iou_decline = baseline["iou"] - candidate["iou"]
    area_increase = abs(candidate["area"]) - abs(baseline["area"])
    return {
        "safe": mse_increase <= 0.002 and iou_decline <= 0.01 and area_increase <= 0.02,
        "material": mse_increase > 0.02 or iou_decline > 0.05,
    }


def verify_freeze(root: Path, split: str) -> dict:
    frozen = json.loads((root / f"{split}-pre-oracle-freeze.json").read_text())
    names = {
        "source-decisions.json": "decision_sha256",
        "rendered-coverage.npz": "coverage_sha256",
    }
    for suffix, key in names.items():
        actual = hashlib.sha256((root / f"{split}-{suffix}").read_bytes()).hexdigest()
        if actual != frozen[key]:
            raise ValueError(f"Frozen artifact changed: {split}-{suffix}")
    return frozen


def pristine_region(corpus: Path, identifier: str, row: dict, bounds: list) -> np.ndarray:
    """Place evaluator-only pristine samples without registration or resizing."""
    x, y, right, bottom = bounds
    px, py, qx, qy = map(int, row["public_bbox"])
    with Image.open(corpus / "oracle" / f"{identifier}-pristine.png") as image:
        samples = np.asarray(image.convert("L"), dtype=float)
    if samples.shape != (qy - py, qx - px):
        raise ValueError("Pristine samples do not match public source geometry")
    if not (x <= px <= qx <= right and y <= py <= qy <= bottom):
        raise ValueError("Inspection region must contain the complete public frame")
    reference = np.zeros((bottom - y, right - x))
    reference[py - y : qy - y, px - x : qx - x] = 1 - samples / 255
    return reference


def score_record(record: dict, rows: dict, maps, corpus: Path) -> dict:
    target, donor, engine = record["target"], record["donor"], record["renderer"]
    pristine = pristine_region(corpus, target, rows[target], record["bounds"])
    baseline = coverage_metrics(pristine, maps[f"{engine}-{target}-baseline"])
    candidate = coverage_metrics(pristine, maps[f"{engine}-{target}-{donor}"])
    return {
        "renderer": engine,
        "source_gate": record["source_gate"],
        **renderer_outcome(baseline, candidate),
        "baseline": baseline,
        "candidate": candidate,
    }


def summarize_pair(target: str, donor: str, records: list) -> dict:
    if sorted(r["renderer"] for r in records) != ["pdfium", "poppler"]:
        raise ValueError("Each substitution requires one result from each renderer")
    return {
        "target": target,
        "donor": donor,
        "source_accepted": all(r["source_gate"] for r in records),
        "safe": all(r["safe"] for r in records),
        "material": any(r["material"] for r in records),
        "renderers": records,
    }


def evaluate(root: Path, corpus: Path, split: str) -> dict:
    frozen = verify_freeze(root, split)
    decisions = json.loads((root / f"{split}-source-decisions.json").read_text())
    rows = {
        row["id"]: row
        for row in json.loads((root / f"{split}-sources.json").read_text())["records"]
    }
    grouped = {}
    with np.load(root / f"{split}-rendered-coverage.npz", allow_pickle=False) as maps:
        for record in decisions["records"]:
            key = record["target"], record["donor"]
            grouped.setdefault(key, []).append(score_record(record, rows, maps, corpus / split))
    pairs = [summarize_pair(t, d, rs) for (t, d), rs in grouped.items()]
    accepted = [pair for pair in pairs if pair["source_accepted"]]
    return {
        "frozen_inputs": frozen,
        "summary": {
            "pairs": len(pairs),
            "accepted": len(accepted),
            "safe": sum(p["safe"] for p in accepted),
            "material": sum(p["material"] for p in accepted),
            "ambiguous": sum(not p["safe"] and not p["material"] for p in accepted),
        },
        "pairs": pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", choices=["validation", "test"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.artifacts, args.corpus, args.split)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
