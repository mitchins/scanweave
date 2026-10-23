"""Independent B1 re-score: native engines (reproduce) + renderer-neutral analytic reference."""
import sys, json, numpy as np, pypdfium2 as pdfium
from pathlib import Path
sys.path.insert(0, '/data/coding/scanweave')
from qualification.font04.metrics import render, measure
R = Path('qualification/font04/local')
art = R/'financial-experimental-v2.pdf.font04'
snap = json.loads((art/'source.json').read_text()); plan = json.loads((art/'plan.json').read_text())
accepted = {r['member'] for r in plan['assignments']}
K = 4
def analytic(path, page):
    d = pdfium.PdfDocument(str(path)); p = d[page]
    b = p.render(scale=300*K/72, grayscale=True); a = np.asarray(b.to_pil().convert('L'), dtype=np.float32)
    h, w = a.shape; a = a[:h//K*K, :w//K*K].reshape(h//K, K, w//K, K).mean((1, 3))
    return a  # 0..255, same convention as render()
def get(engine, path, page):
    return analytic(path, page) if engine == 'analytic' else render(path, page, 300, engine).astype(np.float32)
out = []
for engine in sys.argv[1:]:
    for page in range(13):
        src = 1 - get(engine, R/'financial-source-owned.pdf', page)/255
        A = 1 - get(engine, R/'financial-default-isolated-e.pdf', page)/255
        B = 1 - get(engine, R/'financial-experimental-isolated-e.pdf', page)/255
        hh = min(src.shape[0], A.shape[0], B.shape[0]); ww = min(src.shape[1], A.shape[1], B.shape[1])
        for row in snap['rows']:
            if row['page'] != page or row['source'] is None: continue
            x0, y0, x1, y1 = map(int, row['source']['bbox']); t, l, b_, r_ = y0-4, x0-4, y1+4, x1+4
            if b_ > hh or r_ > ww: continue
            out.append(dict(engine=engine, member=row['index'], accepted=row['index'] in accepted,
                            base=measure(src[t:b_, l:r_], A[t:b_, l:r_]), exp=measure(src[t:b_, l:r_], B[t:b_, l:r_])))
        print(engine, page, flush=True, file=sys.stderr)
json.dump(out, open(sys.argv[0] + '.' + '-'.join(sys.argv[1:]) + '.json', 'w'))
