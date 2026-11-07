import sys
from pathlib import Path
import numpy as np, pypdfium2 as pdfium
from PIL import Image, ImageDraw
from scipy.ndimage import uniform_filter
Q = Path('/data/coding/scanweave/qualification')
L = Q/'acr06/local/bg150'
OUT = Path(sys.argv[1]); OUT.mkdir(exist_ok=True)
def render(p, i, w):
    pg = pdfium.PdfDocument(str(p))[i]
    return pg.render(scale=w/pg.get_width()).to_pil().convert('L')
for spec in sys.argv[2:]:
    g, i = spec.split(':'); i = int(i)
    src = pdfium.PdfDocument(str(Q/f'pdf_packaging/groups/{g}-input.pdf'))[i]
    W = round(src.get_width()/72*300)
    s = render(Q/f'pdf_packaging/groups/{g}-input.pdf', i, W)
    d = render(L/f'baseline/{g}.pdf', i, W)
    u = render(L/f'unguarded/{g}.pdf', i, W)
    H = min(s.height, d.height, u.height)
    S, D, U = (np.asarray(x, dtype=np.float32)[:H] for x in (s, d, u))
    # where unguarded is further from source than default
    worse = uniform_filter(np.abs(U-S) - np.abs(D-S), size=(120, 360))
    y, x = np.unravel_index(np.argmax(worse), worse.shape)
    cw, ch = 720, 240
    x0 = int(np.clip(x-cw//2, 0, W-cw)); y0 = int(np.clip(y-ch//2, 0, H-ch))
    rows = [('source', s), ('default (~200 DPI bg)', d), ('unguarded 150 DPI bg', u)]
    sheet = Image.new('L', (cw*2, (ch*2+24)*3), 255); dr = ImageDraw.Draw(sheet)
    for k, (n, im) in enumerate(rows):
        dr.text((6, k*(ch*2+24)+6), f'{g} p{i+1} {n}  crop x={x0} y={y0} @300dpi, 2x', fill=0)
        sheet.paste(im.crop((x0, y0, x0+cw, y0+ch)).resize((cw*2, ch*2), Image.Resampling.NEAREST), (0, k*(ch*2+24)+24))
    sheet.save(OUT/f'{g}-p{i+1}.png'); print(g, i+1, x0, y0)
