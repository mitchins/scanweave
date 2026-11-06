#!/usr/bin/env python3
"""Measure page-wide ink against pristine typography at the original image size."""
import json
from pathlib import Path
import numpy as np,pypdfium2 as pdfium
from PIL import Image
q=Path('/data/coding/scanweave/qualification/acr06');loc=q/'local/donorfix';out=[]
for dataset in ('fresh','fresh2'):
 for i,name in enumerate(('200','300','600','fractional')):
  truth=np.asarray(Image.open(loc/dataset/f'truth-{i}.png').convert('L'))<128;h,w=truth.shape;row={'dataset':dataset,'name':name,'truth_pixels':int(truth.sum()),'variants':{}}
  for mode in ('main','candidate'):
   d=pdfium.PdfDocument(str(loc/mode/f'{dataset}-{name}.pdf'));p=d[0];im=np.asarray(p.render(scale=(w-0.0001)/p.get_width()).to_pil().convert('L'));shape=list(im.shape)
   if im.shape!=truth.shape:row['variants'][mode]={'shape':shape,'error':'size mismatch'};continue
   m=im<128;inter=int((m&truth).sum());union=int((m|truth).sum());row['variants'][mode]={'shape':shape,'iou':inter/union if union else None,'false_positive_pixels':int((m&~truth).sum()),'false_negative_pixels':int((~m&truth).sum())}
  out.append(row)
(q/'donorfix/fresh-quality.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
