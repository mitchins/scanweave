"""PDF probe helpers using existing embedded fonts; not a converter pipeline."""

import io
import numpy as np
import pikepdf
from fontTools.ttLib import TTFont


def matrix(values):
    a, b, c, d, e, f = values
    return np.array([[a, c, e], [b, d, f], [0.0, 0.0, 1.0]])


def operands(m):
    return [
        float(m[0, 0]),
        float(m[1, 0]),
        float(m[0, 1]),
        float(m[1, 1]),
        float(m[0, 2]),
        float(m[1, 2]),
    ]


def forward(parameters):
    if len(parameters) == 5:
        from .consensus import affine_forward

        return affine_forward(parameters)
    dx, dy, scale = parameters
    center = np.array([32.0, 48.0])
    m = np.eye(3)
    m[:2, :2] *= scale
    m[:2, 2] = center + [dx, dy] - scale * center
    return m


def normalizer(row):
    scale = 32 / row["line"]["xheight"]
    cx = (row["ocr_bbox"][0] + row["ocr_bbox"][2]) / 2
    return np.array(
        [
            [scale, 0.0, 32 - scale * cx],
            [0.0, scale, 48 - scale * row["line"]["baseline"]],
            [0.0, 0.0, 1.0],
        ]
    )


def page_transform(dpi, height=648.0):
    return np.array([[72 / dpi, 0.0, 0.0], [0.0, -72 / dpi, height], [0.0, 0.0, 1.0]])


def font_resource(pdf, font_path, outlines):
    """Bind the actual traced SFNT programs and explicit supplied Unicode."""
    data = font_path.read_bytes()
    tt = TTFont(io.BytesIO(data))
    order = tt.getGlyphOrder()
    program = pdf.make_stream(data)
    program.Length1 = len(data)
    descriptor = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.FontDescriptor,
            FontName=pikepdf.Name.FONT03,
            Flags=4,
            FontBBox=[-49, -49, 1123, 1123],
            ItalicAngle=0,
            Ascent=1123,
            Descent=-49,
            CapHeight=512,
            StemV=80,
            FontFile2=program,
        )
    )
    widths = []
    for i, name in enumerate(order):
        widths.extend([i, [tt["hmtx"][name][0] * 1000 / tt["head"].unitsPerEm]])
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
    maps = [
        f'<{r["gid"]:04x}> <{r["character"].encode("utf-16-be").hex()}>'
        for r in outlines
        if "gid" in r
    ]
    cmap = (
        "/CIDInit /ProcSet findresource begin 12 dict begin begincmap "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def "
        "/CMapName /FONT03Unicode def /CMapType 2 def "
        "1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
    )
    # Keep each bfchar block inside the PDF CMap100-entry limit.
    for start in range(0, len(maps), 100):
        block = maps[start : start + 100]
        cmap += f"{len(block)} beginbfchar\n" + "\n".join(block) + "\nendbfchar\n"
    cmap += "endcmap CMapName currentdict /CMap defineresource pop end end"
    return pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type0,
            BaseFont=pikepdf.Name.FONT03,
            Encoding=pikepdf.Name("/Identity-H"),
            DescendantFonts=[descendant],
            ToUnicode=pdf.make_stream(cmap.encode()),
        )
    )


def contour_matrix(row, parameters, outline):
    x, y = outline["origin"]
    _, height = outline["crop"]
    glyph_to_canvas = np.array(
        [[128.0, 0.0, x], [0.0, -128.0, y + height], [0.0, 0.0, 1.0]]
    )
    return (
        page_transform(row["dpi"])
        @ np.linalg.inv(normalizer(row))
        @ np.linalg.inv(forward(parameters))
        @ glyph_to_canvas
    )
