#!/usr/bin/env python3
"""Generate five-way enlarged JPEG-control and ownership-containment review panels."""
import hashlib,json,os,pathlib,sys
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41h';L=R/'local/hvc41h';P=L/'panels';P.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if os.getenv('SCANWEAVE_HVC41H_PANELS')!='1':sys.exit('research switch required')
if sha(R/'hvc41e/review-decisions.json')!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(R/'local/ink33r/historical.pdf')!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(R/'local/hvc41g/historical-frozen.pdf')!='e408daab686fd47f05451627620a79dc8770e5c299654eba4f76bb5454ef7a4b':sys.exit('frozen hash mismatch')
ghost=json.loads((E/'ghost-ink.json').read_text());rows=ghost['glyphs'];byid={x['proposal']:x for x in rows};source=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=source.size;imgs=[source]+[Image.open(L/(s+'.jpg')).convert('RGB').resize((w,h),Image.Resampling.NEAREST) for s in ('original-39','control','b-pre','b-native')];rank=sorted(rows,key=lambda r:(-max(r['residual_ghost_proxy_pixels']['b-pre'],r['residual_ghost_proxy_pixels']['b-native']),r['proposal']))[:6];indices=[]
def emit(box,path,title,proposals):
 tiles=[x.crop(box).resize(((box[2]-box[0])*4,(box[3]-box[1])*4),Image.Resampling.NEAREST) for x in imgs];cw=max(t.width for t in tiles)+12;ch=max(t.height for t in tiles)+48;sheet=Image.new('RGB',(cw*5,ch),'white');d=ImageDraw.Draw(sheet)
 for j,(name,t) in enumerate(zip(['source','original #39 background','control (same encoder)','B-pre','B-native'],tiles)):d.text((j*cw+3,3),name,fill='black');d.text((j*cw+3,20),title,fill='black');sheet.paste(t,(j*cw+3,43))
 sheet.save(path);indices.append({'path':str(path),'sha256':sha(path),'proposals':proposals,'source_box':box})
for n,r in enumerate(rank,1):
 a,b,c,d=map(int,r['source_box']);box=(max(0,a-14),max(0,b-12),min(w,c+14),min(h,d+12));counts=r['residual_ghost_proxy_pixels'];emit(box,P/f'ghost-{n:02}-{r["proposal"]:03}.png',f"proposal {r['proposal']} | dark proxy C {counts['control']} P {counts['b-pre']} N {counts['b-native']}",[r['proposal']])
a=min(int(byid[i]['source_box'][0]) for i in (207,208));b=min(int(byid[i]['source_box'][1]) for i in (207,208));c=max(int(byid[i]['source_box'][2]) for i in (207,208));d=max(int(byid[i]['source_box'][3]) for i in (207,208));emit((max(0,a-36),max(0,b-14),min(w,c+48),min(h,d+14)),P/'als-207-208.png','alfs context | proposals 207 / 208',[207,208])
images=[Image.open(L/f'containment-{name}.png').convert('RGB') for name in ('b-pre','b-native')];sheet=Image.new('RGB',(images[0].width*2+24,images[0].height+70),'white');draw=ImageDraw.Draw(sheet)
for j,(name,im) in enumerate(zip(['B-pre','B-native'],images)):x=j*(im.width+12);draw.text((x+3,4),name+' | cyan owned-mapped / yellow within MCU / red beyond MCU',fill='black');sheet.paste(im,(x+3,42))
p=P/'containment-map.png';sheet.save(p);indices.append({'path':str(p),'sha256':sha(p),'proposals':[],'classification':'changed decoded pixels; any-overlap native footprint cyan, outside footprint inside touched 16x16 MCU yellow, outside touched MCU red'})
(E/'panel-index.json').write_text(json.dumps(indices,indent=2)+'\n');print('panels',len(indices),'ghost ranking',[r['proposal'] for r in rank],flush=True)
