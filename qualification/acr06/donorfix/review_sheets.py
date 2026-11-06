#!/usr/bin/env python3
"""Claude reviewer sheets: every changed row from panel-index.json, rendered at 300 DPI
(PDFium), word context, target glyph outlined, with per-row error vs source for main and
candidate. Writes local/donorfix/review/rNNNN.png and review-metrics.json."""
import json, math, sys, importlib.util
from pathlib import Path
from collections import defaultdict
import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("panels_src", here / "panels.py")
src = open(here / "panels.py").read()
# reuse source()/main_path() definitions without executing the panel build
ns = {}
exec(src.split("rows=[]")[0], ns)
source, main_path, local = ns["source"], ns["main_path"], ns["local"]
out = local / "review339"; out.mkdir(exist_ok=True)
rows = json.loads((here / "panel-index.json").read_text())
SCALE = 300 / 72
by_page = defaultdict(list)
for r in rows:
    by_page[(r["document"], r["page_index"])].append(r)
tiles, metrics = {}, {}
for (doc, pi), rs in sorted(by_page.items()):
    paths = [source(doc), main_path(doc), local / "candidate" / f"{doc}.pdf"]
    ims = [np.asarray(pdfium.PdfDocument(str(p))[pi].render(scale=SCALE).to_pil().convert("L"), dtype=np.int16) for p in paths]
    h = min(i.shape[0] for i in ims); w = min(i.shape[1] for i in ims)
    ims = [i[:h, :w] for i in ims]
    for r in rs:
        sx = w / r["raster_width"]; sy = h / r["raster_height"]
        boxes = [b for b in (r["observed_bbox"], r["old_bbox"], r["new_bbox"]) if b]
        g = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        gx0, gy0, gx1, gy1 = int(g[0] * sx) - 2, int(g[1] * sy) - 2, int(math.ceil(g[2] * sx)) + 2, int(math.ceil(g[3] * sy)) + 2
        gx0, gy0 = max(gx0, 0), max(gy0, 0)
        reg = [i[gy0:gy1, gx0:gx1] for i in ims]
        em = float(np.abs(reg[1] - reg[0]).mean()) if reg[0].size else 0.0
        ec = float(np.abs(reg[2] - reg[0]).mean()) if reg[0].size else 0.0
        dmc = float(np.abs(reg[2] - reg[1]).mean()) if reg[0].size else 0.0
        # word context
        cb = r["crop_bbox"]
        pad = 6
        cx0, cy0 = max(int(cb[0] * sx) - pad, 0), max(int(cb[1] * sy) - pad, 0)
        cx1, cy1 = min(int(math.ceil(cb[2] * sx)) + pad, w), min(int(math.ceil(cb[3] * sy)) + pad, h)
        # cap context height/width for tile size
        crops = []
        for i in ims:
            c = Image.fromarray(np.uint8(np.clip(i[cy0:cy1, cx0:cx1], 0, 255))).convert("RGB")
            d = ImageDraw.Draw(c)
            d.rectangle([gx0 - cx0, gy0 - cy0, gx1 - cx0 - 1, gy1 - cy0 - 1], outline=(220, 0, 0))
            crops.append(c)
        tiles[r["number"]] = crops
        metrics[r["number"]] = dict(err_main=round(em, 2), err_cand=round(ec, 2), main_vs_cand=round(dmc, 2))
(here / "review-metrics.json").write_text(json.dumps(metrics, indent=1) + "\n")
order = sorted([r for r in rows if metrics[r["number"]]["main_vs_cand"] > 0], key=lambda r: r["number"])
MAXW, TH, CW = 2400, 120, 1190
def norm(c):
    s = TH / c.height
    if c.width * s > 380: s = 380 / c.width
    s = max(min(s, 4.0), 0.25)
    return c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.Resampling.LANCZOS)
pages, cur, y, col = [], None, 0, 0
for r in order:
    m = metrics[r["number"]]
    ts = [norm(c) for c in tiles[r["number"]]]
    rh = max(t.height for t in ts) + 18
    if cur is None or y + rh > 2200:
        if cur is not None and col == 0:
            col, y = 1, 0
        else:
            if cur is not None: pages.append(cur)
            cur = Image.new("RGB", (MAXW, 2200), "white"); y = 0; col = 0
    d = ImageDraw.Draw(cur)
    x0 = col * (CW + 20)
    if col: d.line([(CW + 9, 0), (CW + 9, 2200)], fill=(150, 150, 150))
    d.text((x0 + 2, y + 2), f"#{r['number']} {r['document']} p{r['page_index']} {r['symbol_id']} '{r['text']}' {r['old_decision'][:12]}->{r['new_decision'][9:]} {r['new_owner'][:3]} eM={m['err_main']} eC={m['err_cand']}", fill=(0, 0, 160))
    x = x0
    for t in ts:
        cur.paste(t, (x, y + 16)); x += t.width + 10
    y += rh
pages.append(cur)
for i, p in enumerate(pages, 1):
    p.save(out / f"r{i:03}.png", optimize=True)
print("rows", len(order), "pages", len(pages))
worse = [n for n, m in metrics.items() if m["err_cand"] > m["err_main"] + 3]
print("cand worse >3:", len(worse), worse[:50])
