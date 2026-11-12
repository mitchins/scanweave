"""Collate renderer crops with explicit global pixel coordinates and make grids."""
import json,hashlib,pathlib
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';engines=['splash-default','splash-aa','splash-noaa','cairo','pdfium','mupdf'];variants=['A0','A1','A2','A3'];sha=lambda b:hashlib.sha256(b).hexdigest()
def get(v,i,e,d):return json.loads((L/f'{v}-{i:03}-{e}-{d}.json').read_text())
def align(m,b,shape):
 a=np.zeros(shape,bool);x0,y0,x1,y1=b;a[y0:y1,x0:x1]=m;return a
out=[]
for dpi in (96,300):
 for i in (243,38,18):
  a0=get('A0',i,'pdfium',dpi);refc=[a0['centroid_xy'][0]+a0['crop_box_render_pixels'][0],a0['centroid_xy'][1]+a0['crop_box_render_pixels'][1]]
  for v in variants:
   ref=get(v,i,'pdfium',dpi);rm=np.asarray(Image.open(L/f'{v}-{i:03}-pdfium-{dpi}-mask.png'))>0
   for eng in engines:
    rec=get(v,i,eng,dpi);m=np.asarray(Image.open(L/f'{v}-{i:03}-{eng}-{dpi}-mask.png'))>0
    bx=rec['crop_box_render_pixels'];br=ref['crop_box_render_pixels'];shape=(max(bx[3],br[3]),max(bx[2],br[2]));u=align(m,bx,shape);q=align(rm,br,shape);union=(u|q).sum();rec['iou_against_same_variant_pdfium']=float((u&q).sum()/union) if union else None
    rec['centroid_offset_against_A0_pdfium']=[float(rec['centroid_xy'][j]+bx[j]-refc[j]) for j in (0,1)] if rec['centroid_xy'] else None;out.append(rec)
(E/'phase-a-metrics.json').write_text(json.dumps(out,indent=2)+'\n')
index=[]
for i in (243,38,18):
 cells=[]
 for v in variants:
  row=[]
  for engine in ('splash-aa','splash-noaa','cairo','pdfium','mupdf'):
   im=Image.open(L/f'{v}-{i:03}-{engine}-300.png').convert('RGB');im=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);row.append((v,engine,im))
  cells.append(row)
 cw=max(x[2].width for row in cells for x in row)+12;ch=max(x[2].height for row in cells for x in row)+26;sheet=Image.new('RGB',(cw*5,ch*4),'white');draw=ImageDraw.Draw(sheet)
 for y,row in enumerate(cells):
  for x,(v,e,im) in enumerate(row):draw.text((x*cw+3,y*ch+4),v+' '+e,fill='black');sheet.paste(im,(x*cw+3,y*ch+22))
 p=L/f'phase-a-grid-{i:03}.png';sheet.save(p);index.append({'proposal':i,'path':str(p),'sha256':sha(p.read_bytes())})
(E/'phase-a-panel-index.json').write_text(json.dumps(index,indent=2)+'\n');print('metrics',len(out))
