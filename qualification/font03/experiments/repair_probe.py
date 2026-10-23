from pathlib import Path
import json
import time
import numpy as np
from scipy import optimize, ndimage
from PIL import Image
from qualification.font03.consensus import register_affine, robust_template, affine_warp

root = Path("qualification/font03/local")
out = root / "repair"
out.mkdir(exist_ok=True)
for split in ["validation", "test"]:
    rows = json.loads((root / f"{split}-sources.json").read_text())["records"]
    images = np.load(root / f"{split}-canvases.npy")
    labels = json.loads((root / f"{split}-evaluation-labels.json").read_text())
    groups = json.loads((root / f"{split}-groups.json").read_text())["fitted"]
    prototypes = []
    start = time.monotonic()
    for n, g in enumerate(groups):
        if len(g["source_indices"]) < 3:
            continue
        ref = g["source_indices"][0]
        aligned = [
            register_affine(images[ref], images[i])[1] for i in g["source_indices"]
        ]
        field, _ = robust_template(aligned)
        prototypes.append(
            dict(
                key=f"{split}-repair-{n}",
                character=g["character"],
                members=[rows[i]["id"] for i in g["source_indices"]],
                field=field,
            )
        )
    # Fixed bounded evaluation selection; labels choose damage strata, not donors.
    selected = []
    for char in "e1a8.!":
        for severity in [2, 3, 4]:
            candidates = [
                i
                for i, r in enumerate(rows)
                if r["character"] == char and labels[r["id"]]["severity"] == severity
            ]
            if candidates:
                selected.append(min(candidates, key=lambda i: rows[i]["id"]))
    decisions = []
    for target in selected:
        observed = images[target]
        character = rows[target]["character"]
        strong = observed > 0.5
        candidates = []
        if strong.sum() < 8:
            decisions.append(
                dict(
                    id=rows[target]["id"],
                    target=target,
                    accepted=False,
                    reason="insufficient surviving ink",
                )
            )
            continue
        for prototype in [p for p in prototypes if p["character"] == character]:
            template = prototype["field"]

            def residual(p):
                moving = affine_warp(observed, p)
                return (
                    np.maximum(moving - template, 0)
                    + 0.2 * np.minimum(moving - template, 0)
                ).ravel()

            fit = optimize.least_squares(
                residual,
                [0, 0, 0, 1, 1],
                bounds=([-2, -2, -1, 0.96, 0.96], [2, 2, 1, 1.04, 1.04]),
                loss="huber",
                f_scale=0.12,
                max_nfev=25,
                diff_step=0.001,
            )
            aligned = affine_warp(observed, fit.x)
            mass = max(1.0, aligned.sum())
            missing = float(np.maximum(aligned - template, 0).sum() / mass)
            coverage = float(aligned.sum() / max(1.0, template.sum()))
            candidates.append(
                dict(
                    key=prototype["key"],
                    params=fit.x.tolist(),
                    missing=missing,
                    coverage=coverage,
                    score=missing + 0.05 * abs(1 - coverage),
                )
            )
        candidates.sort(key=lambda r: (r["score"], r["key"]))
        if not candidates:
            decisions.append(
                dict(
                    id=rows[target]["id"],
                    target=target,
                    accepted=False,
                    reason="no same-character cohort",
                )
            )
            continue
        best = candidates[0]
        margin = candidates[1]["score"] - best["score"] if len(candidates) > 1 else None
        accepted = (
            best["missing"] <= 0.10
            and 0.4 <= best["coverage"] <= 1.1
            and (margin is None or margin >= 0.015)
        )
        decisions.append(
            dict(
                id=rows[target]["id"],
                target=target,
                accepted=accepted,
                reason=(
                    "source-supported with distinct cohort margin"
                    if accepted
                    else "insufficient containment, surviving area or cohort separation"
                ),
                margin=margin,
                **best,
            )
        )
    (out / f"{split}-source-decisions.json").write_text(
        json.dumps(
            dict(
                decisions=decisions,
                seconds=time.monotonic() - start,
                policy="Separate damaged arm; supplied character fixed; >=3healthy source witnesses; one-sided surviving-ink fit, >=40%survival, <=10%unexplained source ink, >=.015best/next separation. No expected-word correction.",
            ),
            indent=2,
        )
    )
    np.savez_compressed(
        out / f"{split}-templates.npz", **{p["key"]: p["field"] for p in prototypes}
    )
    (out / f"{split}-provenance.json").write_text(
        json.dumps(
            [{k: v for k, v in p.items() if k != "field"} for p in prototypes], indent=2
        )
    )
    print(
        split,
        len(decisions),
        "accepted",
        sum(r["accepted"] for r in decisions),
        "seconds",
        time.monotonic() - start,
        flush=True,
    )
    # Evaluator is separate and entered only after source decisions/templates save.
    results = []
    for decision in decisions:
        if not decision["accepted"]:
            continue
        target = decision["target"]
        row = rows[target]
        px, py, qx, qy = row["public_bbox"]
        im = np.asarray(
            Image.open(
                Path("qualification/font01/local/corpus-font01-v1")
                / split
                / "oracle"
                / f'{row["id"]}-pristine.png'
            ).convert("L"),
            float,
        )
        yy, xx = np.indices((64, 64))
        xh = row["line"]["xheight"]
        cx = (row["ocr_bbox"][0] + row["ocr_bbox"][2]) / 2
        xn = cx + (xx - 32) * xh / 32
        yn = row["line"]["baseline"] + (yy - 48) * xh / 32
        pristine = ndimage.map_coordinates(
            1 - im / 255, [yn - py - 0.5, xn - px - 0.5], order=1, mode="constant"
        )
        reference = affine_warp(pristine, decision["params"])
        source = affine_warp(images[target], decision["params"])
        template = next(p["field"] for p in prototypes if p["key"] == decision["key"])
        mass = max(1.0, reference.sum())
        base = float(((reference - source) ** 2).sum() / mass)
        candidate = float(((reference - template) ** 2).sum() / mass)
        results.append(
            dict(
                id=row["id"],
                severity=labels[row["id"]]["severity"],
                character=row["character"],
                source_error=base,
                canonical_error=candidate,
                improvement=base - candidate,
                prototype=decision["key"],
            )
        )
    (out / f"{split}-evaluated.json").write_text(json.dumps(results, indent=2))
    print("repair diagnostic", split, results, flush=True)
