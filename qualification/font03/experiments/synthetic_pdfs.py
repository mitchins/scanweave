from pathlib import Path
import json
import hashlib
import sys
import numpy as np
import pikepdf
from qualification.font03.probe_pdf import (
    page_transform,
    normalizer,
    forward,
    matrix,
    operands,
    contour_matrix,
    font_resource,
)

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("qualification/font03/local")
for split in ["validation", "test"]:
    source = json.loads((root / f"{split}-bindings.json").read_text())
    binding = source["bindings"]
    rows = json.loads((root / f"{split}-sources.json").read_text())["records"]
    plan = json.loads((root / f"{split}-consensus-plan.json").read_text())
    curves = root / (split + "-curves")
    outlines = json.loads((curves / "template-outlines.json").read_text())
    bykey = {r["key"]: r for r in outlines}
    targets = []
    rejected = []
    noise = json.loads((root / "training-noise-calibration.json").read_text())[
        "quantiles"
    ]["0.95"]
    for target in plan["targets"]:
        if not all("gid" in bykey[target[arm]] for arm in ["C", "D"]):
            rejected.append(target["id"])
            continue
        row = rows[target["target"]]
        medoid = rows[target["medoid"]]
        b = (
            page_transform(row["dpi"])
            @ np.linalg.inv(normalizer(row))
            @ np.linalg.inv(forward(target["medoid_parameters"]))
            @ normalizer(medoid)
            @ np.linalg.inv(page_transform(medoid["dpi"]))
            @ matrix(binding[medoid["id"]]["matrix"])
        )
        target["placements"] = {
            "A": dict(
                font="F1",
                cid=binding[target["id"]]["cid"],
                matrix=binding[target["id"]]["matrix"],
            ),
            "B": dict(font="F1", cid=binding[medoid["id"]]["cid"], matrix=operands(b)),
        }
        for arm in ["C", "D"]:
            outline = bykey[target[arm]]
            target["placements"][arm] = dict(
                font="F2",
                cid=outline["gid"],
                matrix=operands(contour_matrix(row, target["parameters"], outline)),
            )
        targets.append(target)
    with pikepdf.open(source["source_pdf"]) as pdf:
        out = pikepdf.Pdf.new()
        font = font_resource(out, curves / "templates.ttf", outlines)
        atlas = []
        for arm in ["A", "B", "C", "D"]:
            for number in range(3):
                selected = [t for t in targets if rows[t["target"]]["page"] == number]
                out.pages.append(pdf.pages[number])
                page = out.pages[-1]
                page.Resources = pikepdf.Dictionary(
                    Font=pikepdf.Dictionary(F1=page.Resources.Font.F1, F2=font)
                )
                commands = ["q 1 1 1 rg 0 0 432 648 re f Q", "BT 0 Tr 0 0 0 rg"]
                for target in selected:
                    p = target["placements"][arm]
                    commands.append(
                        "/"
                        + p["font"]
                        + " 1 Tf "
                        + " ".join(f"{v:.10f}" for v in p["matrix"])
                        + " Tm <"
                        + p["cid"].to_bytes(2, "big").hex()
                        + "> Tj"
                    )
                commands.append("ET")
                page.Contents = out.make_stream(("\n".join(commands) + "\n").encode())
                atlas.append(
                    dict(
                        arm=arm,
                        page=number,
                        atlas_page=len(out.pages) - 1,
                        targets=[t["id"] for t in selected],
                        dpi=[200, 300, 600][number],
                    )
                )
        path = root / f"{split}-ABCD.pdf"
        out.save(
            path,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            compress_streams=True,
            deterministic_id=True,
        )
    (root / f"{split}-render-plan.json").write_text(
        json.dumps(
            dict(
                targets=targets,
                atlas=atlas,
                trace_rejections=rejected,
                pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                training_noise_upper=noise,
            ),
            indent=2,
        )
    )
    print(
        split,
        "targets",
        len(targets),
        "trace rejected",
        len(rejected),
        "bytes",
        path.stat().st_size,
    )
