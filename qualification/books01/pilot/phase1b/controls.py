#!/usr/bin/env python3
"""Select fresh fixed-seed controls, stratified by pilot page and output row."""
import hashlib,json,pathlib,random,re
from html.parser import HTMLParser
from PIL import Image,ImageDraw
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';corpus=json.loads((P/'corpus.frozen.json').read_text());ids=corpus['pilot_6'];locks=json.loads((P/'sources.lock.json').read_text())['pages'];runs=json.loads((Q/'results/runs.json').read_text());geo=json.loads((Q/'results/phase1b/geometry.json').read_text())['pages'];refs=json.loads((Q/'results/phase1b/reference.json').read_text())['crops'];rows=['sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E'];D=B/'pilot/phase1b/controls';D.mkdir(parents=True,exist_ok=True)
class Boxes(HTMLParser):
 def __init__(self):super().__init__();self.boxes=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs);m=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',a.get('title',''))
  if 'ocrx_word' in a.get('class','').split() and m:self.boxes.append(tuple(map(int,m.groups())))
def overlap(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))>0
controls=[]
for id in ids:
 key=id.split('/')[-1]; dpi=str(int(locks[id]['resolved_dpi']));h=Boxes();h.feed((B/'ocr-frozen'/key/('psm'+str(runs[id]['selected_psm'])+'-1.hocr')).read_text());old=[r['bbox'] for r in refs if r['page']==id];candidates=[b for b in h.boxes if b[2]>b[0] and b[3]>b[1] and not any(overlap(b,x) for x in old)];crops=[]
 for row in rows:
  valid=[r for r in [geo[id][row]['pdfium'][dpi],geo[id]['src']['pdfium'][dpi]] if r['status']=='accepted']
  if len(valid)<2 or not candidates:continue
  seed=int.from_bytes(hashlib.sha256(('books01-1b-control-v1/'+id+'/'+row).encode()).digest()[:8],'big');rng=random.Random(seed);box=rng.choice(candidates);source=Image.open(B/valid[1]['aligned_render_path']).convert('RGB');target=Image.open(B/valid[0]['aligned_render_path']).convert('RGB');w,h=source.size;box=(max(0,box[0]-3),max(0,box[1]-3),min(w,box[2]+3),min(h,box[3]+3));src=source.crop(box);out=target.crop(box);crops.append((row,box,src,out));controls.append({'page':id,'row':row,'bbox':box,'seed_label':'books01-1b-control-v1/'+id+'/'+row,'assessment':'AI-assessment pending; not human-adjudicated'});source.close();target.close()
 if crops:
  maxw=max(x[2].width for x in crops)*8;total=sum(x[2].height*4+24 for x in crops);sheet=Image.new('RGB',(maxw,max(total,1)),'white');d=ImageDraw.Draw(sheet);y=0
  for row,box,a,b in crops:
   w=a.width*4;h=a.height*4;d.text((0,y),row+'  source | output',fill='black');sheet.paste(a.resize((w,h),Image.Resampling.NEAREST),(0,y+24));sheet.paste(b.resize((w,h),Image.Resampling.NEAREST),(w,y+24));y+=h+24
  sheet.save(D/(key+'.png'))
for i,item in enumerate(controls,1):item['control_id']=f'fresh-{i:03d}'
(D/'controls.json').write_text(json.dumps(controls,indent=2)+'\n')
print('fresh stratified control crops:',len(controls),flush=True)
