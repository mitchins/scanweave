#!/usr/bin/env python3
"""Illustrative proposed unit masks: OCR text is unverified, not a safe-glyph review."""
import hashlib,json,pathlib
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');O=R/'local/hvc41';E=R/'hvc41';dest=O/'panels';dest.mkdir(exist_ok=True);index=[]
for page in (1,2):
 items=json.loads((E/f'proposed-historical-{page:02d}.json').read_text());dump=json.loads((O/'trial2'/'historical'/f'p{page:06}.json').read_text());byid={x['symbol']:x for x in dump['units']};good=sorted(items,key=lambda x:(-x['reference_precision'],x['fill_delta'] if x['fill_delta'] is not None else 999))[:10];bad=sorted(items,key=lambda x:(x['reference_precision'],-(x['fill_delta'] or 0)))[:10];chosen=[];seen=set()
 for label,seq in (('high proxy agreement',good),('low proxy agreement',bad)):
  for x in seq:
   if x['symbol'] not in seen:seen.add(x['symbol']);chosen.append((label,x))
 source=[Image.open(R/'local/ink33r/renders/historical'/f'{page:02d}-{name}.png').convert('RGB') for name in ('source','scanweave','adobe')];ref=Image.open(O/'masks'/f'corpus-historical-{page:02d}-reference-ink.png').convert('RGB')
 for start in range(0,len(chosen),5):
  batch=chosen[start:start+5];prepared=[]
  for why,x in batch:
   u=byid[x['symbol']];b=x['bbox'];x0=max(0,int(b[0])-5);y0=max(0,int(b[1])-5);x1=min(source[0].width,int(b[2])+5);y1=min(source[0].height,int(b[3])+5);box=(x0,y0,x1,y1);crop=[v.crop(box) for v in source]+[ref.crop(box)];mask=np.zeros((y1-y0,x1-x0),np.uint8);ind=np.array(u['mask_indices']);xx=int(b[0])+ind%u['crop_w']-x0;yy=int(b[1])+ind//u['crop_w']-y0;valid=(xx>=0)&(yy>=0)&(xx<mask.shape[1])&(yy<mask.shape[0]);mask[yy[valid],xx[valid]]=255;crop.append(Image.fromarray(mask).convert('RGB'));prepared.append((why,x,box,crop))
  cw=max(100,max(im.width*4+4 for _,_,_,cs in prepared for im in cs));rh=max(100,max(im.height*4+42 for _,_,_,cs in prepared for im in cs));sheet=Image.new('RGB',(cw*5,rh*len(batch)),'white');draw=ImageDraw.Draw(sheet)
  for row,(why,x,box,crops) in enumerate(prepared):
   yy=row*rh
   for col,(label,im) in enumerate(zip(('source','baseline','Adobe','reference','unit mask'),crops)):
    draw.text((col*cw,yy),f'{start+row+1} {label}',fill='black');draw.text((col*cw,yy+14),why,fill='black');sheet.paste(im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST),(col*cw,yy+34))
   index.append({'document':'historical','page':page,'symbol':x['symbol'],'ocr_label_unverified':x['text_ocr_unverified'],'selection':why,'bbox':box,'reference_precision':x['reference_precision'],'fill_delta':x['fill_delta'],'sheet':f'units-{page:02d}-{start//5+1:02d}.png','row':row+1,'verified_glyph':False})
  f=dest/f'units-{page:02d}-{start//5+1:02d}.png';sheet.save(f);digest=hashlib.sha256(f.read_bytes()).hexdigest()
  for x in index[-len(batch):]:x['sha256']=digest
(E/'unit-panel-index.json').write_text(json.dumps(index,indent=2)+'\n');print('unit panels',len(index),flush=True)
