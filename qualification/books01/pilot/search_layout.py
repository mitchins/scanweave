#!/usr/bin/env python3
"""PDFium literal search and approximate line grouping against GT polygons."""
import hashlib,json,math,pathlib,random,re,unicodedata
from PIL import Image,ImageDraw
import pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';corpus=json.loads((P/'corpus.frozen.json').read_text());ids=corpus['pilot_6'];works={p['id']:p['work'] for p in corpus['pages']};locks=json.loads((P/'sources.lock.json').read_text())['pages'];runs=json.loads((Q/'results/runs.json').read_text())
def normal(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',re.sub(r'-\s*\n\s*','',s.replace('ſ','s'))).casefold()).strip()
gts={}; words={}
for id in ids:
 key=id.split('/')[-1];g=json.loads((B/'gt'/works[id]/(key+'.json')).read_text());gts[id]=g; text=' '.join(x['text'] for x in (g['lines'] or g['regions']) if x.get('text'));words[id]=sorted(set(re.findall(r'\w{4,}',normal(text))))
def polygon_iou(poly,rect):
 if len(poly)<3:return 0
 xs=[p[0] for p in poly]+[rect[0],rect[2]];ys=[p[1] for p in poly]+[rect[1],rect[3]];x0=math.floor(min(xs));y0=math.floor(min(ys));x1=math.ceil(max(xs));y1=math.ceil(max(ys));w=x1-x0+1;h=y1-y0+1
 if w<=0 or h<=0 or w*h>30000000:return 0
 a=Image.new('1',(w,h));b=Image.new('1',(w,h));ImageDraw.Draw(a).polygon([(x-x0,y-y0) for x,y in poly],fill=1);ImageDraw.Draw(b).rectangle([rect[0]-x0,rect[1]-y0,rect[2]-x0,rect[3]-y0],fill=1)
 import numpy as np
 aa=np.asarray(a,dtype=bool);bb=np.asarray(b,dtype=bool); union=(aa|bb).sum();return float((aa&bb).sum()/union) if union else 0
def lines_of(page,dpi):
 tp=page.get_textpage(); height=page.get_height();boxes=[]
 for i in range(tp.count_chars()):
  try:
   t=tp.get_text_range(i,1);l,b,r,top=tp.get_charbox(i)
   if not t or t.isspace() or r<=l or top<=b:continue
   boxes.append([l*dpi/72,(height-top)*dpi/72,r*dpi/72,(height-b)*dpi/72])
  except Exception:continue
 groups=[]
 for rect in sorted(boxes,key=lambda q:(q[1]+q[3])/2):
  cy=(rect[1]+rect[3])/2;h=rect[3]-rect[1];match=next((g for g in groups if abs(cy-(g[1]+g[3])/2)<max(h,g[3]-g[1])*0.45),None)
  if match:match[:]=[min(match[0],rect[0]),min(match[1],rect[1]),max(match[2],rect[2]),max(match[3],rect[3])]
  else:groups.append(rect[:])
 return groups
def layout(page,id):
 g=gts[id]; lines=g['lines'] or [dict(polygon=r['polygon'],region_type=r['type']) for r in g['regions'] if r['kind']=='TextRegion' and r.get('text') and len(r['text'].strip().splitlines())==1];pred=lines_of(page,locks[id]['resolved_dpi']);pairs=[]
 for i,line in enumerate(lines):
  poly=line['polygon'];
  if len(poly)<3:continue
  x0=min(x[0] for x in poly);x1=max(x[0] for x in poly);y0=min(x[1] for x in poly);y1=max(x[1] for x in poly)
  for j,r in enumerate(pred):
   if min(x1,r[2])<=max(x0,r[0]) or min(y1,r[3])<=max(y0,r[1]):continue
   v=polygon_iou(poly,r)
   if v>=.5:pairs.append((v,i,j,math.hypot((x0+x1-r[0]-r[2])/2,(y0+y1-r[1]-r[3])/2)))
 used_i=set();used_j=set();matches=[]
 for v,i,j,dist in sorted(pairs,reverse=True):
  if i not in used_i and j not in used_j:used_i.add(i);used_j.add(j);matches.append((i,dist))
 n=len(lines);m=len(pred);dist=sorted(x[1] for x in matches);special={}
 for kind in ('marginalia','footnote'):
  indices={i for i,l in enumerate(lines) if kind in (l.get('region_type') or '')};special[kind]={'gt_lines':len(indices),'matched':len(indices&used_i)}
 return {'gt_type':'TextLine' if g['lines'] else 'single-line TextRegion proxy','gt_count':n,'predicted_count':m,'matched_count':len(matches),'f1':2*len(matches)/(n+m) if n+m else None,'median_centroid_offset_px':dist[len(dist)//2] if dist else None,'iou_threshold':.5,'line_grouping':'PDFium character boxes grouped by vertical centre; can merge columns','special_regions':special}
result={}
for id in ids:
 key=id.split('/')[-1];rng=random.Random(int.from_bytes(hashlib.sha256(('books01-search-v1/'+id).encode()).digest()[:8],'big'));positive=rng.sample(words[id],min(20,len(words[id])));other=sorted(set().union(*(set(words[j]) for j in ids if j!=id))-set(words[id]));negative=rng.sample(other,min(20,len(other)));result[id]={}
 for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
  path=pathlib.Path(runs[id]['rows'][row].get('path',B/'pilot/runs'/key/(row+'.pdf')))
  if not path.exists():result[id][row]={'status':'missing'};continue
  doc=pdfium.PdfDocument(str(path));page=doc[0];tp=page.get_textpage()
  def query(w):
   s=tp.search(w,match_case=False);hit=s.get_next() is not None;s.close();return hit
  pos=[query(w) for w in positive];neg=[query(w) for w in negative];result[id][row]={'search':{'seed':'books01-search-v1/'+id,'positive_word_hashes':[hashlib.sha256(w.encode()).hexdigest() for w in positive],'positive_hits':sum(pos),'positive_count':len(pos),'false_hits':sum(neg),'control_count':len(neg),'control_word_hashes':[hashlib.sha256(w.encode()).hexdigest() for w in negative],'method':'PDFium literal case-insensitive search of reading-normalized GT terms'},'layout':layout(page,id),'dpi_confidence':locks[id]['dpi_evidence']['confidence']}
 print(id,flush=True)
(Q/'results/search-layout.json').write_text(json.dumps(result,indent=2)+'\n')
