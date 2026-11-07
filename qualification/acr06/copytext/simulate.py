#!/usr/bin/env python3
"""Issue #31 diagnosis: replay PDFium's CPDF_TextPage line buffering (origin-y line test,
origin-x insertion sort, ActualText re-emission when consecutive objects change marked
span) over ScanWeave's content stream, and report every span the sort splits and the
object that split it. Usage: simulate.py PDF [PAGE ...]"""
import sys, pikepdf
from collections import Counter

def widths(page):
    """CID -> advance (1000ths) from each Type0 font's descendant /W, by font resource name."""
    res = {}
    for name, font in page.Resources.get("/Font", {}).items():
        d = font.DescendantFonts[0] if "/DescendantFonts" in font else None
        dw = float(d.get("/DW", 1000)) if d is not None else 1000.0
        table = {}
        w = list(d.get("/W", [])) if d is not None else []
        i = 0
        while i < len(w):
            first = int(w[i])
            if isinstance(w[i + 1], pikepdf.Array):
                for k, v in enumerate(w[i + 1]):
                    table[first + k] = float(v)
                i += 2
            else:
                for c in range(first, int(w[i + 1]) + 1):
                    table[c] = float(w[i + 2])
                i += 3
        res[str(name)] = (dw, table)
    return res

def objects(page):
    fonts = widths(page)
    out, tm, tr, mark, size, mid, font = [], None, 0, None, 1.0, 0, None
    stack = []
    for operands, op in pikepdf.parse_content_stream(page):
        o = str(op)
        if o == "BDC":
            mid += 1
            a = operands[1].get("/ActualText") if isinstance(operands[1], pikepdf.Dictionary) else None
            stack.append((mid, str(a) if a is not None else None))
        elif o == "BMC":
            stack.append((None, None))
        elif o == "EMC":
            stack and stack.pop()
        elif o == "Tm":
            tm = [float(x) for x in operands]
        elif o == "Tf":
            size = float(operands[1]); font = str(operands[0])
        elif o == "Tr":
            tr = int(operands[0])
        elif o in ("Tj", "TJ"):
            a, b, c, d, e, f = tm
            raw = bytes(operands[0]) if o == "Tj" else b""
            cid = raw[0] << 8 | raw[1] if len(raw) >= 2 else 0
            dw, table = fonts.get(font, (1000.0, {}))
            # PDFium: GetCharWidth(cid) * size / 1000, then TransformDistance = (XUnit + YUnit) / 2
            w = table.get(cid, dw) / 1000 * size * ((a * a + b * b) ** 0.5 + (c * c + d * d) ** 0.5) / 2
            m = next(((i, t) for i, t in reversed(stack) if t is not None), (None, None))
            out.append(dict(x=e, y=f, w=w, h=abs(d) * size, mark=m[0], text=m[1], invisible=tr == 3))
    return out

def simulate(objs):
    lines, buf = [], []
    for ob in objs:
        if ob["w"] < 0.01:
            continue
        if not buf:
            buf.append(ob); continue
        prev = buf[-1]
        if abs(ob["y"] - prev["y"]) > max(prev["w"], ob["w"]) / 2:
            lines.append(buf); buf = [ob]; continue
        for i in range(len(buf), 0, -1):
            if ob["x"] >= buf[i - 1]["x"]:
                buf.insert(i, ob); break
        else:
            buf.insert(0, ob)
    if buf:
        lines.append(buf)
    findings = []
    for line in lines:
        runs = []
        for ob in line:
            if ob["mark"] is None:
                continue
            if not runs or runs[-1][0] != ob["mark"]:
                runs.append([ob["mark"], ob["text"], []])
            runs[-1][2].append(ob)
        count = Counter(r[0] for r in runs)
        for k, (m, t, obs) in enumerate(runs):
            if count[m] > 1 and k and any(r[0] == m for r in runs[:k]):
                intruder = runs[k - 1]
                findings.append(dict(text=t, repeats=count[m], intruder=intruder[1], intruder_invisible=all(o["invisible"] for o in intruder[2]), intruder_h=round(min(o["h"] for o in intruder[2]), 2)))
    return findings

if __name__ == "__main__":
    pdf = pikepdf.open(sys.argv[1])
    pages = [int(p) for p in sys.argv[2:]] or range(len(pdf.pages))
    total = 0
    for i in pages:
        f = simulate(objects(pdf.pages[i]))
        total += len(f)
        for x in f:
            print(i, x)
    print("re-emissions", total)
