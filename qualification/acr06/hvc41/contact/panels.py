#!/usr/bin/env python3
"""Source-aligned artwork overlays and bounded sample panels, no vectors emitted."""
import pathlib,json,hashlib,random,collections
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41';E=R/'hvc41/contact';P=L/'contact/panels';P.mkdir(parents=True,exist_ok=True);idx=[]
rows=json.loads((E/'decomposition.json').read_text());sel={(m,d,p) for m in ('interior','corner') for d,p in ([('historical',i) for i in range(1,6)]+[('receipts',i) for i in (4,6,7,8,9)])}
for row in rows:
 key=(row['mode'],row['document'],row['page'])
 if key not in sel:continue
 mode,doc,page=key;src=Image.open(R/'local/ink33r/renders'/doc/f'{page:02}-source.png').convert('RGBA');ov=Image.new('RGBA',src.size);draw=ImageDraw.Draw(ov);base=L/'contact'/mode/doc
 for j,art in enumerate(row['largest_artwork'][:3]):
  mask=Image.open(base/art['mask_file']).convert('L');x,y=map(int,art['bbox'][:2]);layer=Image.new('RGBA',mask.size,[(255,0,0,115),(0,190,255,115),(255,0,255,115)][j]);ov.paste(layer,(x,y),mask);draw.rectangle(tuple(map(int,art['bbox'])),outline=[(255,230,0,255),(0,255,255,255),(255,0,255,255)][j],width=5)
  draw.text((x+5,y+5),f"#{art['artwork_index']} pixels={art['pixels']}",fill=(255,255,0,255),stroke_width=2,stroke_fill=(0,0,0,255))
 src=Image.alpha_composite(src,ov).convert('RGB');src.thumbnail((1100,1500),Image.Resampling.LANCZOS);f=P/f'art-{mode}-{doc}-{page:02}.png';src.save(f);idx.append({'kind':'artwork_bbox_mask_overlay','mode':mode,'document':doc,'page':page,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'artwork_shown':row['largest_artwork'][:3]})
pro=[x for x in json.loads((E/'new-proposals.json').read_text()) if x['mode']=='interior' and x['document']=='historical'];random.Random(41037).shuffle(pro);worst=sorted(pro,key=lambda x:(x['reference_precision'], -(x['fill_luminance_delta'] or 1e6)));selected=[];seen=set()
for kind,seq in [('worst',worst[:20]),('seeded_random',pro)]:
 for item in seq:
  k=(item['document'],item['page'],item['symbol'])
  if k in seen:continue
  seen.add(k);selected.append((kind,item))
  if len(selected)>=40:break
 if len(selected)>=40:break
cache={}
for page in sorted({x['page'] for _,x in selected}):
 doc='historical';d=json.loads((L/'contact/interior'/doc/f'p{page:06}.json').read_text());cache[page]={u['symbol']:u for u in d['units']}
for i,(kind,item) in enumerate(selected):
 page=item['page'];u=cache[page][item['symbol']];src=Image.open(R/'local/ink33r/renders/historical'/f'{page:02}-source.png').convert('RGB'); masks=[Image.open(L/'masks'/f'corpus-historical-{page:02}-{name}.png').convert('RGB') for name in ('corner','interior_mode')];x0,y0,x1,y1=map(int,u['bbox']);pad=8;box=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad));bw,bh=u['crop_w'],u['crop_h'];unit=Image.new('L',src.size);a=np.zeros((bh,bw),dtype=np.uint8);a.ravel()[u['mask_indices']]=255;unit.paste(Image.fromarray(a),(x0,y0));images=[src,*masks,unit.convert('RGB')];crops=[]
 for im in images:
  crop=im.crop(box);crop.thumbnail((240,180),Image.Resampling.NEAREST);crop=crop.resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST);crops.append(crop)
 cw=max(x.width for x in crops);ch=max(x.height for x in crops);sheet=Image.new('RGB',(4*cw,max(ch+45,70)),'white');draw=ImageDraw.Draw(sheet)
 for j,(im,label) in enumerate(zip(crops,['source','corner mask','interior mask','proposed unit mask'])):sheet.paste(im,(j*cw,35));draw.text((j*cw+3,3),label,fill='black')
 draw.text((3,18),f"{kind} p{page} {item['symbol']} precision={item['reference_precision']:.3f} delta={item['fill_luminance_delta']}",fill='black');f=P/f'new-unit-{i+1:02}.png';sheet.save(f);idx.append({'kind':'newly_admitted_unit','selection':kind,**item,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(E/'panel-index.json').write_text(json.dumps(idx,indent=2)+'\n');print('art overlays',sum(x['kind']=='artwork_bbox_mask_overlay' for x in idx),'unit panels',len(selected))
