#!/usr/bin/env python3
"""Source and experimental segmentation panels for frozen synthetic controls."""
import hashlib,io,json,pathlib,sys
import numpy as np,pikepdf
from PIL import Image,ImageDraw
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r');from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');O=R/'local/hvc41';E=R/'hvc41';dest=O/'panels';dest.mkdir(exist_ok=True);entries=[];W=np.array([.2126,.7152,.0722],np.float32)
cases=[('control','controls','control-measured',x) for x in ('black_border','yellow','reverse_panel','reverse_page','photograph')]+[('supplemental','controls-supplemental','control-supplemental-measured','small_receipt')]+[('positive','positive-controls','control-positive-measured',x) for x in ('reverse_page-160','reverse_panel-160','dark_table-108')]
def upper(a):return np.partition(a,len(a)//2,axis=0)[len(a)//2]
for kind,folder,reportfolder,name in cases:
 path=R/'local/ink37'/folder/f'{name}.pdf';p=pikepdf.open(path);obj=next(o for o in p.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');a=np.asarray(Image.open(io.BytesIO(obj.read_raw_bytes())).convert('RGB'));p.close();h,w=a.shape[:2];y=a.astype(np.float32)@W;cp=upper(np.array([upper(a[yy:yy+6,xx:xx+6].reshape(-1,3)) for xx,yy in ((0,0),(w-6,0),(0,h-6),(w-6,h-6))]));mid=y[h//10:9*h//10,w//10:9*w//10];cl=a[h//10:9*h//10,w//10:9*w//10];hist=np.bincount(np.minimum((mid/8).astype(int),31).ravel(),minlength=32);mode=int(hist.argmax());pos=np.flatnonzero(hist>=mid.size*.02);bright=int(pos[-1]) if len(pos) else mode
 get=lambda k:upper(cl[(mid>=k*8)&(mid<(k+1)*8)].reshape(-1,3));colors={'corner':cp,'interior mode':get(mode),'bright mode':get(bright)};masks={k:np.abs(y-float(v@W))>60 for k,v in colors.items()};tile=np.zeros((h,w),bool)
 for yy in range(0,h,128):
  for xx in range(0,w,128):
   z=y[yy:yy+128,xx:xx+128];tile[yy:yy+128,xx:xx+128]=np.abs(z-np.median(z))>60
 masks['tiled median']=tile;meta=json.loads((R/'local/ink37'/reportfolder/f'{name}.pdf.json').read_text())['pages'][0];lines=chars_from_hocr(meta['hocr']);line=max(lines,key=lambda z:sum(len(w['chars']) for w in z['words'])) if lines else None
 if line:
  x0,y0,x1,y1=map(int,line['box']);box=(max(0,x0-12),max(0,y0-12),min(w,x1+12),min(h,y1+12))
 else:box=(w//4,h//3,3*w//4,min(h,h//3+100))
 images=[Image.fromarray(a)]+[Image.fromarray((m*255).astype('uint8')).convert('RGB') for m in masks.values()];names=['source']+list(masks);crops=[im.crop(box) for im in images];cw=max(160,round(crops[0].width*1.28)+8);hs=max(1,round(crops[0].height*.32));hb=max(1,round(crops[0].height*1.28));sheet=Image.new('RGB',(cw*len(names),hs+hb+62),'white');draw=ImageDraw.Draw(sheet)
 for i,(label,im) in enumerate(zip(names,crops)):
  x=i*cw;draw.text((x,2),label,fill='black');draw.text((x,18),'reading',fill='black');sheet.paste(im.resize((max(1,round(im.width*.32)),hs),Image.Resampling.NEAREST if i else Image.Resampling.LANCZOS),(x,32));draw.text((x,35+hs),'4x reading',fill='black');sheet.paste(im.resize((max(1,round(im.width*1.28)),hb),Image.Resampling.NEAREST if i else Image.Resampling.LANCZOS),(x,52+hs))
 f=dest/f'control-{name}.png';sheet.save(f);entries.append({'set':kind,'case':name,'box':box,'line_id':line['id'] if line else None,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'note':'No Adobe output exists for synthetic controls.'});print(kind,name,flush=True)
(E/'control-panel-index.json').write_text(json.dumps(entries,indent=2)+'\n');print('COMPLETE',flush=True)
