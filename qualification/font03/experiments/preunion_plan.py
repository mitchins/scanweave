from pathlib import Path
import json
import hashlib
import numpy as np
from PIL import Image
from qualification.font03.consensus import affine_forward

r = Path("qualification/font03/local/town-affine")
old = Path("qualification/font02/local/reuse-study")
groups = json.loads((r / "town-groups.json").read_text())["fitted"]
curves = json.loads((r / "town-trace-input.json").read_text())["templates"]
outs = json.loads((r / "template-outlines.json").read_text())
meta = json.loads((old / "registered-pairs.json").read_text())["observations"]
accepted = {
    x["target"]
    for x in json.loads((r / "native-decisions.json").read_text())
    if x["accepted"]
}
rgb = np.asarray(Image.open(old / "town-source.png").convert("RGB"))
records = []
for i in sorted(accepted):
    gi = next(k for k, g in enumerate(groups) if i in g["original_indices"])
    g = groups[gi]
    p = list(g["parameters"][g["original_indices"].index(i)])
    p[2] = 0.0
    o = meta[i]
    line = o["line"]
    s = 32 / line["xheight"]
    cx = sum(o["ocr_bbox"][::2]) / 2
    base = (
        line["line_bbox"][3]
        + line["baseline"][1]
        + line["baseline"][0] * (cx - line["line_bbox"][0])
    )
    n = np.array([[s, 0, 32 - s * cx], [0, s, 48 - s * base], [0, 0, 1.0]])
    f = affine_forward(p)
    x, y = outs[gi]["origin"]
    w, h = outs[gi]["crop"]
    a = np.linalg.inv(n) @ np.linalg.inv(f) @ np.array([x, y, 1])
    b = np.linalg.inv(n) @ np.linalg.inv(f) @ np.array([x + w, y + h, 1])
    records.append(dict(target=i, symbol_id=o["id"], group=gi, bbox=[*a[:2], *b[:2]]))
plan = dict(
    rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
    width=rgb.shape[1],
    height=rgb.shape[0],
    templates=curves,
    occurrences=records,
)
(r / "preunion-plan.json").write_text(json.dumps(plan, indent=2))
print(records)
