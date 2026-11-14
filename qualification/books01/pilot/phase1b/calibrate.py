#!/usr/bin/env python3
"""Score reviewed crop/row pairs on aligned renders; calibrate in-sample only."""
import collections,json,pathlib
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_erosion,distance_transform_edt
from skimage.color import rgb2lab,deltaE_ciede2000
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot'; refs=json.loads((Q/'results/phase1b/reference.json').read_text())['crops'];locks=json.loads((P/'sources.lock.json').read_text())['pages'];geo=json.loads((Q/'results/phase1b/geometry.json').read_text())['pages']; corpus=json.loads((P/'corpus.frozen.json').read_text());works={p['id']:p['work'] for p in corpus['pages']};rows=['sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E'];detectors=['glyph_shape','missing_ink','spurious_ink','illustration_colour','border_inversion']; assessment='AI-assessed, provisional (not human-adjudicated)';cache={}; gtcache={}
def getim(id,row):
 key=(id,row)
 if key not in cache:
  dpi=str(int(locks[id]['resolved_dpi']));g=geo[id][row]['pdfium'][dpi];cache[key]=Image.open(B/g['aligned_render_path']).convert('RGB') if g['status']=='accepted' else None
 return cache[key]
def graphic(id,box):
 if id not in gtcache:
  page=id.split('/')[-1];g=json.loads((B/'gt'/works[id]/(page+'.json')).read_text());im=Image.new('1',tuple(g['source_dimensions']));d=ImageDraw.Draw(im)
  for r in g['regions']:
   if r['kind'] in ('ImageRegion','GraphicRegion','ChartRegion') and len(r['polygon'])>=3:d.polygon([tuple(x) for x in r['polygon']],fill=1)
  for r in g['regions']:
   if r['kind']=='TextRegion' and len(r['polygon'])>=3:d.polygon([tuple(x) for x in r['polygon']],fill=0)
  gtcache[id]=im
 im=gtcache[id];x=int((box[0]+box[2])/2);y=int((box[1]+box[3])/2);return 0<=x<im.width and 0<=y<im.height and bool(im.getpixel((x,y)))
def calc(src,out,box,id):
 x0,y0,x1,y1=map(int,box);pad=5;w,h=src.size; box=(max(0,x0),max(0,y0),min(w,x1),min(h,y1));x0,y0,x1,y1=box
 if x1<=x0 or y1<=y0:return None
 a=np.asarray(src.crop(box));b=np.asarray(out.crop(box));gray=lambda x:.299*x[:,:,0]+.587*x[:,:,1]+.114*x[:,:,2]; ga=gray(a);gb=gray(b);padded=np.asarray(src.crop((max(0,x0-pad),max(0,y0-pad),min(w,x1+pad),min(h,y1+pad))).convert('L'));bg=float(np.percentile(padded,90));low=float(np.percentile(padded,5));threshold=bg-20.; ink=ga<threshold;pred=gb<threshold;source_ink=int(ink.sum());contrast=bg-low;valid=contrast>=20 and source_ink>0;tp=int((ink&pred).sum());ea=ink&~binary_erosion(ink);eb=pred&~binary_erosion(pred);u=int((ea|eb).sum());iou=int((ea&eb).sum())/u if u else None;chamfer=float((distance_transform_edt(~ink)[pred].mean()+distance_transform_edt(~pred)[ink].mean())/2) if ink.any() and pred.any() else None
 colour=float(deltaE_ciede2000(rgb2lab(a),rgb2lab(b)).mean()) if graphic(id,box) else None; edge=min(x0,y0,w-x1,h-y1)<=max(w,h)*.05;inversion=float(np.logical_xor(ga<128,gb<128).mean()) if edge else None
 return {'valid_source_contrast_and_ink':valid,'local_contrast':contrast,'source_ink_pixels':source_ink,'source_ink_fraction':source_ink/ink.size,'contrast_floor':20,'glyph_shape':(1-iou) if valid and iou is not None else None,'contour_iou':iou,'chamfer_px':chamfer,'missing_ink':(source_ink-tp)/source_ink if valid else None,'spurious_ink':(int(pred.sum())-tp)/int(pred.sum()) if valid and pred.any() else (0. if valid else None),'illustration_colour':colour,'border_inversion':inversion}
records=[]
for ref in refs:
 id=ref['page'];src=getim(id,'src')
 for row in rows:
  out=getim(id,row);vals=calc(src,out,ref['bbox'],id) if src is not None and out is not None else None;types=ref['panel_taxonomy_by_row'].get(row,[]);positive=row in ref['provisional_positive_rows'];negative=row==ref['original_flagged_row'] and ref['review_verdict'] in ('false_positive','no_inversion');labels={}
  for det in detectors:
   kind={'glyph_shape':{'wrong_shape','missing_ink'},'missing_ink':{'missing_ink'},'spurious_ink':{'spurious_ink_halo'},'illustration_colour':{'colour_shift','blur_texture'},'border_inversion':{'border_inversion'}}[det]
   pos=positive and bool(kind.intersection(types));neg=negative and ref['original_detector']==det
   if det=='illustration_colour' and not graphic(id,ref['bbox']):pos=False;neg=False
   labels[det]=1 if pos else 0 if neg else None
  records.append({'crop_id':ref['crop_id'],'page':id,'bbox':ref['bbox'],'row':row,'small_box':min(ref['bbox'][2]-ref['bbox'][0],ref['bbox'][3]-ref['bbox'][1])<10,'scores':vals,'labels':labels,'assessment':assessment})
summary={};examples={}
for det in detectors:
 labelled=[r for r in records if r['labels'][det] is not None];positive=[r for r in labelled if r['labels'][det]==1];negative=[r for r in labelled if r['labels'][det]==0];vals=sorted({r['scores'][det] for r in labelled if r['scores'] is not None and r['scores'][det] is not None});threshold=None
 if positive and negative and vals:
  best=None
  for t in vals+[max(vals)+1]:
   tp=sum(r['scores'] is not None and r['scores'][det] is not None and r['scores'][det]>=t for r in positive);tn=sum(r['scores'] is None or r['scores'][det] is None or r['scores'][det]<t for r in negative);quality=(tp/len(positive)+tn/len(negative))/2
   if best is None or quality>best[0]:best=(quality,t)
  threshold=best[1]
 elif positive and not negative:
  valid=[r['scores'][det] for r in positive if r['scores'] is not None and r['scores'][det] is not None]
  if valid:threshold=min(valid)*.5
 elif negative and not positive:
  valid=[r['scores'][det] for r in negative if r['scores'] is not None and r['scores'][det] is not None]
  if valid:threshold=max(valid)+1e-9
 def measure(group):
  pos=[r for r in group if r['labels'][det]==1];neg=[r for r in group if r['labels'][det]==0];hit=lambda r:threshold is not None and r['scores'] is not None and r['scores'][det] is not None and r['scores'][det]>=threshold
  tp=sum(hit(r) for r in pos);fp=sum(hit(r) for r in neg)
  if threshold is None:return {'positive_count':len(pos),'negative_count':len(neg),'true_positive':None,'false_positive':None,'false_negative':None,'precision':None,'recall':None}
  return {'positive_count':len(pos),'negative_count':len(neg),'true_positive':tp,'false_positive':fp,'false_negative':len(pos)-tp,'precision':tp/(tp+fp) if tp+fp and len(neg)>0 else None,'recall':tp/len(pos) if pos else None}
 summary[det]={'threshold':threshold,'threshold_method':'in-sample balanced accuracy if both classes exist; half the smallest positive score when only positives exist; above maximum negative score when only negatives exist; not independently validated','all':measure(labelled),'min_dimension_lt_10_px':measure([r for r in labelled if r['small_box']]),'min_dimension_ge_10_px':measure([r for r in labelled if not r['small_box']]),'assessment':assessment}
 hit=lambda r:threshold is not None and r['scores'] is not None and r['scores'][det] is not None and r['scores'][det]>=threshold
 examples[det]={kind:[{'crop_id':r['crop_id'],'page':r['page'],'row':r['row'],'score':r['scores'][det] if r['scores'] else None,'assessment':assessment} for r in labelled if predicate(r)][:8] for kind,predicate in {'true_positive':lambda r:r['labels'][det]==1 and hit(r),'false_positive':lambda r:r['labels'][det]==0 and hit(r),'missed':lambda r:r['labels'][det]==1 and not hit(r)}.items()}
for im in cache.values():
 if im:im.close()
(Q/'results/phase1b/calibration.json').write_text(json.dumps({'assessment':assessment,'reference_pairs':len(records),'unknown_labels':'excluded; no unlabelled row is assumed negative','small_box_definition':'minimum bbox dimension <10 source pixels; no size suppression','source_contrast_floor':'20 levels in padded local grayscale; requires at least one actual source-ink pixel','detectors':summary,'examples':examples,'raw_scores':records},indent=2)+'\n')
