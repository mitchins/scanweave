from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib,math
r=Path('/data/coding/scanweave/qualification/acr06');local=r/'local/ink37';out=local/'panels-final';out.mkdir(exist_ok=True)
items=[('Chicken','receipts',4,(187,819,322,847)),('Nos','historical',2,(540,1195,630,1236)),('quod','historical',2,(305,1517,417,1569))]
g=json.loads((r/'ink37/polarity37/owner-glyph-panel-index.json').read_text());p5=[x for x in g if x['document']=='historical' and x['page']==5]
for i in (0,10,20,30):
 x=p5[i];items.append((f'historical-p5-example-{i+1}','historical',5,x['box']))
rows=[]
for label,doc,n,box in items:
 source=Image.open(r/'local/ink33/renders'/doc/f'{n:02d}-source.png').convert('RGB');main=Image.open(local/'owner37/renders/pdfium'/doc/f'main-{n:02d}.png').convert('RGB');cand=Image.open(local/'owner37/renders/pdfium'/doc/f'candidate-{n:02d}.png').convert('RGB');x0,y0,x1,y1=box;box=(max(0,math.floor(x0)-15),max(0,math.floor(y0)-15),min(source.width,math.ceil(x1)+15),min(source.height,math.ceil(y1)+15));crops=[im.crop(box) for im in (source,main,cand)];w=max(im.width*4+12 for im in crops);h=max(im.height*4+30 for im in crops);sheet=Image.new('RGB',(w*6,h),'white');draw=ImageDraw.Draw(sheet)
 for j,(name,im) in enumerate(zip(('source','main','candidate'),crops)):
  draw.text((j*w,0),name,fill='black');sheet.paste(im,(j*w,20));draw.text(((j+3)*w,0),name+' 4x',fill='black');sheet.paste(im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST),((j+3)*w,20))
 p=out/f'{label}.png';sheet.save(p);rows.append({'label':label,'document':doc,'page':n,'box':box,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(r/'ink37/polarity37/owner-named-panel-index.json').write_text(json.dumps(rows,indent=2)+'\n')
