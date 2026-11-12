"""Apply the training-derived allowance to native source error in both renderers.

Run after synthetic_measure, before structural_calibration. Pristine references
are intentionally not read here. This is a development experiment, not a
production acceptance policy.
"""

import json
from pathlib import Path

root = Path("qualification/font03/local/affine-refinement")
noise = json.loads((root / "training-noise-calibration.json").read_text())["quantiles"][
    "0.95"
]
results = {}
for split in ("validation", "test"):
    rows = json.loads((root / f"{split}-source-rendered.json").read_text())["records"]
    lookup = {(r["target"], r["renderer"], r["arm"]): r for r in rows}
    decisions = []
    targets = sorted({r["target"] for r in rows})
    for target in targets:
        reasons = []
        for renderer in ("pdfium", "poppler"):
            current = lookup[target, renderer, "A"]
            candidate = lookup[target, renderer, "C"]
            if not candidate["source_gate"]:
                reasons.append(renderer + " initial source gate")
            if candidate["source_mse"] > current["source_mse"] + noise:
                reasons.append(renderer + " native source error budget")
        decisions.append(dict(target=target, accepted=not reasons, reasons=reasons))
    results[split] = decisions
(root / "native-noise-decisions.json").write_text(
    json.dumps(dict(decisions=results, noise=noise), indent=2)
)
