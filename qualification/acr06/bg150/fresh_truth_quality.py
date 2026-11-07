#!/usr/bin/env python3
"""Compare frozen pristine text and line truth with the fresh PDF renders."""
import collections,json,re,subprocess,tempfile
from pathlib import Path
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage
from skimage.metrics import structural_similarity
q=Path('/data/coding/scanweave/qualification');root=q/'acr06/local/bg150'; m=json.loads((root/'fresh-truth/manifest.json').read_text()); out={}
for i,page in enumerate(m['pages'],1):
 name=f'freshtruth{i}'; truth=Image.open(page['pristine_png']).convert('L'); dims=truth.size; clean=np.asarray(truth)
 paths=[page['pdf'],str(root/'baseline'/f'{name}.pdf'),str(root/'candidate'/f'{name}.pdf')]
 imgs=[pdfium.PdfDocument(p)[0].render(scale=300/72).to_pil().convert('L').resize(dims,Image.Resampling.BICUBIC) for p in paths]
 arrays=[np.asarray(im,dtype=np.float32) for im in imgs]; truth_words=collections.Counter(re.findall(r'[A-Za-z0-9]{2,}',' '.join(page['text_truth'])))
 def ocr(im):
  with tempfile.NamedTemporaryFile(suffix='.png') as f:
   im.save(f.name); s=subprocess.run(['tesseract',f.name,'-','--psm','3','-l','eng'],check=True,capture_output=True,text=True).stdout
  return collections.Counter(re.findall(r'[A-Za-z0-9]{2,}',s))
 got=[ocr(im) for im in imgs]; textmask=np.zeros(clean.shape,bool)
 for x0,y0,x1,y1 in page['text_boxes_pixels']: textmask[y0:y1,x0:x1]=True
 ink=(clean<80)&textmask; lab,n=ndimage.label(ink); areas=np.bincount(lab.ravel())[1:]; ids=np.flatnonzero((areas>=2)&(areas<=100))+1
 line=np.zeros(clean.shape,bool)
 for y in range(1900,2401,62): line[y:y+2,150:1900]=True
 for x in range(150,1901,350): line[1900:2397,x:x+2]=True
 rows=[]
 for label,a,counter in zip(['source','default','candidate'],arrays,got):
  paper=ndimage.gaussian_filter(a,sigma=16); contrast=paper-a
  surv=float(np.mean(ndimage.maximum(contrast,labels=lab,index=ids)>=30)) if len(ids) else None
  crop=lambda z:z[2520:3090,150:1950]
  rows.append({'arm':label,'truth_words':sum(truth_words.values()),'recalled_truth_words':sum((truth_words&counter).values()),'truth_words_not_recalled':sorted((truth_words-counter).elements()),'unmatched_ocr_tokens':sorted((counter-truth_words).elements()),'small_truth_components':len(ids),'small_truth_component_survival':surv,'truth_line_pixel_continuity':float(np.mean(contrast[line]>=20)), 'artwork_ssim':float(structural_similarity(crop(clean),crop(a.astype('uint8')),data_range=255))})
 out[name]=rows; (q/'acr06/bg150/fresh-truth-quality.json').write_text(json.dumps(out,indent=2)+'\n'); print(name,flush=True)
