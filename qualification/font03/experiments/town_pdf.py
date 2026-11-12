from pathlib import Path
import json
import numpy as np
import pikepdf
from fontTools.ttLib import TTFont

root = Path("qualification/font03/local")
old = Path("qualification/font02/local/reuse-study")
groups = json.loads((root / "town-groups.json").read_text())
plan = json.loads((old / "substitution-plan.json").read_text())
binding = plan["glyph_bindings"]
meta = json.loads((old / "registered-pairs.json").read_text())["observations"]
outlines = json.loads((root / "template-outlines.json").read_text())
upem = 2048
P = np.array([[435 / 1813, 0, 0], [0, -637 / 2655, 637], [0, 0, 1.0]])


def N(i):
    o = meta[i]
    g = o["line"]
    s = 32 / g["xheight"]
    cx = (o["ocr_bbox"][0] + o["ocr_bbox"][2]) / 2
    base = (
        g["line_bbox"][3]
        + g["baseline"][1]
        + g["baseline"][0] * (cx - g["line_bbox"][0])
    )
    return np.array([[s, 0, 32 - s * cx], [0, s, 48 - s * base], [0, 0, 1.0]])


def tm(v):
    a, b, c, d, e, f = v
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


def F(p):
    dx, dy, s = p
    c = np.array([32.0, 48.0])
    m = np.eye(3)
    m[:2, :2] *= s
    m[:2, 2] = c + [dx, dy] - s * c
    return m


def add_font(pdf):
    tt = TTFont(root / "templates.ttf")
    order = tt.getGlyphOrder()
    fontfile = pdf.make_stream((root / "templates.ttf").read_bytes())
    fontfile.Length1 = len((root / "templates.ttf").read_bytes())
    descriptor = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.FontDescriptor,
            FontName=pikepdf.Name.FONT03,
            Flags=4,
            FontBBox=[-100, -100, 2300, 2300],
            ItalicAngle=0,
            Ascent=1123,
            Descent=-49,
            CapHeight=512,
            StemV=80,
            FontFile2=fontfile,
        )
    )
    widths = []
    for i, name in enumerate(order):
        widths.extend([i, [tt["hmtx"][name][0] * 1000 / upem]])
    descendant = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.CIDFontType2,
            BaseFont=pikepdf.Name.FONT03,
            CIDSystemInfo=pikepdf.Dictionary(
                Registry="Adobe", Ordering="Identity", Supplement=0
            ),
            FontDescriptor=descriptor,
            CIDToGIDMap=pikepdf.Name.Identity,
            DW=500,
            W=widths,
        )
    )
    cmap = (
        b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def /CMapName /FONT03Unicode def /CMapType 2 def 1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
        + str(len(order) - 1).encode()
        + b" beginbfchar\n"
        + b"\n".join(f"<{i:04x}> <0065>".encode() for i in range(1, len(order)))
        + b"\nendbfchar endcmap CMapName currentdict /CMap defineresource pop end end"
    )
    return pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type0,
            BaseFont=pikepdf.Name.FONT03,
            Encoding=pikepdf.Name("/Identity-H"),
            DescendantFonts=[descendant],
            ToUnicode=pdf.make_stream(cmap),
        )
    )


updates = {"B": {}, "C": {}}
for gi, g in enumerate(groups["fitted"]):
    med = g["medoid_original"]
    for i, parameters in zip(g["original_indices"], g["parameters"]):
        transform = F(parameters)
        b = (
            P
            @ np.linalg.inv(N(i))
            @ np.linalg.inv(transform)
            @ N(med)
            @ np.linalg.inv(P)
            @ tm(binding[med]["matrix"])
        )
        x0, y0 = outlines[gi]["origin"]
        w, h = outlines[gi]["crop"]
        glyph_to_canvas = np.array([[128.0, 0, x0], [0, -128.0, y0 + h], [0, 0, 1.0]])
        c = P @ np.linalg.inv(N(i)) @ np.linalg.inv(transform) @ glyph_to_canvas
        updates["B"][i] = dict(
            font="F1", cid=binding[med]["cid"], matrix=args(b), group=gi
        )
        updates["C"][i] = dict(
            font="F2", cid=outlines[gi]["gid"], matrix=args(c), group=gi
        )
source = Path("qualification/font02/local/financial-required.pdf")
with pikepdf.open(source) as pdf:
    pdf.pages[0].Resources.Font.F2 = add_font(pdf)
    out = pikepdf.Pdf.new()
    for arm in ["A", "B", "C"]:
        out.pages.append(pdf.pages[0])
        page = out.pages[-1]
        commands = ["q 1 1 1 rg 0 0 435 637 re f Q", "BT 0 Tr 0 0 0 rg"]
        for i, bind in enumerate(binding):
            row = updates.get(arm, {}).get(
                i, dict(font="F1", cid=bind["cid"], matrix=bind["matrix"])
            )
            commands.append(
                "/"
                + row["font"]
                + " 1 Tf "
                + " ".join(f"{x:.10f}" for x in row["matrix"])
                + " Tm <"
                + row["cid"].to_bytes(2, "big").hex()
                + "> Tj"
            )
        commands.append("ET")
        page.Contents = out.make_stream(("\n".join(commands) + "\n").encode())
    out.save(
        root / "town-ABC.pdf",
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
        compress_streams=True,
        deterministic_id=True,
    )
for arm in ["B", "C"]:
    with pikepdf.open(source) as pdf:
        if arm == "C":
            pdf.pages[0].Resources.Font.F2 = add_font(pdf)
        ops = list(pikepdf.parse_content_stream(pdf.pages[0]))
        targets = {binding[i]["op_index"]: u for i, u in updates[arm].items()}
        rewritten = []
        position = None
        for index, (operands, op) in enumerate(ops):
            if str(op) == "Tm":
                position = len(rewritten)
            if index in targets:
                u = targets[index]
                rewritten[position] = pikepdf.ContentStreamInstruction(
                    u["matrix"], pikepdf.Operator("Tm")
                )
                rewritten.append(
                    pikepdf.ContentStreamInstruction(
                        [pikepdf.Name("/" + u["font"]), 1], pikepdf.Operator("Tf")
                    )
                )
                rewritten.append(
                    pikepdf.ContentStreamInstruction(
                        [pikepdf.String(u["cid"].to_bytes(2, "big"))], op
                    )
                )
                rewritten.append(
                    pikepdf.ContentStreamInstruction(
                        [pikepdf.Name.F1, 1], pikepdf.Operator("Tf")
                    )
                )
                continue
            rewritten.append(pikepdf.ContentStreamInstruction(operands, op))
        pdf.pages[0].Contents = pdf.make_stream(
            pikepdf.unparse_content_stream(rewritten)
        )
        pdf.save(
            root / f"financial-{arm}-shadow.pdf",
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            compress_streams=True,
            deterministic_id=True,
        )
(root / "town-placement.json").write_text(json.dumps(updates, indent=2))
print(
    "C26 placements; complete bytes",
    [(a, (root / f"financial-{a}-shadow.pdf").stat().st_size) for a in ["B", "C"]],
)
