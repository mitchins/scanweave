"""Produce the frozen three-parameter Town control, distinct from affine trials."""

import json
from pathlib import Path
import numpy as np
from qualification.font03.consensus import register, robust_template

root = Path("qualification/font03/local")
config = json.loads(Path("qualification/font03/construction-control.json").read_text())
images = np.load("qualification/font02/local/reuse-study/line-coverage.npy")
fields = []
for group in config["groups"]["fitted"]:
    reference = group["medoid_original"]
    aligned = [
        register(images[reference], images[i])[1] for i in group["original_indices"]
    ]
    field, _ = robust_template(aligned)
    fields.append(field)
(root / "town-groups.json").write_text(json.dumps(config["groups"], indent=2))
np.save(root / "town-templates.npy", fields)
(root / "town-trace-input.json").write_text(
    json.dumps(
        dict(
            templates=[
                dict(
                    key=f"town-C-{i}",
                    size=64,
                    character="e",
                    coverage=field.ravel().tolist(),
                )
                for i, field in enumerate(fields)
            ]
        )
    )
)
