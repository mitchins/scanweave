"""Analyse the Windows Reader captures: text equality vs default, and within-renderer
default-vs-candidate differences in Reader compared with the same differences in pinned PDFium."""
import json, sys, os, hashlib
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from pdfium_render import render

W = '/data/coding/scanweave/qualification/font04/local/winvm/share'
R = W + '/out/reader'
OUT = '/data/coding/scanweave/qualification/font04/local/reader-win/analysis/out'
os.makedirs(OUT, exist_ok=True)
DOCS = {'financial': (13, ['cover-2.0', 'cover-1.5']), 'mixed': (2, ['cover-2.0'])}
CANVAS = (85, 1385)          # y-range of the document canvas in a 1920x1440 capture
SIDE = (60, 1860)            # x-range (exclude left tool strip and right rail)

def gray(p): return np.asarray(Image.open(p).convert('L'), dtype=np.int16)
def page_rect(img):
    """Bounding box of non-white content inside the canvas (page background or ink)."""
    c = img[CANVAS[0]:CANVAS[1], SIDE[0]:SIDE[1]]
    ys, xs = np.where(c < 250)
    return (SIDE[0] + xs.min(), CANVAS[0] + ys.min(), SIDE[0] + xs.max() + 1, CANVAS[0] + ys.max() + 1)
POPUP = (1540, 0, 1920, 220)   # 'Reopen closed PDFs' notice area (UI, not document)
def register(screen, ref):
    """Place the PDFium render on the Reader capture: best integer offset near the fit-centred guess."""
    h, w = ref.shape; gx = (SIDE[0] + SIDE[1]) // 2 - w // 2 + 8; gy = CANVAS[0]
    best = None
    for dy in range(-4, 5):
        for dx in range(-24, 25):
            x, y = gx + dx, gy + dy
            if x < 0 or y < 0 or y + h > screen.shape[0] or x + w > screen.shape[1]: continue
            v = np.abs(screen[y:y + h:4, x:x + w:4] - ref[::4, ::4]).mean()
            if best is None or v < best[0]: best = (v, x, y)
    return best[1], best[2]
def masked(img, x0, y0):
    """Copy of a page crop with the popup area (screen coords) blanked."""
    a = img.copy(); px0, py0, px1, py1 = POPUP
    a[max(0, py0 - y0):max(0, py1 - y0), max(0, px0 - x0):max(0, px1 - x0)] = 255
    return a
def ink_bbox(a, thr=110):
    ys, xs = np.where(a < thr); return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
def diffstats(a, b):
    d = np.abs(a - b)
    return {'mean_abs': round(float(d.mean()), 3), 'frac_gt64': round(float((d > 64).mean()), 6), 'max': int(d.max())}

report = {'text': [], 'fit': [], 'zoom400': []}
for doc, (n, cands) in DOCS.items():
    for p in range(1, n + 1):
        t0 = open(f'{R}/{doc}-default-p{p:02d}.txt', encoding='utf-8').read()
        for c in cands:
            t1 = open(f'{R}/{doc}-{c}-p{p:02d}.txt', encoding='utf-8').read()
            report['text'].append({'doc': doc, 'variant': c, 'page': p, 'len_default': len(t0), 'len_candidate': len(t1),
                                   'equal': t0 == t1, 'sha_default': hashlib.sha256(t0.encode()).hexdigest()[:16]})
        # fit renders
        rd = gray(f'{R}/{doc}-default-p{p:02d}-fit.png')
        pdf0 = f'{W}/in/{doc}-default.pdf'
        _, (pw, ph) = render(pdf0, p - 1, 0.1)
        scale = (CANVAS[1] - CANVAS[0]) / ph
        pd = np.asarray(Image.fromarray(render(pdf0, p - 1, scale)[0]).convert('L'), dtype=np.int16)
        x0, y0 = register(rd, pd)
        y1, x1 = y0 + pd.shape[0], x0 + pd.shape[1]
        for c in cands:
            rc = gray(f'{R}/{doc}-{c}-p{p:02d}-fit.png')
            pc = np.asarray(Image.fromarray(render(f'{W}/in/{doc}-{c}.pdf', p - 1, scale)[0]).convert('L'), dtype=np.int16)
            ra, rb = masked(rd[y0:y1, x0:x1], x0, y0), masked(rc[y0:y1, x0:x1], x0, y0)
            h, w = min(ra.shape[0], pd.shape[0]), min(ra.shape[1], pd.shape[1])
            entry = {'doc': doc, 'variant': c, 'page': p, 'page_rect': [int(x0), int(y0), int(x1), int(y1)], 'scale_px_per_pt': round(scale, 4),
                     'reader_default_vs_candidate': diffstats(ra, rb), 'pdfium_default_vs_candidate': diffstats(pd, pc),
                     'reader_vs_pdfium_default': diffstats(ra[:h, :w], pd[:h, :w]), 'reader_vs_pdfium_candidate': diffstats(rb[:h, :w], pc[:h, :w])}
            report['fit'].append(entry)
            # diff visual: Reader diff | PDFium diff
            dr = np.clip(np.abs(ra - rb) * 4, 0, 255).astype(np.uint8); dp = np.clip(np.abs(pd - pc) * 4, 0, 255).astype(np.uint8)
            hh = max(dr.shape[0], dp.shape[0]); canvas = np.zeros((hh, dr.shape[1] + dp.shape[1] + 10), np.uint8)
            canvas[:dr.shape[0], :dr.shape[1]] = dr; canvas[:dp.shape[0], dr.shape[1] + 10:] = dp
            Image.fromarray(255 - canvas).save(f'{OUT}/{doc}-{c}-p{p:02d}-diff-reader-vs-pdfium.png')
        # zoom crops: within-Reader default vs candidate
        zd = masked(gray(f'{R}/{doc}-default-p{p:02d}-zoom400.png'), 0, 0)[CANVAS[0]:CANVAS[1], SIDE[0]:SIDE[1]]
        for c in cands:
            zc = masked(gray(f'{R}/{doc}-{c}-p{p:02d}-zoom400.png'), 0, 0)[CANVAS[0]:CANVAS[1], SIDE[0]:SIDE[1]]
            report['zoom400'].append({'doc': doc, 'variant': c, 'page': p, 'reader_default_vs_candidate': diffstats(zd, zc)})
json.dump(report, open(f'{OUT}/analysis.json', 'w'), indent=1)
neq = [t for t in report['text'] if not t['equal']]
print('text pages compared', len(report['text']), 'unequal', len(neq))
for e in report['fit']:
    print(e['doc'], e['variant'], e['page'], 'R', e['reader_default_vs_candidate'], 'P', e['pdfium_default_vs_candidate'],
          'RvP-def', e['reader_vs_pdfium_default']['mean_abs'], 'RvP-cand', e['reader_vs_pdfium_candidate']['mean_abs'])
for e in report['zoom400']: print('zoom', e['doc'], e['variant'], e['page'], e['reader_default_vs_candidate'])
