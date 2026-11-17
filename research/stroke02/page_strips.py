"""Development-only source/baseline/candidate/MRC/Adobe PDF crop strips."""
import json,pathlib,sys
from PIL import Image,ImageDraw
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent));import crop_fit as c
B,O=c.B,c.O;res=json.loads(pathlib.Path('/tmp/scanweave-books01/qualification/books01/phase2/results.json').read_text())['pages'];cases={'8967062':(1165,748,1236,791),'12342014':(84,360,611,442),'8967228':(1942,148,2309,205),'aventinus_grammatica_1515_0008':(400,1200,900,1270),'luther_babstum_1526_0011':(400,1700,900,1770),'euler_rechenkunst01_1738_0025':(0,500,500,570)};dest=O/'final';dest.mkdir(exist_ok=True)
for key,box in cases.items():
 d=O/'pages-extensions'/key;candidate=d/'candidate.pdf'
 if not candidate.exists():print(key,'missing candidate');continue
 run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());row=res[run['id']]['rows'];dpi=run['dpi']
 for zoom in (1,2):
  entries=[]
  for label,name,path in [('source','src',run['rows']['src']['path']),('ScanWeave #39','sw-E',run['rows']['sw-E']['path']),('experimental ScanWeave','sw-E',candidate),('MRC','mrc-M',run['rows']['mrc-M']['path']),('Adobe','adobe-E',next((x for x in (B/'runs/adobe'/f'{key}.adobe.pdf',B/'runs/adobe-p2'/f'{key}.adobe.pdf') if x.exists()),None))]:
   geom=None if name=='src' else row.get(name,{}).get('geometry');img=None
   if path and pathlib.Path(path).exists() and (name=='src' or (geom and geom.get('status')=='accepted')):
    img=c.pdf_crop(path,key,box,dpi,zoom,geom)
   entries.append((label,img))
  w=max(360,(box[2]-box[0])*zoom);h=(box[3]-box[1])*zoom;sheet=Image.new('RGB',(w,len(entries)*(h+24)),'white');draw=ImageDraw.Draw(sheet)
  for i,(label,img) in enumerate(entries):
   y=i*(h+24);draw.text((2,y+3),label+(' (unavailable or registration failed)' if img is None else ''),fill='black')
   if img:sheet.paste(img,(0,y+24))
  tag={'8967062':'613','12342014':'french'}.get(key,key);sheet.save(dest/(tag+('' if zoom==2 else '-1x')+'.png'))
 print(key,'done',flush=True)
