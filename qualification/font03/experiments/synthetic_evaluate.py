from pathlib import Path
import sys
import json
import hashlib
import numpy as np
from PIL import Image
from qualification.font02.rendered_reuse import coverage_metrics, renderer_outcome

root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("qualification/font03/local")
split = sys.argv[1]
frozen = json.loads((root / f"{split}-source-freeze.json").read_text())
assert (
    hashlib.sha256((root / f"{split}-source-rendered.json").read_bytes()).hexdigest()
    == frozen["decisions_sha256"]
)
assert (
    hashlib.sha256((root / f"{split}-native-coverages.npz").read_bytes()).hexdigest()
    == frozen["coverage_sha256"]
)
source = json.loads((root / f"{split}-source-rendered.json").read_text())
rows = {
    r["id"]: r
    for r in json.loads((root / f"{split}-sources.json").read_text())["records"]
}
maps = np.load(root / f"{split}-native-coverages.npz")
results = []
baseline = {}
truth = json.loads((root / f"{split}-evaluation-labels.json").read_text())
plans = {
    r["id"]: r
    for r in json.loads((root / f"{split}-render-plan.json").read_text())["targets"]
}
for r in source["records"]:
    row = rows[r["target"]]
    x, y, xx, yy = r["bounds"]
    px, py, qx, qy = row["public_bbox"]
    pristine = np.zeros((yy - y, xx - x))
    im = np.asarray(
        Image.open(
            Path("qualification/font01/local/corpus-font01-v1")
            / split
            / "oracle"
            / f'{r["target"]}-pristine.png'
        ).convert("L"),
        float,
    )
    assert im.shape == (qy - py, qx - px)
    pristine[py - y : qy - y, px - x : qx - x] = 1 - im / 255.0
    measurement = coverage_metrics(
        pristine, maps[f'{r["renderer"]}-{r["arm"]}-{r["target"]}']
    )
    key = r["renderer"], r["target"]
    if r["arm"] == "A":
        baseline[key] = measurement
    base = baseline[key]
    outcome = renderer_outcome(base, measurement)
    results.append(
        dict(
            **r,
            pristine=measurement,
            baseline_pristine=base,
            **outcome,
            severity=truth[r["target"]]["severity"],
        )
    )
summary = {}
for arm in ["A", "B", "C", "D"]:
    rs = [r for r in results if r["arm"] == arm]
    accepted_ids = [
        t
        for t in plans
        if arm in ["C", "D"] and all(r["source_gate"] for r in rs if r["target"] == t)
    ]
    accepted = [r for r in rs if r["target"] in accepted_ids]
    summary[arm] = dict(
        targets=len(rs) // 2,
        mean_error=float(np.mean([r["pristine"]["mse"] for r in rs])),
        p95_error=float(np.quantile([r["pristine"]["mse"] for r in rs], 0.95)),
        material_targets=len({r["target"] for r in rs if r["material"]}),
        source_accepted=len(accepted_ids),
        accepted_material=len({r["target"] for r in accepted if r["material"]}),
        accepted_ambiguous=len(
            {r["target"] for r in accepted if not r["safe"] and not r["material"]}
        ),
        accepted_mean_error=(
            float(np.mean([r["pristine"]["mse"] for r in accepted]))
            if accepted
            else None
        ),
    )
(root / f"{split}-evaluated.json").write_text(
    json.dumps(
        dict(
            summary=summary,
            records=results,
            protocol="FONT02 frozen per-renderer relative-safe/material diagnostic thresholds; no font-label penalty.",
        ),
        indent=2,
    )
)
print(split, json.dumps(summary, indent=2))
