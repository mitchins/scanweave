#!/usr/bin/env python3
"""Create suspected-only blind comparisons; never publish the local label key."""
import hashlib,json,pathlib,random,re,secrets,statistics
from html.parser import HTMLParser
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_erosion,distance_transform_edt
from skimage.color import rgb2lab,deltaE_ciede2000
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';corpus=json.loads((P/'corpus.frozen.json').read_text()); ids=corpus['pilot_6'];works={p['id']:p['work'] for p in corpus['pages']};locks=json.loads((P/'sources.lock.json').read_text())['pages']; runs=json.loads((Q/'results/runs.json').read_text()); rows=['sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']; rnd=secrets.SystemRandom(); D=B/'pilot/blind';D.mkdir(parents=True,exist_ok=True)
class Boxes(HTMLParser):
 def __init__(self):super().__init__();self.boxes=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs);m=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',a.get('title',''))
  if 'ocrx_word' in a.get('class','').split() and m:self.boxes.append(tuple(map(int,m.groups())))
def bound(box,w,h):
 x0,y0,x1,y1=box;return (max(0,min(w,x0)),max(0,min(h,y0)),max(0,min(w,x1)),max(0,min(h,y1)))
def score(a,b):
 gray=lambda x:(.299*x[:,:,0]+.587*x[:,:,1]+.114*x[:,:,2])<128
 x=gray(a);y=gray(b);tp=int((x&y).sum()); ea=x&~binary_erosion(x);eb=y&~binary_erosion(y); inter=int((ea&eb).sum());union=int((ea|eb).sum()); iou=inter/union if union else 1.; missing=1-tp/int(x.sum()) if x.any() else 0.;spurious=1-tp/int(y.sum()) if y.any() else 0.;chamfer=float((distance_transform_edt(~x)[y].mean()+distance_transform_edt(~y)[x].mean())/2) if x.any() and y.any() else None
 return {'contour_iou':iou,'shape_mismatch':1-iou,'chamfer_px':chamfer,'missing_ink_fraction':missing,'spurious_ink_fraction':spurious}
index=[];keymap={};raw={};thresholds={};counter=0; raw_scores=(B/'pilot/raw-scores.jsonl').open('w')
for id in ids:
 page=id.split('/')[-1];dpi=int(locks[id]['resolved_dpi']);files={r:B/'pilot/renders'/page/r/('pdfium-'+str(dpi)+'.png') for r in ['src']+rows};
 if not all(p.exists() for p in files.values()):continue
 images={r:Image.open(p).convert('RGB') for r,p in files.items()};w,h=images['src'].size
 if any(abs(im.width-w)>1 or abs(im.height-h)>1 for im in images.values()):continue
 w=min(im.width for im in images.values());h=min(im.height for im in images.values()); images={r:im.crop((0,0,w,h)) for r,im in images.items()}
 psm=runs[id]['selected_psm'];parser=Boxes();parser.feed((B/'ocr-frozen'/page/f'psm{psm}-1.hocr').read_text()); candidates={x:[] for x in ['glyph_shape','missing_ink','spurious_ink','illustration_colour','border_inversion']}
 for bbox in parser.boxes:
  box=bound(bbox,w,h);x0,y0,x1,y1=box
  if x1-x0<2 or y1-y0<2:continue
  a=np.asarray(images['src'].crop(box));
  for row in rows:
   b=np.asarray(images[row].crop(box));s=score(a,b)
   for det,field in [('glyph_shape','shape_mismatch'),('missing_ink','missing_ink_fraction'),('spurious_ink','spurious_ink_fraction')]:candidates[det].append((float(s[field]),box,row,s))
 # Illustration and page-edge detector samples use fixed 128px tiles.
 gt=json.loads((B/'gt'/works[id]/(page+'.json')).read_text()); tiles=[]
 for region in gt['regions']:
  if region['kind'] not in ('ImageRegion','GraphicRegion','ChartRegion') or not region['polygon']:continue
  xs=[p[0] for p in region['polygon']];ys=[p[1] for p in region['polygon']];cx=(min(xs)+max(xs))//2;cy=(min(ys)+max(ys))//2;tiles.append(bound((cx-64,cy-64,cx+64,cy+64),w,h))
 borders=[bound(x,w,h) for x in [(0,0,128,128),(w-128,0,w,128),(0,h-128,128,h),(w-128,h-128,w,h)]]
 for det,boxes in [('illustration_colour',tiles),('border_inversion',borders)]:
  for box in boxes:
   if box[2]<=box[0] or box[3]<=box[1]:continue
   a=np.asarray(images['src'].crop(box))
   for row in rows:
    b=np.asarray(images[row].crop(box));
    if det=='illustration_colour':val=float(deltaE_ciede2000(rgb2lab(a),rgb2lab(b)).mean());details={'mean_deltaE2000':val}
    else:
     x=a.mean(axis=2)<128;y=b.mean(axis=2)<128;val=float(np.logical_xor(x,y).mean());details={'dark_light_disagreement':val}
    candidates[det].append((val,box,row,details))
 all_candidates=[];thresholds[id]={}
 for det,entries in candidates.items():
  for value,box,row,details in entries:raw_scores.write(json.dumps({'page':id,'detector':det,'bbox':box,'row':row,'score':value,'components':details})+'\n')
 for det,entries in candidates.items():
  values=sorted(e[0] for e in entries);thresholds[id][det]={'count':len(entries),'p995':values[min(len(values)-1,int(.995*len(values)))] if values else None,'rule':'top two candidates, threshold is pilot 99.5th percentile for triage calibration'}
  ordered=sorted(entries,key=lambda x:x[0],reverse=True);all_candidates.extend([(det,e) for e in ordered[:2]])
 # Nonflagged word-box controls, selected away from the top-two candidate bboxes.
 flagged={e[1] for _,e in all_candidates}; controlboxes=[bound(b,w,h) for b in parser.boxes if bound(b,w,h) not in flagged and b[2]>b[0] and b[3]>b[1]]
 for box in rnd.sample(controlboxes,min(2,len(controlboxes))):all_candidates.append(('control',(0.,box,None,{'selection':'random non-top-candidate box'})))
 raw[id]={'detector_counts':{k:len(v) for k,v in candidates.items()},'controls':min(2,len(controlboxes))}
 for det,(value,box,row,details) in all_candidates:
  counter+=1; cid=f'crop-{counter:04d}'; order=rows[:];rnd.shuffle(order); labels={chr(65+i):r for i,r in enumerate(order)};keymap[cid]={'labels':labels,'flagged_row':row};x0,y0,x1,y1=box
  if x1<=x0 or y1<=y0:continue
  crops=[('Source',images['src'].crop(box))]+[(label,images[r].crop(box)) for label,r in labels.items()]; cw=(x1-x0)*4;ch=(y1-y0)*4;sheet=Image.new('RGB',(cw*len(crops),ch+24),'white'); draw=ImageDraw.Draw(sheet)
  for i,(label,crop) in enumerate(crops):draw.text((i*cw+2,3),label,fill='black');sheet.paste(crop.resize((cw,ch),Image.Resampling.NEAREST),(i*cw,24))
  sheet.save(D/(cid+'.png'));index.append({'crop_id':cid,'page':id,'bbox':box,'detector':det,'raw_score':value,'raw_components':details,'status':'control' if det=='control' else 'suspected'})
 for im in images.values():im.close()
raw_scores.close()
(D/'blind-index.json').write_text(json.dumps(index,indent=2)+'\n');(B/'pilot/blind-key.json').write_text(json.dumps(keymap,indent=2)+'\n');(Q/'results/triage.json').write_text(json.dumps({'status':'suspected only; no human adjudication yet','calibration':'Within each pilot page, top two scores per detector and 99.5th percentile recorded; no threshold establishes a confirmed defect.','thresholds':thresholds,'counts':raw,'crop_count':len(index)},indent=2)+'\n')
