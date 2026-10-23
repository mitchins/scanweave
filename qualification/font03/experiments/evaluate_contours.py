"""Evaluator-only native contour, IoU and ink-area diagnostics after decisions."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path("qualification/font03/local")


def contour_error(reference, candidate):
    """Symmetric boundary distances; empty contours explicitly remain unresolved."""
    a, b = reference > 0.5, candidate > 0.5
    a = a ^ ndimage.binary_erosion(a, structure=np.ones((3, 3)))
    b = b ^ ndimage.binary_erosion(b, structure=np.ones((3, 3)))
    if not a.any() or not b.any():
        return None
    distances = np.concatenate(
        (ndimage.distance_transform_edt(~a)[b], ndimage.distance_transform_edt(~b)[a])
    )
    return dict(mean=float(distances.mean()), p95=float(np.quantile(distances, 0.95)))


def evaluate(split):
    folder = ROOT / "affine-refinement"
    frozen = json.loads((folder / f"{split}-source-freeze.json").read_text())
    source_record = folder / f"{split}-source-rendered.json"
    if (
        hashlib.sha256(source_record.read_bytes()).hexdigest()
        != frozen["decisions_sha256"]
    ):
        raise RuntimeError("Source decision binding mismatch")
    arrays = folder / f"{split}-native-coverages.npz"
    if hashlib.sha256(arrays.read_bytes()).hexdigest() != frozen["coverage_sha256"]:
        raise RuntimeError("Native render binding mismatch")
    accepted = {
        r["target"]
        for r in json.loads((folder / f"{split}-final-decisions.json").read_text())[
            "decisions"
        ]
        if r["accepted"]
    }
    records = json.loads((folder / f"{split}-evaluated.json").read_text())["records"]
    rows = {
        r["id"]: r
        for r in json.loads((ROOT / f"{split}-sources.json").read_text())["records"]
    }
    maps = np.load(arrays)
    results = []
    for record in records:
        if record["target"] not in accepted or record["arm"] not in ["A", "C"]:
            continue
        row = rows[record["target"]]
        left, top, right, bottom = record["bounds"]
        x, y, xx, yy = row["public_bbox"]
        pristine = np.zeros((bottom - top, right - left))
        path = (
            Path("qualification/font01/local/corpus-font01-v1")
            / split
            / "oracle"
            / f'{record["target"]}-pristine.png'
        )
        with Image.open(path) as image:
            pristine[y - top : yy - top, x - left : xx - left] = (
                1 - np.asarray(image.convert("L"), float) / 255
            )
        key = f'{record["renderer"]}-{record["arm"]}-{record["target"]}'
        distance = contour_error(pristine, maps[key])
        results.append(
            dict(
                target=record["target"],
                renderer=record["renderer"],
                arm=record["arm"],
                dpi=row["dpi"],
                contour_native_px=distance,
                **record["pristine"],
            )
        )
    summary = {}
    for arm in ["A", "C"]:
        selected = [r for r in results if r["arm"] == arm]
        summary[arm] = dict(
            mean_iou=float(np.mean([r["iou"] for r in selected])),
            iou_p05=float(np.quantile([r["iou"] for r in selected], 0.05)),
            mean_signed_area=float(np.mean([r["area"] for r in selected])),
            abs_area_p95=float(np.quantile([abs(r["area"]) for r in selected], 0.95)),
            mean_contour_300dpi_equiv=float(
                np.mean(
                    [
                        r["contour_native_px"]["mean"] * 300 / r["dpi"]
                        for r in selected
                        if r["contour_native_px"]
                    ]
                )
            ),
        )
    return dict(records=results, summary=summary)


if __name__ == "__main__":
    result = {split: evaluate(split) for split in ["validation", "test"]}
    (ROOT / "contour-evaluation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({s: r["summary"] for s, r in result.items()}, indent=2))
