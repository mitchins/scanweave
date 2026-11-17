"""Create honest 2x-PDFium comparison panels for the incomplete milestone."""
import json,pathlib,sys
from PIL import Image,ImageDraw
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B=c.B;O=c.O;(O/'final').mkdir(exist_ok=True)
results=json.loads(pathlib.Path('/tmp/scanweave-books01/qualification/books01/phase2/results.json').read_text())['pages']
for key,info in c.CASES.items():
 run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dpi=run['dpi'];target=info['target'];rows=results[run['id']]['rows'];images=[]
 for title,row in [('source','src'),('ScanWeave #39','sw-E')]:
  geometry=None if row=='src' else rows[row]['geometry'];images.append((title,c.pdf_crop(run['rows'][row]['path'],key,target,dpi,2,geometry)))
 images.append(('improved ScanWeave: unavailable',None))
 doc=c.pdfium.PdfDocument(str(O/'crops'/f'{key}-inverse_layers.pdf'));images.append(('crop-only prototype (not ScanWeave)',doc[0].render(scale=dpi*2/72).to_pil().convert('RGB')))
 for title,row in [('MRC','mrc-M'),('Adobe (registered)','adobe-E')]:
  if row=='adobe-E':
   paths=[B/'runs/adobe'/f'{key}.adobe.pdf',B/'runs/adobe-p2'/f'{key}.adobe.pdf'];path=next((p for p in paths if p.exists()),None)
  else:path=run['rows'][row]['path']
  geometry=rows.get(row,{}).get('geometry');images.append((title,c.pdf_crop(path,key,target,dpi,2,geometry) if path and geometry and geometry.get('status')=='accepted' else None))
 width=max(360,2*(target[2]-target[0]));h=2*(target[3]-target[1]);sheet=Image.new('RGB',(width,len(images)*(h+24)),'white');draw=ImageDraw.Draw(sheet)
 for i,(title,img) in enumerate(images):
  y=i*(h+24);draw.text((2,y+3),title,fill='black')
  if img:sheet.paste(img,(0,y+24))
 sheet.save(O/'final'/('613.png' if key=='8967062' else 'french.png'))
