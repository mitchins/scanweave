"""Diagnostic sensitivity only: shifts are never used to admit a glyph."""
import json,pathlib,numpy as np
from PIL import Image
E=pathlib.Path('/data/coding/scanweave/qualification/acr06/hvc41c');rows=json.loads((E/'font-control-ledger.json').read_text());out=[]
for r in rows:
 a=np.asarray(Image.open(r['panel']).convert('L'))[::4,::4];cw=a.shape[1]//4;x0,y0,x1,y1=map(int,r['ocr_box']);ww=x1-x0+6;hh=y1-y0+6;ref=a[20:20+hh,2*cw:2*cw+ww]>128;vec=a[20:20+hh,3*cw:3*cw+ww]>128;best=(-1,None)
 for dy in range(-2,3):
  for dx in range(-2,3):
   v=np.zeros_like(vec);y0=max(0,dy);y1=min(vec.shape[0],vec.shape[0]+dy);x0=max(0,dx);x1=min(vec.shape[1],vec.shape[1]+dx);v[y0:y1,x0:x1]=vec[y0-dy:y1-dy,x0-dx:x1-dx];u=int((ref|v).sum());iou=float((ref&v).sum()/u) if u else None
   if iou is not None and iou>best[0]:best=(iou,(dx,dy))
 out.append({'control':r['control'],'word_index':r['word_index'],'char_ocr_unverified':r['char_ocr_unverified'],'unshifted_iou':r['source_vs_font_mask_iou'],'diagnostic_best_iou':best[0],'diagnostic_best_shift':best[1],'note':'Diagnostic after inspection; never used for acceptance or threshold change.'})
(E/'alignment-diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print('diagnosed',len(out))
