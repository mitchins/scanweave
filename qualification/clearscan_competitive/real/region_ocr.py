"""Character OCR from CORD text-region crops; full original images remain composition inputs.
Only annotation boxes are read, never annotation transcription. Historical pages
use full-page OCR. Existing Tesseract engine, hocr_char_boxes=1, English model.
"""
import json,re,subprocess,time
from pathlib import Path
from PIL import Image
from lxml import etree
B=Path(__file__).resolve().parent;records=[]
for p in sorted(list(B.glob('cord-*.png'))+list(B.glob('history-*.png'))):
 if '.ocr-crop' in p.name:continue
 im=Image.open(p);w,h=im.size;x0=y0=0;x1=w;y1=h
 if p.stem.startswith('cord'):
  annotation=json.loads(p.with_suffix('.truth.json').read_text());q=[word['quad'] for line in annotation['valid_line'] for word in line['words']];xs=[v for b in q for k,v in b.items() if k.startswith('x')];ys=[v for b in q for k,v in b.items() if k.startswith('y')]
  if xs:x0=max(0,min(xs)-12);y0=max(0,min(ys)-12);x1=min(w,max(xs)+12);y1=min(h,max(ys)+12)
 crop=B/(p.stem+'.ocr-crop.png');im.crop((x0,y0,x1,y1)).save(crop);stem=B/(p.stem+'.regions');cmd=['tesseract',str(crop),str(stem),'--dpi','300','-l','eng','--psm','6','-c','hocr_char_boxes=1','hocr'];start=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True,check=True)
 doc=etree.parse(str(stem)+'.hocr',etree.XMLParser(load_dtd=False,no_network=True));
 for elem in doc.iter():
  title=elem.get('title')
  if title:
   def shift(m):
    key=m.group(1);a,b,c,d=map(int,m.groups()[1:]);return f'{key} {a+x0} {b+y0} {c+x0} {d+y0}'
   elem.set('title',re.sub(r'\b(bbox|x_bboxes) (\d+) (\d+) (\d+) (\d+)',shift,title))
  if elem.get('class')=='ocr_page':elem.set('title',f'bbox 0 0 {w} {h}; scan_res 300 300')
 Path(str(stem)+'.hocr').write_bytes(etree.tostring(doc,encoding='UTF-8'))
 records.append({'page':p.name,'crop':[x0,y0,x1,y1],'seconds':time.monotonic()-start,'command':cmd});print(p.stem,round(records[-1]['seconds'],2),flush=True)
(B/'region-ocr-manifest.json').write_text(json.dumps(records,indent=2))
