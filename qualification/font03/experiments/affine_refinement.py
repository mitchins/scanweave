from pathlib import Path
import json
import time
import shutil
import numpy as np
from qualification.font03.consensus import register_affine, robust_template

original = Path("qualification/font03/local")
root = original / "affine-refinement"
root.mkdir(exist_ok=True)
errors = []
(root / "initial-protocol.json").write_text(
    json.dumps(
        dict(
            reason="Documented benchmark scale.96..1.04,aspect.97..1.03,rotation±1.5deg cannot be explained by first uniform±2% fit; same-face boundary-hit failures observed. Hold groups fixed; change nuisance alignment only.",
            translation=2,
            rotation=1,
            scalex=[0.96, 1.04],
            scaley=[0.96, 1.04],
            nonlinear=False,
            shear=False,
            refit_admission=False,
        ),
        indent=2,
    )
)
for split in ["train", "validation", "test"]:
    rows = json.loads((original / f"{split}-sources.json").read_text())["records"]
    images = np.load(original / f"{split}-canvases.npy")
    groups = json.loads((original / f"{split}-groups.json").read_text())["fitted"]
    truth = json.loads((original / f"{split}-evaluation-labels.json").read_text())
    binding = (
        None
        if split == "train"
        else json.loads((original / f"{split}-bindings.json").read_text())["bindings"]
    )
    templates = []
    targets = []
    start = time.monotonic()
    for group in groups:
        members = (
            group["source_indices"]
            if binding is None
            else [i for i in group["source_indices"] if rows[i]["id"] in binding]
        )
        if len(members) < 3:
            continue
        pure = len({truth[rows[i]["id"]]["face"] for i in members}) == 1
        cache = {}
        for target in members:
            witnesses = [i for i in members if i != target]
            reference = witnesses[0]
            if reference not in cache:
                cache[reference] = {
                    i: register_affine(images[reference], images[i])[1]
                    for i in members
                    if i != reference
                }
                cache[reference][reference] = images[reference]
            field, _ = robust_template([cache[reference][i] for i in witnesses])
            parameters, aligned = register_affine(field, images[target])
            error = float(((field - aligned) ** 2).sum() / max(1.0, aligned.sum()))
            if split == "train":
                if pure:
                    errors.append(error)
                continue
            medoid = (
                group["medoid_source_index"]
                if group["medoid_source_index"] in witnesses
                else reference
            )
            medoid_parameters, _ = register_affine(images[medoid], images[target])
            key = f'{split}-E-{rows[target]["id"]}'
            templates.append(
                dict(
                    key=key,
                    character=rows[target]["character"],
                    size=64,
                    coverage=field.ravel().tolist(),
                )
            )
            targets.append(
                dict(
                    id=rows[target]["id"],
                    target=target,
                    reference=reference,
                    witness_ids=[rows[i]["id"] for i in witnesses],
                    medoid=medoid,
                    parameters=parameters.tolist(),
                    medoid_parameters=medoid_parameters.tolist(),
                    character=rows[target]["character"],
                    C=key,
                    D=key,
                    normalized_error=error,
                )
            )
    if split == "train":
        calibration = dict(
            scope="Training only, known-consistent face groups only; source coverage, not pristine pixels. Same fixed groups as first arm.",
            samples=len(errors),
            quantiles={
                str(q): float(np.quantile(errors, q)) for q in [0.5, 0.9, 0.95, 0.99]
            },
        )
        (root / "training-noise-calibration.json").write_text(
            json.dumps(calibration, indent=2)
        )
        print("train", calibration, time.monotonic() - start, flush=True)
        continue
    for suffix in ["sources.json", "bindings.json", "evaluation-labels.json"]:
        shutil.copyfile(original / f"{split}-{suffix}", root / f"{split}-{suffix}")
    shutil.copyfile(original / f"{split}-canvases.npy", root / f"{split}-canvases.npy")
    (root / f"{split}-trace-input.json").write_text(
        json.dumps({"templates": templates})
    )
    (root / f"{split}-consensus-plan.json").write_text(
        json.dumps(
            dict(
                targets=targets,
                seconds=time.monotonic() - start,
                shape_fit="Same groups; target excluded; bounded affine source placement. D arm duplicates C as render invariant, not another fit.",
            ),
            indent=2,
        )
    )
    print(split, len(targets), time.monotonic() - start, flush=True)
