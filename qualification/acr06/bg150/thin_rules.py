#!/usr/bin/env python3
"""One/two-pixel source-line contrast and continuity, at 300 DPI."""
import json
from pathlib import Path
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage
q=Path('/data/coding/scanweave/qualification');root=q/'acr06/local/bg150';e=q/'acr06/bg150'
groups=['financial','forms','historical','mixed','receipts']
sources={g:q/f'pdf_packaging/groups/{g}-input.pdf' for g in groups}
sources.update(single=q/'pdf_packaging/real/input/scan-c03-29.pdf',competitive300=q/'clearscan_competitive/300/source.pdf',competitive600=q/'clearscan_competitive/600/source.pdf',fresh1=root/'fresh/page-1.pdf',fresh2=root/'fresh/page-2.pdf',freshtruth1=root/'fresh-truth/page-1.pdf',freshtruth2=root/'fresh-truth/page-2.pdf')
result={}
for name,path in sources.items():
 arms=['default','candidate']+(['unguarded'] if name in groups else [])
 pdfs=[pdfium.PdfDocument(str(path))]+[pdfium.PdfDocument(str(root/('baseline' if a=='default' else a)/f'{name}.pdf')) for a in arms]
 rows=[]
 for i in range(len(pdfs[0])):
  ims=[pdf[i].render(scale=300/72).to_pil().convert('L') for pdf in pdfs]; size=ims[0].size
  arrays=[np.asarray(im if im.size==size else im.resize(size,Image.Resampling.BICUBIC),dtype=np.float32) for im in ims]
  paper=ndimage.gaussian_filter(arrays[0],sigma=16); ink=paper-arrays[0]>30
  horiz=ndimage.binary_opening(ink,structure=np.ones((1,12),bool)); vert=ndimage.binary_opening(ink,structure=np.ones((12,1),bool))
  hthin=horiz&(ndimage.convolve(ink.astype('uint8'),np.ones((5,1),dtype='uint8'),mode='constant')<=2)
  vthin=vert&(ndimage.convolve(ink.astype('uint8'),np.ones((1,5),dtype='uint8'),mode='constant')<=2)
  mask=hthin|vthin; row={'page':i+1,'source_line_pixels':int(mask.sum()),'arms':{}}
  for arm,a in zip(['source']+arms,arrays):
   contrast=(paper-a)[mask]
   row['arms'][arm]={'mean_contrast':float(contrast.mean()) if contrast.size else None,'continuity_20_levels':float((contrast>=20).mean()) if contrast.size else None}
  rows.append(row)
 result[name]=rows; (e/'thin-rules.json').write_text(json.dumps(result,indent=2)+'\n'); print(name,flush=True)
