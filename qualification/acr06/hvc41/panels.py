#!/usr/bin/env python3
"""Source, baseline, Adobe and experimental-mask panels; no unsafe vectors."""
import hashlib,json,math,pathlib,sys
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');O=R/'local/hvc41';E=R/'hvc41';dest=O/'panels';dest.mkdir(exist_ok=True);items=[]
for doc,page in [('historical',x) for x in range(1,6)]+[('receipts',x) for x in (4,6,7,8,9)]:
 p=R/'local/ink33r';data=json.loads((p/'maps'/doc/f'{page:02d}.json').read_text());ref=Image.open(O/'masks'/f'corpus-{doc}-{page:02d}-reference-ink.png').convert('L');proposed=Image.open(O/'masks'/f'corpus-{doc}-{page:02d}-proposed.png').convert('L');a=np.asarray(proposed if doc=='historical' and page in (1,2) else ref);choices=[]
 for line in data['lines']:
  b=line.get('box');
  if not b:continue
  x0,y0,x1,y1=map(int,b);x0=max(0,x0);y0=max(0,y0);x1=min(a.shape[1],x1);y1=min(a.shape[0],y1)
  if x1>x0 and y1>y0:choices.append((int(a[y0:y1,x0:x1].sum()),[x0,y0,x1,y1],line.get('id')))
 if choices:_,box,lid=max(choices,key=lambda x:x[0]);reason='line with largest proxy/proposed mask sum'
 else:
  w,h=ref.size;box=[w//4,h//3,3*w//4,h//3+min(100,h//5)];lid=None;reason='no OCR line; context only'
 x0,y0,x1,y1=box;pad=8;box=[max(0,x0-pad),max(0,y0-pad),min(ref.width,x1+pad),min(ref.height,y1+pad)]
 images=[Image.open(p/'renders'/doc/f'{page:02d}-{name}.png').convert('RGB') for name in ('source','scanweave','adobe')]+[ref.convert('RGB')]+[Image.open(O/'masks'/f'corpus-{doc}-{page:02d}-{name}.png').convert('RGB') for name in ('corner','interior_mode','tile_median_128')]
 names=['source','baseline','Adobe XI registered','reference ink proxy','corner FG','interior FG','tiled FG']; crops=[im.crop(tuple(box)) for im in images];cw=max(160,round(crops[0].width*1.28)+8);hs=max(1,round(crops[0].height*.32));hb=max(1,round(crops[0].height*1.28));sheet=Image.new('RGB',(cw*len(names),hs+hb+62),'white');draw=ImageDraw.Draw(sheet)
 for n,(name,im) in enumerate(zip(names,crops)):
  x=n*cw;draw.text((x+2,2),name,fill='black');draw.text((x+2,18),'reading',fill='black');sheet.paste(im.resize((max(1,round(im.width*.32)),hs),Image.Resampling.NEAREST if n>=3 else Image.Resampling.LANCZOS),(x,32));draw.text((x+2,35+hs),'4x reading',fill='black');sheet.paste(im.resize((max(1,round(im.width*1.28)),hb),Image.Resampling.NEAREST if n>=3 else Image.Resampling.LANCZOS),(x,52+hs))
 f=dest/f'{doc}-{page:02d}-line.png';sheet.save(f);items.append({'kind':'line','document':doc,'page':page,'line_id':lid,'box':box,'selection':reason,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 # Whole-page geometry/context: source, baseline, Adobe and segmentation masks.
 scale=min(480/ref.width,650/ref.height);scaled=[im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.NEAREST if i>=3 else Image.Resampling.LANCZOS) for i,im in enumerate(images)];cw=max(x.width for x in scaled);hh=max(x.height for x in scaled);whole=Image.new('RGB',(cw*len(names),hh+20),'white');draw=ImageDraw.Draw(whole)
 for n,(name,im) in enumerate(zip(names,scaled)):draw.text((n*cw,0),name,fill='black');whole.paste(im,(n*cw,20))
 f=dest/f'{doc}-{page:02d}-page.png';whole.save(f);items.append({'kind':'page','document':doc,'page':page,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 print(doc,page,flush=True)
(E/'panel-index.json').write_text(json.dumps(items,indent=2)+'\n');print('COMPLETE',flush=True)
