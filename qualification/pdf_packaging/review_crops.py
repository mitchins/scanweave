"""Native and enlarged same-coordinate real-page crops, no rescaling of glyph geometry."""
import json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageOps,ImageDraw
B=Path(__file__).resolve().parent;D=B/'review-crops';D.mkdir(exist_ok=True)
rows=json.loads((B/'corpus.json').read_text());ids=[r['id'] for r in rows];cases=[('cord-02',(.35,.52,.85,.70)),('history-01',(.16,.15,.75,.30)),('scan-linn',(.07,.13,.48,.22)),('nara-form-02',(.10,.21,.70,.30))];records=[]
for id,box in cases:
 index=ids.index(id);thumbs=[]
 for arm in ['source','adobe','scanweave','ocrmypdf1','ocrmypdf3','archive']:
  path=B/'real'/('input' if arm=='source' else arm)/(id+'.pdf');pi=0
  if arm=='adobe':path=B/'real'/('adobe-all.pdf' if index<30 else 'adobe-forms.pdf');pi=index if index<30 else index-30
  doc=pdfium.PdfDocument(str(path));page=doc[pi];w,h=page.get_size();x0,y0,x1,y1=box;crop=(w*x0,h*(1-y1),w*(1-x1),h*y0)
  for zoom in [1,8]:
   im=page.render(scale=300/72*zoom,crop=crop).to_pil().convert('RGB');name=f'{id}-{arm}-{zoom*100}pct.png';im.save(D/name);records.append({'id':id,'arm':arm,'zoom':zoom,'source_pdf':str(path),'page':pi,'crop_fraction':box,'pixels':list(im.size),'file':name})
   if zoom==1:
    small=ImageOps.contain(im,(450,180));canvas=Image.new('RGB',(460,205),'white');canvas.paste(small,(5,20));ImageDraw.Draw(canvas).text((5,3),arm,fill='black');thumbs.append(canvas)
 sheet=Image.new('RGB',(460*3,205*2),'#ddd')
 for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*460,(i//3)*205))
 sheet.save(D/(id+'-context.png'))
(D/'manifest.json').write_text(json.dumps(records,indent=2))
