from pathlib import Path
import json
import time
import hashlib
import numpy as np
from qualification.font03.consensus import complete_groups, fit_group, Limits

root = Path("qualification/font03/local")
protocol = dict(
    limits=Limits().__dict__,
    roles="D0/D1 healthy development; evaluator severity selects the arm, faces never used for inference. Test families previously inspected in FONT01/02.",
    quality="Pristine errors and material regressions retained per occurrence; structural veto + LOO noise envelope frozen before oracle pixels. No zero-tolerance source-error rule.",
)
(root / "initial-protocol.json").write_text(json.dumps(protocol, indent=2))
for split in ["train", "validation", "test"]:
    rows = json.loads((root / f"{split}-sources.json").read_text())["records"]
    truth = json.loads((root / f"{split}-evaluation-labels.json").read_text())
    indices = [i for i, r in enumerate(rows) if truth[r["id"]]["severity"] <= 1]
    images = np.load(root / f"{split}-canvases.npy")[indices]
    characters = [rows[i]["character"] for i in indices]
    start = time.monotonic()
    groups, pairs = complete_groups(images, characters)
    results = []
    templates = []
    for group in groups:
        if len(group) < 3:
            continue
        fit = fit_group(images, group)
        templates.append(fit.pop("template"))
        fit.pop("uncertainty")
        fit["ids"] = [rows[indices[i]]["id"] for i in group]
        fit["character"] = characters[group[0]]
        fit["source_indices"] = [indices[i] for i in group]
        fit["medoid_source_index"] = indices[fit["medoid"]]
        results.append(fit)
    np.save(root / f"{split}-templates.npy", templates)
    output = dict(
        source_sha256=hashlib.sha256(
            (root / f"{split}-sources.json").read_bytes()
        ).hexdigest(),
        eligible_indices=indices,
        groups=[[indices[i] for i in g] for g in groups],
        fitted=results,
        seconds=time.monotonic() - start,
    )
    (root / f"{split}-groups.json").write_text(json.dumps(output, indent=2))
    print(
        split,
        "healthy",
        len(indices),
        "groups",
        len(groups),
        "fitted",
        [len(r["ids"]) for r in results],
        "seconds",
        time.monotonic() - start,
        flush=True,
    )
