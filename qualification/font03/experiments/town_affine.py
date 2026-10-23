from pathlib import Path
import json
import numpy as np
from qualification.font03.consensus import (
    register_affine,
    robust_template,
    structural_distances,
    geometry_rejections,
)

original = Path("qualification/font03/local")
out = original / "town-affine"
out.mkdir(exist_ok=True)
old = Path("qualification/font02/local/reuse-study")
images = np.load(old / "line-coverage.npy")
config = json.loads(Path("qualification/font03/construction-control.json").read_text())
groups = config["groups"]
limits = config["structural_limits"]
noise = config["noise"]
fields = []
fitted = []
decisions = []
for g in groups["fitted"]:
    members = g["original_indices"]
    reference = g["medoid_original"]
    aligned = [register_affine(images[reference], images[i])[1] for i in members]
    field, _ = robust_template(aligned)
    index = len(fields)
    fields.append(field)
    params = []
    for target in members:
        p, aligned = register_affine(field, images[target])
        params.append(p.tolist())
        distance = structural_distances(aligned, field)
        error = float(((field - aligned) ** 2).sum() / max(1.0, aligned.sum()))
        reasons = geometry_rejections(aligned, field)
        if error > noise:
            reasons.append("normal-variation cap")
        reasons.extend(
            k for k, limit in limits.items() if distance[k] > max(limit, 1e-6)
        )
        decisions.append(
            dict(
                target=target,
                group=index,
                parameters=p.tolist(),
                accepted=not reasons,
                reasons=reasons,
                error=error,
                distances=distance,
            )
        )
    fitted.append(
        dict(original_indices=members, medoid_original=reference, parameters=params)
    )
(out / "town-groups.json").write_text(json.dumps(dict(fitted=fitted), indent=2))
(out / "field-decisions.json").write_text(json.dumps(decisions, indent=2))
(out / "town-trace-input.json").write_text(
    json.dumps(
        dict(
            templates=[
                dict(
                    key=f"town-E-{i}",
                    size=64,
                    character="e",
                    coverage=f.ravel().tolist(),
                )
                for i, f in enumerate(fields)
            ]
        )
    )
)
print("real field accepted", sum(r["accepted"] for r in decisions), "/", len(decisions))
