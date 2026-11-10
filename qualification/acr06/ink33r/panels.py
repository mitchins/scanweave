#!/usr/bin/env python3
"""40 largest measured gaps + 10 seeded random, with page/document extras."""
import hashlib,json,pathlib,random,statistics
from PIL import Image,ImageDraw,ImageFont
R=pathlib.Path('/data/coding/scanweave'); E=R/'qualification/acr06/ink33r'; O=R/'qualification/acr06/local/ink33r'; G=['historical','financial','mixed','receipts','forms']; K=['source','scanweave','adobe']; LABEL={'source':'Source','scanweave':'ScanWeave','adobe':'Adobe XI','a':'Line color','b':'Word color','c':'Adobe transfer'}
lines=[]
for g in G:
 for file in sorted(E.glob(f'metrics-{g}-*.json')):
  for l in json.loads(file.read_text())['lines']:
   gap=l['metrics']['scanweave']['gap']
   if gap is not None: lines.append({'document':g,'page':l['page'],'id':l['id'],'box':l['box'],'gap':gap})
ranked=sorted(lines,key=lambda l:abs(l['gap']),reverse=True); selected=[]; seen=set()
def add(l,reason):
 k=(l['document'],l['page'],l['id'])
 if k not in seen: seen.add(k); selected.append(dict(l,reason=reason))
for l in ranked[:40]: add(l,'largest absolute gaps')
rng=random.Random(33033); pool=[l for l in ranked if (l['document'],l['page'],l['id']) not in seen]
for l in rng.sample(pool,min(10,len(pool))): add(l,'seeded random from remaining mixed lines')
for g in G:
 choices=[x for x in ranked if x['document']==g]
 for x in choices[:3]: add(x,'document worst lines')
 if choices:
  mid=statistics.median(x['gap'] for x in choices)
  add(min(choices,key=lambda x:abs(x['gap']-mid)),'document median-gap mixed line')
for page in range(1,6):
 choices=[x for x in ranked if x['document']=='historical' and x['page']==page]
 if choices: add(choices[0],'historical page coverage')
 else:
  dat=json.loads((O/'maps'/'historical'/f'{page:02d}.json').read_text()); candidates=[l for l in dat['lines'] if l['box'][2]>l['box'][0] and l['box'][3]>l['box'][1]]
  if candidates:
   l=max(candidates,key=lambda l:(l['box'][2]-l['box'][0])*(l['box'][3]-l['box'][1])); add({'document':'historical','page':page,'id':l['id'],'box':l['box'],'gap':None},'historical page coverage; no mixed line')
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; font=ImageFont.truetype(fontpath,16); bold=ImageFont.truetype(fontpath,18)
outdir=O/'panels'; outdir.mkdir(parents=True,exist_ok=True); sheets=[]; index=[]
for start in range(0,len(selected),4):
 block=selected[start:start+4]; prepared=[]; maxwidth=0
 for n,l in enumerate(block,start+1):
  g=l['document']; page=l['page']; x0,y0,x1,y1=l['box']; crops=[]
  for name in K:
   img=Image.open(O/'renders'/g/f'{page:02d}-{name}.png').convert('RGB'); pad=4; crops.append(img.crop((max(0,x0-pad),max(0,y0-pad),min(img.width,x1+pad),min(img.height,y1+pad))))
  w,h=crops[0].size; small=max(1,round(w*.32)); big=max(1,round(w*1.28)); hs=max(1,round(h*.32)); hb=max(1,round(h*1.28)); col=big+12; width=130+3*col; height=75+hs+hb+15; maxwidth=max(maxwidth,width); prepared.append((n,l,crops,small,big,hs,hb,col,height))
 sheet=Image.new('RGB',(maxwidth,sum(x[-1] for x in prepared)+15),'white'); draw=ImageDraw.Draw(sheet); y=8
 for n,l,crops,small,big,hs,hb,col,height in prepared:
  gap='n/a' if l['gap'] is None else f"{l['gap']:+.1f}"
  draw.text((8,y),f"{n:02d}  {l['document']} p{l['page']} {l['id']} | vector - raster {gap} | {l['reason']}",font=bold,fill='black')
  for i,name in enumerate(K): draw.text((130+i*col,y+24),LABEL[name],font=font,fill='black')
  yy=y+47; draw.text((8,yy),'Reading size',font=font,fill='black')
  for i,crop in enumerate(crops):sheet.paste(crop.resize((small,hs),Image.Resampling.LANCZOS),(130+i*col,yy))
  yy+=hs+6; draw.text((8,yy),'4× reading size',font=font,fill='black')
  for i,crop in enumerate(crops):sheet.paste(crop.resize((big,hb),Image.Resampling.LANCZOS),(130+i*col,yy))
  index.append(dict(l,number=n,sheet=f'sheet-{start//4+1:02d}.png',y=y,height=height)); y+=height
 filename=f'sheet-{start//4+1:02d}.png'; path=outdir/filename; sheet.save(path,optimize=True); sha=hashlib.sha256(path.read_bytes()).hexdigest(); sheets.append({'file':str(path),'sha256':sha,'pixels':list(sheet.size),'lines':len(block)}); print(filename,sha,flush=True)
(E/'panel-index.json').write_text(json.dumps({'selection_seed':33033,'first_40':'largest absolute measured line gaps','next_10':'uniform sample without replacement from remaining eligible mixed lines','items':index,'sheets':sheets},indent=2)+'\n')
