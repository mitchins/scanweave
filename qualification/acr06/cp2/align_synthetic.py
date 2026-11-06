#!/usr/bin/env python3
"""ACR-06 CP2: assign and register CamScanner synthetic pages (sparse text defeats ORB) by scale-searched template matching.
Usage: align_synthetic.py <qualification dir> <aligned dir>"""
import sys, json
from pathlib import Path
import numpy as np, pikepdf
from PIL import Image
from skimage.feature import match_template
from skimage.transform import AffineTransform, warp

Q = Path(sys.argv[1]); OUT = Path(sys.argv[2])
doc = pikepdf.open(Q/'acr06/local/camscanner/web-out/synthetic300-p07.pdf')
cs = []; csbytes = []
for p in doc.pages:
    name = [o for o in pikepdf.parse_content_stream(p) if str(o.operator) == 'Do'][0].operands[0]
    csbytes.append(len(p.Resources.XObject[name].read_raw_bytes()))
    cs.append(np.asarray(pikepdf.PdfImage(p.Resources.XObject[name]).as_pil_image().convert('L'), dtype=float)/255)
src = [np.asarray(Image.open(Q/f'acr06/local/winvm/share/in/src/synthetic300-p{i:02}.png').convert('L'), dtype=float)/255 for i in range(8)]
F = 4
def small(a, s=1.0):
    im = Image.fromarray((a*255).astype(np.uint8)); return np.asarray(im.resize((max(1,round(im.width*s/F)), max(1,round(im.height*s/F))), Image.BILINEAR), dtype=float)/255
from scipy.optimize import linear_sum_assignment
cand = {}
for j, c in enumerate(cs):
    for i, s in enumerate(src):
        S = small(s)
        for scale in np.concatenate([np.arange(0.97, 1.031, 0.005), np.arange(1.50, 1.80, 0.01)]):
            T = small(c, 1/scale)  # CamScanner image expressed at source pixel scale
            if T.shape[0] > S.shape[0] or T.shape[1] > S.shape[1]: continue
            r = match_template(S, T); k = np.unravel_index(np.argmax(r), r.shape); v = r[k]
            if v > cand.get((j, i), (-1,))[0]: cand[(j, i)] = (float(v), i, float(scale), int(k[1]*F), int(k[0]*F))
score = np.array([[cand[(j, i)][0] for i in range(8)] for j in range(len(cs))])
print(np.round(score, 3))
rows, cols = linear_sum_assignment(-score)
best = {int(j): cand[(int(j), int(i))] for j, i in zip(rows, cols)}
recs = []
for j, (v, i, scale, x, y) in sorted(best.items()):
    # Map source px -> CamScanner px: cs = (src - offset) * scale
    model = AffineTransform(scale=scale, translation=(-x*scale, -y*scale))
    w = warp(cs[j], model, output_shape=src[i].shape, cval=1.0, order=1)
    Image.fromarray((w*255).round().astype(np.uint8)).save(OUT/f'synthetic-p{i}-camscanner.png')
    recs.append(dict(cs_page=j, source_page=i, ncc=round(v,4), scale_cs_px_per_src_px=round(scale,4), offset_src_px=[x, y], cs_px=list(cs[j].shape[::-1])))
    print(recs[-1], flush=True)
assert sorted(r['source_page'] for r in recs) == list(range(8)), 'assignment not one-to-one'
pj = json.loads((OUT/'pages.json').read_text())
for r in recs:
    e = next(p for p in pj if p['page'] == f"synthetic-p{r['source_page']}")
    e['camscanner'].update(page=r['cs_page'], registration='template-match', ncc=r['ncc'], scale_cs_px_per_src_px=r['scale_cs_px_per_src_px'], offset_src_px=r['offset_src_px'], image_px=r['cs_px'], jpeg_bytes=csbytes[r['cs_page']])
    for k in ('rotation_deg','registration_inliers','matches','image'): e['camscanner'].pop(k, None)
(OUT/'pages.json').write_text(json.dumps(pj, indent=1)+'\n')
