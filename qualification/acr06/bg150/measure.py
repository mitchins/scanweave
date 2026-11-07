#!/usr/bin/env python3
"""Per-page OCR and visual proxies for source/default/experimental PDFs."""
import argparse
import collections
import json
import re
import subprocess
import tempfile
import sys
from pathlib import Path
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage
from skimage.metrics import structural_similarity
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/cp3')
from bytes import placements

Image.MAX_IMAGE_PIXELS = None
P = argparse.ArgumentParser()
P.add_argument('source'); P.add_argument('default'); P.add_argument('candidate'); P.add_argument('output')
P.add_argument('--pages', default='')
A = P.parse_args()
docs = [pdfium.PdfDocument(x) for x in (A.source, A.default, A.candidate)]
pdfs = [pikepdf.open(x) for x in (A.default,A.candidate)]
selected = [int(v)-1 for v in A.pages.split(',')] if A.pages else range(len(docs[0]))

def ocr(im):
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        im.save(f.name)
        p = subprocess.run(['tesseract',f.name,'-','--psm','3','-l','eng'], capture_output=True,text=True,check=True)
    return collections.Counter(re.findall(r'[A-Za-z0-9]{2,}',p.stdout))

def ocr_result(ref, default, candidate):
    d = ref & default; c = ref & candidate
    return {'source_words':sum(ref.values()), 'default_recalled':sum(d.values()), 'candidate_recalled':sum(c.values()),
            'lost_source_words':sorted((d-c).elements()), 'gained_source_words':sorted((c-d).elements()),
            'all_lost_words':sorted((default-candidate).elements()), 'all_gained_words':sorted((candidate-default).elements())}

def background(pg):
    images = [x for x in (pg.get('/Resources',{}).get('/XObject') or {}).values() if x.get('/Subtype') == '/Image']
    if not images: return None
    image = max(images,key=lambda x:int(x.Width)*int(x.Height))
    if str(image.get('/Filter')) != '/DCTDecode': return None
    placed = collections.defaultdict(list)
    placements(pg, [1,0,0,1,0,0], placed)
    mb=[float(x) for x in pg.mediabox]
    area=(mb[2]-mb[0])*(mb[3]-mb[1])
    if max(placed.get(image.objgen, [0])) < area * .95: return None
    return image

def render(doc, i):
    return doc[i].render(scale=300/72).to_pil().convert('RGB')

def fit(im, size):
    return im if im.size == size else im.resize(size,Image.Resampling.BICUBIC)

def metrics(source, default, candidate):
    s = np.asarray(source.convert('L'),dtype=np.float32)
    d = np.asarray(fit(default,source.size).convert('L'),dtype=np.float32)
    c = np.asarray(fit(candidate,source.size).convert('L'),dtype=np.float32)
    paper = ndimage.gaussian_filter(s, sigma=16)
    ink = paper-s > 30
    lab,n = ndimage.label(ink)
    counts = np.bincount(lab.ravel())[1:]
    ids = np.flatnonzero((counts>=2)&(counts<=20))+1
    def survival(a):
        if len(ids)==0: return None
        return float(np.mean(ndimage.maximum(paper-a,labels=lab,index=ids)>=30))
    horizontal = ndimage.binary_opening(ink,structure=np.ones((1,12),dtype=bool))
    vertical = ndimage.binary_opening(ink,structure=np.ones((12,1),dtype=bool))
    lines = horizontal | vertical
    def continuity(a):
        return float(np.mean((paper-a)[lines]>=20)) if lines.any() else None
    sm = lambda a: np.asarray(Image.fromarray(a.astype('uint8')).resize((max(1,source.width//4),max(1,source.height//4)),Image.Resampling.BOX))
    ds,dd,dc = map(sm,(s,d,c))
    diff = np.abs(d-c)
    return {'small_components_2_to_20px':len(ids), 'small_survival_default':survival(d),'small_survival_candidate':survival(c),
            'line_pixels':int(lines.sum()),'line_continuity_default':continuity(d),'line_continuity_candidate':continuity(c),
            'ssim_default':float(structural_similarity(ds,dd,data_range=255)), 'ssim_candidate':float(structural_similarity(ds,dc,data_range=255)),
            'whole_render_mean_abs_diff':float(diff.mean()),'whole_render_max_abs_diff':float(diff.max()),'whole_render_changed_pixels':int((diff>0).sum()),
            'note':'Small components and lines are threshold proxies, not semantic classifications; SSIM is whole-page at quarter scale.'}

out = {'source':A.source,'default':A.default,'candidate':A.candidate,'pages':[]}
for i in selected:
    ims = [render(d,i) for d in docs]
    ims[1:] = [fit(x,ims[0].size) for x in ims[1:]]
    refs = [ocr(im) for im in ims]
    row = {'page':i+1,'complete_ocr':ocr_result(*refs),'visual':metrics(*ims)}
    bgs = [background(p.pages[i]) for p in pdfs]
    if all(x is not None for x in bgs):
        bgims = [fit(pikepdf.PdfImage(x).as_pil_image().convert('RGB'),ims[0].size) for x in bgs]
        row['background_ocr'] = ocr_result(refs[0],*[ocr(x) for x in bgims])
        row['backgrounds'] = [{'width':int(x.Width),'height':int(x.Height),'bytes':len(x.read_raw_bytes())} for x in bgs]
    out['pages'].append(row)
    Path(A.output).write_text(json.dumps(out,indent=2)+'\n')
    print(f'{A.output}: page {i+1}',flush=True)
