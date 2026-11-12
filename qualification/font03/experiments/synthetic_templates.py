from pathlib import Path
import json
import time
import numpy as np
from qualification.font03.consensus import (
    register,
    robust_template,
    distance_template,
)

root = Path("qualification/font03/local")
for split in ["validation", "test"]:
    rows = json.loads((root / f"{split}-sources.json").read_text())["records"]
    images = np.load(root / f"{split}-canvases.npy")
    groups = json.loads((root / f"{split}-groups.json").read_text())["fitted"]
    binding = json.loads((root / f"{split}-bindings.json").read_text())["bindings"]
    templates = []
    targets = []
    start = time.monotonic()
    for group in groups:
        members = [i for i in group["source_indices"] if rows[i]["id"] in binding]
        if len(members) < 3:
            continue
        cache = {}
        for target in members:
            witnesses = [i for i in members if i != target]
            reference = witnesses[0]
            if reference not in cache:
                cache[reference] = {
                    i: register(images[reference], images[i])[1]
                    for i in members
                    if i != reference
                }
                cache[reference][reference] = images[reference]
            aligned = [cache[reference][i] for i in witnesses]
            coverage, _ = robust_template(aligned)
            distance = distance_template(aligned)
            parameters, _ = register(coverage, images[target])
            medoid = (
                group["medoid_source_index"]
                if group["medoid_source_index"] in witnesses
                else reference
            )
            medoid_parameters, _ = register(images[medoid], images[target])
            record = dict(
                id=rows[target]["id"],
                target=target,
                reference=reference,
                witness_ids=[rows[i]["id"] for i in witnesses],
                medoid=medoid,
                parameters=parameters.tolist(),
                medoid_parameters=medoid_parameters.tolist(),
                character=rows[target]["character"],
            )
            for method, field in [("C", coverage), ("D", distance)]:
                key = f'{split}-{method}-{rows[target]["id"]}'
                templates.append(
                    dict(
                        key=key,
                        character=rows[target]["character"],
                        size=64,
                        coverage=field.ravel().tolist(),
                    )
                )
                record[method] = key
            targets.append(record)
    (root / f"{split}-trace-input.json").write_text(
        json.dumps({"templates": templates})
    )
    (root / f"{split}-consensus-plan.json").write_text(
        json.dumps(
            dict(
                targets=targets,
                shape_fit="Target pixels excluded from canonical fields. Source-only grouping before leave-one-out; target source permits bounded placement fit, never oracle fitting.",
                seconds=time.monotonic() - start,
            ),
            indent=2,
        )
    )
    print(
        split,
        len(targets),
        "targets",
        len(templates),
        "curves",
        time.monotonic() - start,
        flush=True,
    )
