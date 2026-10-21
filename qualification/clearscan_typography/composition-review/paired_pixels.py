#!/usr/bin/env python3
"""Read-only pixel attribution for frozen S4/S5 300 DPI pages.

Uses Poppler's integer-DPI renders and existing pristine/source PNGs. It does
not regenerate or alter any canonical evaluation artifact.
"""
import json
import math
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import pypdfium2 as pdfium

VECTOR_ONLY_PDF = 'stages/S4-vector-only.pdf'
COMPETITIVE_PDF = 'qualification/clearscan_competitive/300/clearscan.pdf'


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "qualification/clearscan_competitive/300/final"
ORACLE = ROOT / "qualification/experiments/m1g/fixture/dpi300/oracle"
SOURCE = ROOT / "qualification/experiments/m1g/fixture/dpi300/input"
STAGES = json.loads((BASE / "stages/stage-errors.json").read_text())['occurrences']
OUT = Path(__file__).resolve().parent
POP_TEMP = Path(tempfile.mkdtemp(prefix='scanweave-comp-poppler-'))
for label,path in [('S4',BASE/VECTOR_ONLY_PDF),('S5',ROOT/COMPETITIVE_PDF)]:
    subprocess.run(['pdftoppm','-r','300','-png','-gray',str(path),str(POP_TEMP/label)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def gray(path):
    return np.asarray(Image.open(path).convert('L'), dtype=np.uint8)

def iou(a, b):
    aa, bb = a < 170, b < 170
    u = np.count_nonzero(aa | bb)
    return float(np.count_nonzero(aa & bb) / u) if u else 1.0

def sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()

rows = []
pdfs = {
 'S4': pdfium.PdfDocument(str(BASE/VECTOR_ONLY_PDF)),
 'S5': pdfium.PdfDocument(str(ROOT/COMPETITIVE_PDF)),
 'raster_only': pdfium.PdfDocument(str(BASE/'raster-only.pdf')),
}
for page in range(8):
    truth_doc = json.loads((ORACLE / f'page{page:02d}.truth.json').read_text())
    truth_records = {r['id']:r for r in truth_doc['records']}
    truth_img = gray(ORACLE / f'page{page:02d}.png')
    src_img = gray(SOURCE / f'page{page:02d}.png')
    # pdftoppm -r 300 gives one-based page suffixes.
    # Exact-size PDFium. The companion Poppler renders are made by the
    # documented integer-DPI command below and retained for cross-checking.
    s4 = np.asarray(pdfs['S4'][page].render(scale=math.nextafter(300/72,0.0)).to_pil().convert('L'))[:truth_img.shape[0],:truth_img.shape[1]]
    s5 = np.asarray(pdfs['S5'][page].render(scale=math.nextafter(300/72,0.0)).to_pil().convert('L'))[:truth_img.shape[0],:truth_img.shape[1]]
    raster = np.asarray(pdfs['raster_only'][page].render(scale=math.nextafter(300/72,0.0)).to_pil().convert('L'))[:truth_img.shape[0],:truth_img.shape[1]]
    pop4=gray(POP_TEMP/f'S4-{page+1}.png')[:truth_img.shape[0],:truth_img.shape[1]]
    pop5=gray(POP_TEMP/f'S5-{page+1}.png')[:truth_img.shape[0],:truth_img.shape[1]]
    for o in STAGES:
        if o['page'] != page: continue
        rec = truth_records.get(o['id'])
        if not rec: continue
        x0,y0,x1,y1 = map(int, rec['bbox'])
        # Match the benchmark's five-pixel guard, excluding most adjacent ink.
        x0+=5; y0+=5; x1-=5; y1-=5
        if x1<=x0 or y1<=y0: continue
        a,b,t,s,r = (im[y0:y1,x0:x1] for im in (s4,s5,truth_img,src_img,raster))
        ad,bd,td,sd = a<170,b<170,t<170,s<170
        removed = ad & ~bd
        added = ~ad & bd
        # Under a white page, S4's vector coverage is approximately 1-S4/255.
        # Replacing white with the raster-only sample predicts S5 ~= S4*raster/255.
        predicted = a.astype(np.float32) * r.astype(np.float32) / 255.0
        rows.append({
            'page':page, 'id':o['id'], 'text':o['text'], 'truth_bbox_inset5':[x0,y0,x1,y1],
            'S4_IoU':iou(a,t), 'S5_IoU':iou(b,t), 'delta_IoU':iou(b,t)-iou(a,t),
            'S4_dark':int(ad.sum()), 'S5_dark':int(bd.sum()), 'truth_dark':int(td.sum()),
            'removed_dark':int(removed.sum()),
            'removed_that_was_pristine_ink':int((removed & td).sum()),
            'removed_that_was_source_ink':int((removed & sd).sum()),
            'added_dark':int(added.sum()),
            'added_that_is_pristine_ink':int((added & td).sum()),
            'added_that_was_source_ink':int((added & sd).sum()),
            'added_present_in_raster_only':int((added & (r<170)).sum()),
            'added_raster_only_lt200':int((added & (r<200)).sum()),
            'added_raster_only_lt240':int((added & (r<240)).sum()),
            'added_raster_only_mean':float(r[added].mean()) if added.any() else None,
            'added_S4_mean':float(a[added].mean()) if added.any() else None,
            'added_S5_mean':float(b[added].mean()) if added.any() else None,
            'added_blend_prediction_mae':float(np.abs(b[added].astype(np.float32)-predicted[added]).mean()) if added.any() else None,
            'added_source_intensity_mean':float(s[added].mean()) if added.any() else None,
            'added_source_intensity_lt200':int((added & (s<200)).sum()),
            'added_source_intensity_lt240':int((added & (s<240)).sum()),
            'mean_abs_gray_delta':float(np.abs(a.astype(np.int16)-b.astype(np.int16)).mean()),
            'abs_gray_delta_sum':int(np.abs(a.astype(np.int16)-b.astype(np.int16)).sum()),
            'abs_error_vs_background_blend_sum':int(np.abs(b.astype(np.float32)-predicted).sum()),
            'abs_error_vs_white_background_sum':int(np.abs(b.astype(np.float32)-a.astype(np.float32)).sum()),
            'stage_record_delta':o['composition_delta'],
            'Poppler_S4_IoU':iou(pop4[y0:y1,x0:x1],t), 'Poppler_S5_IoU':iou(pop5[y0:y1,x0:x1],t),
            'Poppler_delta_IoU':iou(pop5[y0:y1,x0:x1],t)-iou(pop4[y0:y1,x0:x1],t),
            'Poppler_changed_pixels':int(np.count_nonzero(pop4[y0:y1,x0:x1]!=pop5[y0:y1,x0:x1])),
            'Poppler_threshold_changes':int(np.count_nonzero((pop4[y0:y1,x0:x1]<170)!=(pop5[y0:y1,x0:x1]<170))),
        })

def summarize(items):
    keys=('removed_dark','removed_that_was_pristine_ink','removed_that_was_source_ink',
          'added_dark','added_that_is_pristine_ink','added_that_was_source_ink','abs_gray_delta_sum')
    return {k:sum(x[k] for x in items) for k in keys} | {
      'n':len(items), 'mean_IoU_S4':float(np.mean([x['S4_IoU'] for x in items])),
      'mean_IoU_S5':float(np.mean([x['S5_IoU'] for x in items])),
      'mean_delta_IoU':float(np.mean([x['delta_IoU'] for x in items]))}

result={
 'inputs':{
  'S4_pdf_sha256':sha(BASE/VECTOR_ONLY_PDF),
  'S5_pdf_sha256':sha(ROOT/COMPETITIVE_PDF),
  'raster_only_pdf_sha256':sha(BASE/'raster-only.pdf'),
  'render_command':'PDFium scale=nextafter(300/72,0); cross-check Poppler pdftoppm -r 300', 'threshold':170,
  'crop':'pristine truth bbox inset 5 px (benchmark isolated glyph crop)',
  'pristine_sha256':{str(p):sha(ORACLE/f'page{p:02d}.png') for p in range(8)},
  'source_sha256':{str(p):sha(SOURCE/f'page{p:02d}.png') for p in range(8)},
  'pdfium_version':str(pdfium.PDFIUM_INFO)},
 'page_summaries':{str(p):summarize([x for x in rows if x['page']==p]) for p in range(8)},
 'renderer_summary':{r:{'n':len(rows),'mean_S4_IoU':float(np.mean([x[f'{r}_S4_IoU'] for x in rows])),'mean_S5_IoU':float(np.mean([x[f'{r}_S5_IoU'] for x in rows])),'mean_delta':float(np.mean([x[f'{r}_delta_IoU'] for x in rows])),'changed_pixels':sum(x.get(f'{r}_changed_pixels',0) for x in rows),'threshold_changes':sum(x.get(f'{r}_threshold_changes',0) for x in rows)} for r in ['Poppler']},
 'selected_occurrences':rows,
 'interpretation':'Changed dark pixels are tested independently against pristine truth and source scan. Truth-inset crops reduce neighboring-glyph contamination; rasterized rendering antialias values are also summarized as absolute grayscale delta.'
}
(OUT/'paired-pixels.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({p:v for p,v in result['page_summaries'].items()},indent=2))
for r in sorted(rows,key=lambda x:x['delta_IoU'])[:12]:
 print(r['page'],r['id'],repr(r['text']),'IoU',round(r['S4_IoU'],3),round(r['S5_IoU'],3),
       'add',r['added_dark'],'truth',r['added_that_is_pristine_ink'],'source<200/<240',r['added_source_intensity_lt200'],r['added_source_intensity_lt240'],
       'raster_only',r['added_present_in_raster_only'])
