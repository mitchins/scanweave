import json
import hashlib
import io
from pathlib import Path
import pikepdf
from fontTools.ttLib import TTFont

r = Path("qualification/font03/local")
out = {}
for name, path in [
    ("baseline", Path("qualification/font02/local/financial-required.pdf")),
    ("preunion", r / "financial-preunion.pdf"),
]:
    with pikepdf.open(path) as pdf:
        fonts = {}
        used = set()
        draws = 0
        by_page = []
        raster = 0
        for obj in pdf.objects:
            if (
                isinstance(obj, pikepdf.Stream)
                and obj.get("/Subtype") == pikepdf.Name.Image
            ):
                raster += len(obj.read_raw_bytes())
        for pi, page in enumerate(pdf.pages):
            count = 0
            tf = None
            mode = 0
            stack = []
            for operands, operator in pikepdf.parse_content_stream(page):
                op = str(operator)
                if op == "q":
                    stack.append((tf, mode))
                if op == "Q":
                    tf, mode = stack.pop()
                if op == "Tf":
                    tf = page.Resources.Font[operands[0]]
                if op == "Tr":
                    mode = int(operands[0])
                if op not in ["Tj", "TJ"] or mode == 3:
                    continue
                strings = (
                    [x for x in operands[0] if isinstance(x, pikepdf.String)]
                    if op == "TJ"
                    else [operands[0]]
                )
                for st in strings:
                    data = bytes(st)
                    for k in range(0, len(data), 2):
                        cid = int.from_bytes(data[k : k + 2], "big")
                        mapping = tf.DescendantFonts[0].CIDToGIDMap.read_bytes()
                        gid = int.from_bytes(mapping[2 * cid : 2 * cid + 2], "big")
                        used.add((tf.objgen, gid))
                        count += 1
            by_page.append(count)
            draws += count
            for tf in page.Resources.Font.values():
                if tf.objgen in fonts:
                    continue
                descendant = tf.DescendantFonts[0]
                program = descendant.FontDescriptor.FontFile2
                tt = TTFont(io.BytesIO(program.read_bytes()))
                fonts[tf.objgen] = dict(
                    slots=tt["maxp"].numGlyphs,
                    encoded_bytes=len(program.read_raw_bytes()),
                    decoded_bytes=len(program.read_bytes()),
                    points=sum(
                        tt["glyf"][g].numberOfContours > 0
                        and len(tt["glyf"][g].coordinates)
                        or 0
                        for g in tt.getGlyphOrder()
                    ),
                    sha256=hashlib.sha256(program.read_bytes()).hexdigest(),
                )
        out[name] = dict(
            pdf_bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            fonts=list(fonts.values()),
            painted_draws=draws,
            distinct_visible_designs=len(used),
            per_page_draws=by_page,
            raster_bytes=raster,
        )
(r / "construction-inventory.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
