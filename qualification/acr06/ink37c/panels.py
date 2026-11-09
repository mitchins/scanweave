from pathlib import Path
from PIL import Image,ImageDraw
import json,math,hashlib
R=Path('/data/coding/scanweave/qualification/acr06'); local=R/'local/ink37c'; out=local/'panels';out.mkdir(exist_ok=True)
old=json.load(open(R/'ink37/polarity37/owner-glyph-panel-index.json'));images={};items=[]
for doc,n in [('historical',2),('historical',5),('receipts',4)]:
 images[(doc,n)]=[Image.open(R/'local/ink33/renders'/doc/f'{n:02d}-source.png').convert('RGB'),Image.open(R/'local/ink37/owner37/renders/pdfium'/doc/f'main-{n:02d}.png').convert('RGB'),Image.open(R/'local/ink37/owner37/renders/pdfium'/doc/f'candidate-{n:02d}.png').convert('RGB'),Image.open(local/'renders/pdfium'/f'{doc}-{n:02d}-300.png').convert('RGB')]
 assert len({im.size for im in images[(doc,n)]})==1
for g in old:items.append({'document':g['document'],'page':g['page'],'box':g['object_box'],'kind':'glyph'})
for label,doc,n,box in [('Chicken','receipts',4,[187,819,322,847]),('Nos','historical',2,[540,1195,630,1236]),('quod','historical',2,[305,1517,417,1569]),('ingenui','historical',5,[481,1178,621,1229]),('ad','historical',5,[1042,375,1081,440])]:items.append({'document':doc,'page':n,'box':box,'kind':'word','label':label})
for start in range(0,len(items),5):
 batch=items[start:start+5]; prepared=[]
 for obj in batch:
  ims=images[(obj['document'],obj['page'])];x0,y0,x1,y1=obj['box'];box=(max(0,math.floor(x0)-12),max(0,math.floor(y0)-12),min(ims[0].width,math.ceil(x1)+12),min(ims[0].height,math.ceil(y1)+12));prepared.append([im.crop(box) for im in ims]);obj['crop_box']=box
 cw=max(120,max(im.width*4+10 for crops in prepared for im in crops));rh=max(110,max(im.height*4+25 for crops in prepared for im in crops)); sheet=Image.new('RGB',(cw*12,rh*len(batch)),'white');draw=ImageDraw.Draw(sheet)
 for j,(obj,crops) in enumerate(zip(batch,prepared)):
  y=j*rh
  for k,(name,im) in enumerate(zip(('source','main','lossless','compact'),crops)):
   for col,scale in ((k,0.32),(k+4,1),(k+8,4)):
    draw.text((col*cw,y),f'{start+j+1:02} {name} {scale:g}x',fill='black'); size=(max(1,round(im.width*scale)),max(1,round(im.height*scale)));sheet.paste(im.resize(size,Image.Resampling.NEAREST),(col*cw,y+20))
  obj['sheet']=f'sheet-{start//5+1:02d}.png';obj['sheet_row']=j+1
 path=out/f'sheet-{start//5+1:02d}.png';sheet.save(path);sha=hashlib.sha256(path.read_bytes()).hexdigest()
 for obj in batch:obj['sheet_sha256']=sha
for (doc,n),ims in images.items():
 thumb=[im.resize((round(im.width*.32),round(im.height*.32)),Image.Resampling.LANCZOS) for im in ims];w=max(i.width for i in thumb);h=max(i.height for i in thumb);sheet=Image.new('RGB',(w*4,h+25),'white');draw=ImageDraw.Draw(sheet)
 for k,(lab,im) in enumerate(zip(('source','main','lossless','compact'),thumb)):draw.text((k*w,0),lab,fill='black');sheet.paste(im,(k*w,20))
 p=out/f'{doc}-{n:02d}-page.png';sheet.save(p);items.append({'kind':'page','document':doc,'page':n,'sheet':p.name,'sheet_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(R/'ink37c/panel-index.json').write_text(json.dumps(items,indent=2)+'\n')
