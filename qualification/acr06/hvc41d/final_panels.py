import json,pathlib,hashlib,numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';r=json.loads((E/'p1-preflight-ledger.json').read_text())[243];a,b,c,d=r['reference_box'];imgs=[Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'),Image.open(L/'renders/pdfium-300-01-baseline.png').convert('RGB'),Image.open(L/'renders/pdfium-300-01-candidate.png').convert('RGB')];index=[]
for name,box,scale in [('glyph-4x',(a-4,b-4,c+4,d+4),4),('context-4x',(a-100,b-25,c+100,d+25),4),('context-reading',(a-220,b-60,c+220,d+60),1)]:
 crops=[im.crop(box) for im in imgs];cw=max(180,max(i.width for i in crops)*scale+24);ch=max(i.height for i in crops)*scale+30;canvas=Image.new('RGB',(cw*3,ch),'white');draw=ImageDraw.Draw(canvas)
 for k,(im,label) in enumerate(zip(crops,['source','baseline #39','candidate'])):
  draw.text((k*cw+5,4),label,fill='black');canvas.paste(im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST),(k*cw+5,25))
 f=L/f'final-243-{name}.png';canvas.save(f);index.append({'proposal':243,'kind':name,'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(E/'final-panel-index.json').write_text(json.dumps(index,indent=2)+'\n')
