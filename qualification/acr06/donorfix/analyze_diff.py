#!/usr/bin/env python3
import json,math,sys
from pathlib import Path
import numpy as np,pypdfium2 as pdfium
from PIL import Image
from scipy.ndimage import distance_transform_edt,label,find_objects
local=Path('/data/coding/scanweave/qualification/acr06/local/donorfix');name=sys.argv[1];pi=int(sys.argv[2]);rows=[r for r in json.load(open(local/'panels/index.json')) if r['document']==name and r['page_index']==pi]; main=local/'main'/f'{name}.pdf'; main=main if main.exists() else local/'baseline'/('single.pdf' if name=='single' else f'{name}-off.pdf');cand=local/'candidate'/f'{name}.pdf';
def render(p):
 d=pdfium.PdfDocument(str(p));return np.array(d[pi].render(scale=150/72).to_pil().convert('RGB')).astype('int16')
a=render(main);b=render(cand);h,w=a.shape[:2];sx=w/rows[0]['raster_width'];sy=h/rows[0]['raster_height'];near=np.zeros((h,w),bool)
for r in rows:
 for box in (r['observed_bbox'],r['old_bbox'],r['new_bbox']):
  if box:
   x0=max(0,math.floor(box[0]*sx));x1=min(w,math.ceil(box[2]*sx));y0=max(0,math.floor(box[1]*sy));y1=min(h,math.ceil(box[3]*sy));near[y0:y1,x0:x1]=True
D=np.max(abs(a-b),axis=2); dist=distance_transform_edt(~near);d={}
for margin in (2,4,8,16,32):
 d[str(margin)]={str(th):int(((D>th)&(dist>margin)).sum()) for th in (0,2,8,24,64)}
img=np.zeros((h,w,3),np.uint8);img[:,:,0]=np.clip(D*4,0,255);img[:,:,1]=np.where(near,100,0);Image.fromarray(img).save(local/f'diff-{name}-{pi}.png')
print(json.dumps({'document':name,'page_index':pi,'counts_by_render_px_distance_and_intensity':d,'max_delta':int(D.max()),'changed_rows':len(rows)},indent=2))
