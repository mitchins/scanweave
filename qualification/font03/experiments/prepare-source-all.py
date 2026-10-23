"""Freeze evaluator-selected controls; registration inputs remain source-only."""

from pathlib import Path
import json
import hashlib
import sys
import numpy as np
from scipy import ndimage
from PIL import Image

sys.path.insert(0, str(Path.cwd()))
from qualification.font01.context import source_lines

root = Path("qualification/font03/local")
for split in ["train", "validation", "test"]:
    corpus = Path("qualification/font01/local/corpus-font01-v1") / split
    public = [
        json.loads(line)
        for line in (corpus / "observations.jsonl").read_text().splitlines()
    ]
    labels = [
        json.loads(line)
        for line in (corpus / "oracle/labels.jsonl").read_text().splitlines()
    ]
    truth = {p["id"]: label for p, label in zip(public, labels)}
    assert len(public) == len(labels)
    chosen = [p for p in public if p["character"] in "e1a8.!"]
    frozen = {
        "split": split,
        "selection": "All available observations for fixed characters e1a8.! across severity strata. Labels used for benchmark stratification only, never registration or candidate ranking.",
        "ids": [p["id"] for p in chosen],
        "public_sha256": hashlib.sha256(
            (corpus / "observations.jsonl").read_bytes()
        ).hexdigest(),
        "labels_sha256": hashlib.sha256(
            (corpus / "oracle/labels.jsonl").read_bytes()
        ).hexdigest(),
        "parameters": {
            "rotation_degrees": 0,
            "translation_grid_px": 2,
            "uniform_scale": [0.98, 1.02],
            "grid": 64,
            "xheight_grid": 32,
            "baseline_grid": 48,
            "max_nfev": 30,
            "healthy_candidate_gate": "No worse source-coverage MSE than current glyph in BOTH renderers; no character rewriting. Oracle evaluation only after decisions.",
        },
    }
    (root / (split + "-frozen.json")).write_text(json.dumps(frozen, indent=2))
    owned = {}
    source_pages = {}
    exports = {}
    for page in range(3):
        export_root = (
            root
            if split == "train"
            else Path("qualification/font02/local/hard-negatives")
        )
        export = json.loads((export_root / f"{split}-{page}-owned.json").read_text())
        exports[page] = export
        for o in export["observations"]:
            owned[o["id"].removeprefix("g")] = o
        source = np.asarray(
            Image.open(corpus / f"page-{page}.png").convert("RGB"), float
        )
        source_pages[page] = np.round(source @ np.array([0.2126, 0.7152, 0.0722]))
    line_info = {}
    for indices in source_lines(public):
        page = public[indices[0]]["page"]
        samples = [
            owned[public[i]["id"]]
            for i in indices
            if public[i]["id"] in owned and public[i]["character"] in "ace"
        ]
        samples = [o for o in samples if o["height"] >= 4 and not o["suspect"]]
        if len(samples) < 3:
            samples = [
                owned[public[i]["id"]]
                for i in indices
                if public[i]["id"] in owned and owned[public[i]["id"]]["height"] >= 4
            ]
        if not samples:
            continue
        xh = float(np.median([o["height"] for o in samples]))
        base = float(np.median([o["bbox"][3] for o in samples]))
        for i in indices:
            line_info[public[i]["id"]] = {
                "xheight": xh,
                "baseline": base,
                "members": len(indices),
                "source_samples": len(samples),
            }
    records = []
    canvases = []
    abstentions = []
    for p in chosen:
        identifier = p["id"]
        o = owned.get(identifier)
        line = line_info.get(identifier)
        if o is None or line is None or o["suspect"] or line["xheight"] < 4:
            abstentions.append(
                {
                    "id": identifier,
                    "reason": "No bounded single-character ownership or reliable line geometry",
                }
            )
            continue
        gray = source_pages[p["page"]]
        x0, y0, x1, y1 = map(int, o["bbox"])
        pad = 2
        if x0 < pad or y0 < pad or x1 + pad > gray.shape[1] or y1 + pad > gray.shape[0]:
            abstentions.append(
                {"id": identifier, "reason": "Page-edge halo unsupported"}
            )
            continue
        patch = gray[y0 - pad : y1 + pad, x0 - pad : x1 + pad]
        mask = np.pad(np.array(o["mask"], bool).reshape(o["height"], o["width"]), pad)
        paper = float(np.quantile(patch[~mask], 0.8))
        ink = float(np.quantile(patch[mask], 0.15))
        if paper <= ink + 30:
            abstentions.append(
                {"id": identifier, "reason": "Insufficient ink/paper contrast"}
            )
            continue
        distance = ndimage.distance_transform_edt(~mask)
        foreign = (
            np.abs(
                patch
                - float(np.dot(exports[p["page"]]["paper"], [0.2126, 0.7152, 0.0722]))
            )
            > 60
        ) & ~mask
        fd = (
            ndimage.distance_transform_edt(~foreign)
            if foreign.any()
            else np.full(patch.shape, 100.0)
        )
        support = (distance <= 1.5) & (distance < fd)
        coverage = np.clip((paper - patch) / (paper - ink), 0, 1) * support
        yy, xx = np.mgrid[:64, :64]
        cx = (o["ocr_bbox"][0] + o["ocr_bbox"][2]) / 2
        s = 32 / line["xheight"]
        xn = cx + (xx - 32) / s
        yn = line["baseline"] + (yy - 48) / s
        canvas = ndimage.map_coordinates(
            coverage,
            [yn - (y0 - pad) - 0.5, xn - (x0 - pad) - 0.5],
            order=1,
            mode="constant",
        )
        canvases.append(canvas)
        records.append(
            {
                "id": identifier,
                "source_symbol_id": o["id"],
                "character": p["character"],
                "page": p["page"],
                "dpi": p["dpi"],
                "bbox": o["bbox"],
                "ocr_bbox": o["ocr_bbox"],
                "public_bbox": p["bbox"],
                "line": line,
                "paper": paper,
                "ink": ink,
                "shape_key": o["shape_key"],
                "width": o["width"],
                "height": o["height"],
                "mask": o["mask"],
            }
        )
    np.save(root / (split + "-canvases.npy"), np.array(canvases))
    (root / (split + "-sources.json")).write_text(
        json.dumps({"records": records, "abstentions": abstentions}, indent=2)
    )
    (root / (split + "-evaluation-labels.json")).write_text(
        json.dumps({p["id"]: truth[p["id"]] for p in chosen}, indent=2)
    )
    print(
        split,
        "selected",
        len(chosen),
        "source inputs",
        len(records),
        "abstentions",
        len(abstentions),
        flush=True,
    )
