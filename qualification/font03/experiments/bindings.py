"""Source-only healthy reuse probes. No oracle images/font labels are opened."""

from pathlib import Path
import json
import io
import re
import sys
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy import ndimage
import pikepdf
from fontTools.ttLib import TTFont

root = Path("qualification/font03/local")
split = sys.argv[1]
inputs = json.loads((root / (split + "-sources.json")).read_text())
rows = inputs["records"]
byid = {r["id"]: i for i, r in enumerate(rows)}
source_pdf = (
    Path("qualification/font02/local/hard-negatives/validation-product.pdf")
    if split == "validation"
    else Path("qualification/font01/local/rust-control-test-v2.pdf")
)
source_report = (
    Path("qualification/font02/local/hard-negatives/validation-product.json")
    if split == "validation"
    else Path("qualification/font01/local/rust-control-test-v2.json")
)
report = json.loads(source_report.read_text())
report = report.get("conversion", report)


def mat(args):
    a, b, c, d, e, f = map(float, args)
    return np.array([[a, c, e], [b, d, f], [0, 0, 1.0]])


def args(m):
    return [
        float(m[0, 0]),
        float(m[1, 0]),
        float(m[0, 1]),
        float(m[1, 1]),
        float(m[0, 2]),
        float(m[1, 2]),
    ]


def P(dpi):
    return np.array([[72 / dpi, 0, 0], [0, -72 / dpi, 648], [0, 0, 1.0]])


def N(row):
    s = 32 / row["line"]["xheight"]
    cx = (row["ocr_bbox"][0] + row["ocr_bbox"][2]) / 2
    return np.array(
        [[s, 0, 32 - s * cx], [0, s, 48 - s * row["line"]["baseline"]], [0, 0, 1.0]]
    )


def moved(image, p):
    dx, dy, scale = p
    center = np.array([48.0, 32.0])
    matrix = np.eye(2) / scale
    return ndimage.affine_transform(
        image,
        matrix,
        offset=center - matrix @ (center + [dy, dx]),
        order=1,
        mode="constant",
        prefilter=False,
    )


def forward(p):
    dx, dy, scale = p
    center = np.array([32.0, 48.0])
    m = np.eye(3)
    m[:2, :2] *= scale
    m[:2, 2] = center + [dx, dy] - scale * center
    return m


bindings = {}
abstentions = list(inputs["abstentions"])
atlas = []
pairs = []
with pikepdf.open(source_pdf) as pdf:
    font = pdf.pages[0].Resources.Font.F1
    desc = font.DescendantFonts[0]
    tt = TTFont(io.BytesIO(desc.FontDescriptor.FontFile2.read_bytes()))
    order = tt.getGlyphOrder()
    upem = tt["head"].unitsPerEm
    mapping = desc.CIDToGIDMap.read_bytes()
    unicode = {}
    for block in re.findall(
        rb"beginbfchar(.*?)endbfchar", font.ToUnicode.read_bytes(), re.S
    ):
        for a, b in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            unicode[int(a, 16)] = bytes.fromhex(b.decode()).decode("utf-16-be")
    for page_number, page in enumerate(pdf.pages):
        owned = json.loads(
            (
                Path("qualification/font02/local/hard-negatives")
                / f"{split}-{page_number}-owned.json"
            ).read_text()
        )["observations"]
        visible = {
            o["symbol_id"]
            for o in report["page_reports"][page_number]["occurrences"]
            if o["owner"] == "visible_tounicode"
        }
        owned = [o for o in owned if o["id"] in visible]
        draws = []
        matrix = None
        mode = 0
        for operands, op in pikepdf.parse_content_stream(page):
            if str(op) == "Tm":
                matrix = mat(operands)
            elif str(op) == "Tr":
                mode = int(operands[0])
            elif str(op) == "Tj" and mode != 3:
                cid = int.from_bytes(bytes(operands[0]), "big")
                char = unicode[cid]
                if char not in "e1a8.!" or len(char) != 1:
                    continue
                gid = int.from_bytes(mapping[2 * cid : 2 * cid + 2], "big")
                g = tt["glyf"][order[gid]]
                dpi = [200, 300, 600][page_number]
                center = (
                    np.linalg.inv(P(dpi))
                    @ matrix
                    @ np.array(
                        [
                            (g.xMin + g.xMax) / (2 * upem),
                            (g.yMin + g.yMax) / (2 * upem),
                            1,
                        ]
                    )
                )
                draws.append(
                    {
                        "cid": cid,
                        "gid": gid,
                        "character": char,
                        "matrix": matrix,
                        "center": center[:2],
                    }
                )
        for char in "e1a8.!":
            source = [o for o in owned if o["text"] == char]
            glyphs = [d for d in draws if d["character"] == char]
            if not source:
                continue
            if len(source) != len(glyphs):
                raise ValueError((page_number, char, len(source), len(glyphs)))
            centers = np.array(
                [
                    [
                        (o["bbox"][0] + o["bbox"][2]) / 2,
                        (o["bbox"][1] + o["bbox"][3]) / 2,
                    ]
                    for o in source
                ]
            )
            cost = np.linalg.norm(
                centers[:, None, :]
                - np.array([d["center"] for d in glyphs])[None, :, :],
                axis=2,
            )
            ii, jj = linear_sum_assignment(cost)
            for i, j in zip(ii, jj):
                identifier = source[i]["id"].removeprefix("g")
                if identifier not in byid:
                    continue
                if cost[i, j] > max(5, source[i]["height"] * 0.25):
                    abstentions.append(
                        {
                            "id": identifier,
                            "reason": "Ambiguous source-to-visible-glyph placement",
                        }
                    )
                    continue
                bindings[identifier] = glyphs[j]

(root / (split + "-bindings.json")).write_text(
    json.dumps(
        {
            "source_pdf": str(source_pdf),
            "bindings": {
                k: {**v, "matrix": args(v["matrix"]), "center": v["center"].tolist()}
                for k, v in bindings.items()
            },
            "abstentions": abstentions,
        },
        indent=2,
    )
)
