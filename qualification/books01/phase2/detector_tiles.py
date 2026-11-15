#!/usr/bin/env python3
"""Use existing pilot tile detectors and fixed thresholds on aligned renders."""
import collections,json,pathlib
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';D=B/'phase2';src=Q/'phase1b/calibrate.py';ns={'__file__':str(src)};exec(compile(src.read_text().split('records=[]')[0],str(src),'exec'),ns);cal=json.loads((Q/'results/phase1b/calibration.json').read_text())['detectors'];pages=[p for p in json.loads((P/'corpus.frozen.json').read_text())['pages'] if p['split']=='dev'];out={}
for p in pages:
 id=p['id'];key=id.split('/')[-1];g=json.loads((B/'gt'/p['work']/(key+'.json')).read_text());source=D/'renders'/key/'src'/'pdfium-native.png';out[id]={}
 if not source.exists():continue
 a=Image.open(source).convert('RGB');w,h=a.size;tiles=[]
 for r in g['regions']:
  if r['kind'] not in ('ImageRegion','GraphicRegion','ChartRegion') or not r['polygon']:continue
  x=[v[0] for v in r['polygon']];y=[v[1] for v in r['polygon']];cx=(min(x)+max(x))//2;cy=(min(y)+max(y))//2;tiles.append([max(0,cx-64),max(0,cy-64),min(w,cx+64),min(h,cy+64)])
 borders=[[0,0,min(128,w),min(128,h)],[max(0,w-128),0,w,min(128,h)],[0,max(0,h-128),min(w,128),h],[max(0,w-128),max(0,h-128),w,h]]
 for row in ['sw-E','mrc-M','ocrmypdf-E','adobe-E']:
  f=D/'renders'/key/row/'pdfium-aligned.png'
  if not f.exists():out[id][row]={'status':'unavailable'};continue
  im=Image.open(f).convert('RGB');counts={}
  for det,boxes in [('illustration_colour',tiles),('border_inversion',borders)]:
   values=[]
   for box in boxes:
    x=ns['calc'](a,im,box,id)
    if x and x[det] is not None:values.append(x[det])
   counts[det]={'examined':len(values),'suspected':sum(v>=cal[det]['threshold'] for v in values) if cal[det]['threshold'] is not None else None}
  out[id][row]={'status':'automated suspicions, unreviewed','detectors':counts};im.close()
 a.close()
(P/'phase2/detector-tiles.json').write_text(json.dumps(out,indent=2)+'\n');print('tile results',len(out),'pages')
