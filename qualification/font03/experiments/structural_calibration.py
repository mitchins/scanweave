from pathlib import Path
import json
import numpy as np
from qualification.font03.consensus import (
    register_affine,
    robust_template,
    structural_distances,
)

root = Path("qualification/font03/local")
out = root / "affine-refinement"
rows = json.loads((root / "train-sources.json").read_text())["records"]
images = np.load(root / "train-canvases.npy")
labels = json.loads((root / "train-evaluation-labels.json").read_text())
groups = json.loads((root / "train-groups.json").read_text())["fitted"]
metrics = []
for group in groups:
    members = group["source_indices"]
    if len(members) < 4 or len({labels[rows[i]["id"]]["face"] for i in members}) != 1:
        continue
    cache = {}
    for target in members:
        witnesses = [i for i in members if i != target]
        ref = witnesses[0]
        if ref not in cache:
            cache[ref] = {
                i: register_affine(images[ref], images[i])[1]
                for i in members
                if i != ref
            }
            cache[ref][ref] = images[ref]
        field, _ = robust_template([cache[ref][i] for i in witnesses])
        _, aligned = register_affine(field, images[target])
        metrics.append(structural_distances(aligned, field))
limits = {
    key: float(np.quantile([r[key] for r in metrics], 0.95)) for key in metrics[0]
}
result = dict(
    scope="Training-family known-consistent groups only, >=3independent source witnesses per held-out observation. Same prior fixed groups. No pristine pixels. Quantile.95 fixed for every descriptor; no character-specific limit.",
    samples=len(metrics),
    limits=limits,
    metrics=metrics,
)
(out / "structural-calibration.json").write_text(json.dumps(result, indent=2))
print("calibration", len(metrics), limits)
for split in ["validation", "test"]:
    rows = json.loads((root / f"{split}-sources.json").read_text())["records"]
    images = np.load(root / f"{split}-canvases.npy")
    plans = {
        r["id"]: r
        for r in json.loads((out / f"{split}-consensus-plan.json").read_text())[
            "targets"
        ]
    }
    templates = {
        r["key"]: np.array(r["coverage"]).reshape(64, 64)
        for r in json.loads((out / f"{split}-trace-input.json").read_text())[
            "templates"
        ]
    }
    decisions = json.loads((out / "native-noise-decisions.json").read_text())[
        "decisions"
    ][split]
    frozen = []
    for d in decisions:
        p = plans[d["target"]]
        row = rows[p["target"]]
        small = (
            row["width"] < 4
            or row["height"] < 4
            or max(row["width"], row["height"]) < 0.35 * row["line"]["xheight"]
        )
        _, aligned = register_affine(templates[p["C"]], images[p["target"]])
        dist = structural_distances(aligned, templates[p["C"]])
        reasons = list(d["reasons"])
        if len(p["witness_ids"]) < 3:
            reasons.append("fewer than3independent healthy witnesses")
        if small:
            reasons.append("small-mark geometry unresolved at native sampling")
        for key, limit in limits.items():
            if dist[key] > max(limit, 1e-6):
                reasons.append(key)
        frozen.append(
            dict(
                target=d["target"],
                accepted=not reasons,
                reasons=reasons,
                distances=dist,
            )
        )
    (out / f"{split}-final-decisions.json").write_text(
        json.dumps(
            dict(
                decisions=frozen,
                policy="Calibrated source structure + native error budget + >=3other healthy sources + tiny geometry abstention. No pristine pixel used.",
                limits=limits,
            ),
            indent=2,
        )
    )
    print(split, "accepted", sum(r["accepted"] for r in frozen), "of", len(frozen))
