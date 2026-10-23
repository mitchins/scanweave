"""Independent B2' rescore: full-page analytic (PDFium 4x box-averaged) crops, neighbours included."""
import sys, json, numpy as np, pypdfium2 as pdfium
from pathlib import Path
R = Path('qualification/font04/local'); K = 4
points = sys.argv[1:]
snap = json.loads((R/f'financial-B2prime-{points[0]}.pdf.font04/source.json').read_text())['rows']
subs = {p: {a['member'] for a in json.loads((R/f'financial-B2prime-{p}.pdf.font04/plan.json').read_text())['assignments']} for p in points}
docs = {'src': Path('/tmp/claude-1000/-data-coding-scanweave/90ad46f6-35b7-4992-9197-11c0b1d47b0d/scratchpad/b2p/source-b2.pdf'), 'default': R/'financial-B2prime-default.pdf'} | {p: R/f'financial-B2prime-{p}.pdf' for p in points}
def page(path, i):
    b = pdfium.PdfDocument(str(path))[i].render(scale=300*K/72, grayscale=True)
    a = np.asarray(b.to_pil().convert('L'), np.float32); h, w = a.shape
    return 1 - a[:h//K*K, :w//K*K].reshape(h//K, K, w//K, K).mean((1, 3))/255
def err(s, x): return float(np.square(s-x).sum()/max(1., np.maximum(s, x).sum()))
out = []
for i in range(13):
    P = {k: page(v, i) for k, v in docs.items()}
    for r in snap:
        if r['page'] != i: continue
        x0, y0, x1, y1 = map(int, r['bbox']); sl = np.s_[max(0, y0-2):y1+2, max(0, x0-2):x1+2]
        rec = dict(member=r['index'], ch=r['character'], default=err(P['src'][sl], P['default'][sl]))
        for p in points: rec[p] = err(P['src'][sl], P[p][sl]); rec[p+'_sub'] = r['index'] in subs[p]
        out.append(rec)
    print('page', i, file=sys.stderr, flush=True)
json.dump(out, open(Path(sys.argv[0]).with_suffix('.json'), 'w'))
d = out
for p in points:
    a = np.array([x['default'] for x in d]); b = np.array([x[p] for x in d]); m = np.array([x[p+'_sub'] for x in d])
    print(f"{p}: all n={len(a)} mean {a.mean():.4f}->{b.mean():.4f} p95 {np.percentile(a,95):.4f}->{np.percentile(b,95):.4f} | subs n={m.sum()} mean {a[m].mean():.4f}->{b[m].mean():.4f} p95 {np.percentile(a[m],95):.4f}->{np.percentile(b[m],95):.4f} worse>0.02: {(b[m]-a[m]>.02).sum()} better>0.02: {(a[m]-b[m]>.02).sum()} max regression {(b-a).max():.4f}")
