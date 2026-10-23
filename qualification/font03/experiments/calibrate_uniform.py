"""Known-consistent training cohorts calibrate noise; pristine pixels unused."""

import json
from pathlib import Path
import numpy as np

root = Path("qualification/font03/local")
rows = json.loads((root / "train-sources.json").read_text())["records"]
truth = json.loads((root / "train-evaluation-labels.json").read_text())
groups = json.loads((root / "train-groups.json").read_text())["fitted"]
errors = []
excluded = 0
for group in groups:
    faces = {truth[rows[i]["id"]]["face"] for i in group["source_indices"]}
    if len(faces) != 1:
        excluded += 1
        continue
    errors.extend(group["leave_one_out"])
result = dict(
    scope="Supervised training calibration, consistent cohorts only; never pristine pixels.",
    samples=len(errors),
    excluded_mixed_groups=excluded,
    quantiles={str(q): float(np.quantile(errors, q)) for q in [0.5, 0.9, 0.95, 0.99]},
)
(root / "training-noise-calibration.json").write_text(json.dumps(result, indent=2))
