import json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;P=B.parent/'pdf_packaging';D=B/'comparisons';D.mkdir(exist_ok=True);groups=json.loads((P/'groups.json').read_text());records=[]
cases={'cord-00':(.10,.25,.90,.60),'cord-05':(.15,.30,.85,.60),'history-02':(.12,.18,.70,.26),'history-03':(.15,.24,.75,.32),'scan-linn':(.10,.13,.75,.22),'nara-form-01':(.15,.20,.75,.29),'nara-form-02':(.15,.20,.75,.29)}
for id,box in cases.items():
 group=next((k,v['members'].index(id)) for k,v in groups.items() if id in v['members']);arms=[('Source',P/'real/input'/f'{id}.pdf',0),('Previous',P/'real/scanweave'/f'{id}.pdf',0),('Updated',B/'outputs'/f'{id}.pdf',0),('Adobe XI',P/'groups'/f'{group[0]}-adobe.pdf',group[1])]
 thumbs=[];crops=[]
 for name,path,pageindex in arms:
  page=pdfium.PdfDocument(str(path))[pageindex];im=page.render(scale=1).to_pil().convert('RGB');canvas=Image.new('RGB',(640,850),'white');im.thumbnail((630,820));canvas.paste(im,((640-im.width)//2,25));ImageDraw.Draw(canvas).text((5,3),name,fill='black');thumbs.append(canvas)
  w,h=page.get_size();x0,y0,x1,y1=box;crop=(w*x0,h*(1-y1),w*(1-x1),h*y0);im=page.render(scale=3,crop=crop).to_pil().convert('RGB');canvas=Image.new('RGB',(max(450,im.width),im.height+25),'white');canvas.paste(im,(0,25));ImageDraw.Draw(canvas).text((5,3),name,fill='black');crops.append(canvas);records.append({'id':id,'arm':name,'pdf':str(path),'page':pageindex,'crop_fraction':box,'scale':3,'note':'300% physical viewing scale; no glyph-bbox renormalization'})
 sheet=Image.new('RGB',(2560,850),'white')
 for i,im in enumerate(thumbs):sheet.paste(im,(i*640,0))
 sheet.save(D/f'{id}-native.png')
 sheet=Image.new('RGB',(max(x.width for x in crops),sum(x.height for x in crops)),'white');y=0
 for im in crops:sheet.paste(im,(0,y));y+=im.height
 sheet.save(D/f'{id}-300pct.png')
(D/'manifest.json').write_text(json.dumps(records,indent=2));print('comparisons written')
