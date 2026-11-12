from pathlib import Path
import json
import re
import collections
import pikepdf

r = Path("qualification/font03/local")
out = []
with pikepdf.open("qualification/font02/local/financial-required.pdf") as pdf:
    f = pdf.pages[0].Resources.Font.F1
    m = f.DescendantFonts[0].CIDToGIDMap.read_bytes()
    unicode = {}
    for block in re.findall(
        rb"beginbfchar(.*?)endbfchar", f.ToUnicode.read_bytes(), re.S
    ):
        for a, b in re.findall(rb"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", block):
            unicode[int(a, 16)] = bytes.fromhex(b.decode()).decode("utf-16-be")
    for pi, page in enumerate(pdf.pages):
        chars = collections.defaultdict(list)
        stack = []
        mode = 0
        for a, op in pikepdf.parse_content_stream(page):
            s = str(op)
            if s == "q":
                stack.append(mode)
            elif s == "Q":
                mode = stack.pop()
            elif s == "Tr":
                mode = int(a[0])
            elif s == "Tj" and mode != 3:
                cid = int.from_bytes(bytes(a[0]), "big")
                gid = int.from_bytes(m[2 * cid : 2 * cid + 2], "big")
                chars[unicode[cid]].append(gid)
        out.append(
            dict(
                page=pi + 1,
                characters={
                    c: dict(draws=len(g), designs=len(set(g)))
                    for c, g in sorted(chars.items())
                },
            )
        )
(r / "financial-character-inventory.json").write_text(json.dumps(out, indent=2))
print(
    "per-character draws/design sums across pages (not global distinct):",
    {
        c: [
            sum(p["characters"].get(c, {}).get(k, 0) for p in out)
            for k in ["draws", "designs"]
        ]
        for c in ["e", "a", "o", "t", "1", "8", ".", ","]
    },
)
