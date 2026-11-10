#!/usr/bin/env python3
"""Measure estimator hypotheses against OCR-local source contrast, never emit vectors.
Reference is independent of candidate segmentation; it is a proxy, not labels.
"""
import json,pathlib,sys,hashlib,io
import pikepdf
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
from scipy.ndimage import label,binary_fill_holes
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); O=R/'local/hvc41'; E=R/'hvc41'; O.mkdir(parents=True,exist_ok=True);(O/'masks').mkdir(exist_ok=True)
WTS=np.array([.2126,.7152,.0722]); rows=[x for x in json.loads((E/'estimator-measurements.json').read_text()) if x['set']=='corpus'] if '--controls-only' in sys.argv else []
def luma(rgb):return np.asarray(rgb,dtype=np.float32)@WTS.astype(np.float32)
def upper_median(a):return np.partition(a,len(a)//2,axis=0)[len(a)//2]
def corner(a):
 h,w=a.shape[:2];return upper_median(np.array([upper_median(a[y:y+6,x:x+6].reshape(-1,3)) for x,y in ((0,0),(w-6,0),(0,h-6),(w-6,h-6))]))
def tiled(y,sz=128):
 h,w=y.shape;out=np.zeros((h,w),bool)
 for y0 in range(0,h,sz):
  for x0 in range(0,w,sz):
   z=y[y0:y0+sz,x0:x0+sz]; med=np.median(z);out[y0:y0+sz,x0:x0+sz]=np.abs(z-med)>60
 return out
def bg_values(a,y):
 h,w=y.shape;mid=y[h//10:9*h//10,w//10:9*w//10]; colors=a[h//10:9*h//10,w//10:9*w//10];hist=np.bincount(np.minimum((mid/8).astype(int),31).ravel(),minlength=32);k=int(hist.argmax());rgb=colors[(mid>=k*8)&(mid<(k+1)*8)];mode=upper_median(rgb.reshape(-1,3));candidates=np.flatnonzero(hist>=mid.size*.02);bright=int(candidates[-1]) if len(candidates) else k;brgb=upper_median(colors[(mid>=bright*8)&(mid<(bright+1)*8)].reshape(-1,3));center=upper_median(colors.reshape(-1,3));return mode,brgb,center,{'interior_mode_fraction':float(hist[k]/mid.size),'bright_mode_fraction':float(hist[bright]/mid.size)}
def do(setname,doc,page,a,meta,reverse,adobe_objects=None):
 h,w=a.shape[:2]; y=luma(a);lines=chars_from_hocr(meta['hocr']);boxes=[c['box'] for l in lines for word in l['words'] for c in word['chars']];ink=np.zeros((h,w),bool);paper=np.zeros((h,w),bool);roi=np.zeros((h,w),bool);valid=[];bg_samples=[]
 for b in boxes:
  x0,y0,x1,y1=map(int,b);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
  if x1-x0<2 or y1-y0<2:continue
  sub=y[y0:y1,x0:x1]; bg=float(np.percentile(sub,15 if reverse else 85));r=sub>bg+30 if reverse else sub<bg-30;p=sub<bg+10 if reverse else sub>bg-10
  if r.sum()<3 or p.sum()<3:continue
  ink[y0:y1,x0:x1]|=r;paper[y0:y1,x0:x1]|=p;roi[y0:y1,x0:x1]=True;valid.append((x0,y0,x1,y1));bg_samples.append(bg)
 paper &= ~ink
 cp=corner(a);mode,bright,interior,info=bg_values(a,y)
 modes={'corner':cp,'interior_mode':mode,'bright_mode':bright,'interior_median':interior};masks={k:np.abs(y-float(luma(v)))>60 for k,v in modes.items()};masks['tile_median_128']=tiled(y)
 border=np.zeros((h,w),bool);dy=max(1,h//20);dx=max(1,w//20);border[:dy]=True;border[-dy:]=True;border[:,:dx]=True;border[:,-dx:]=True
 ref_n=int(ink.sum());pn=int(paper.sum());rgb_ref=upper_median(a[ink]) if ref_n else None;paper_rgb=upper_median(a[paper]) if pn else None
 estimates={}
 for name,m in masks.items():
  true=int((m&ink).sum());false=int((m&paper).sum());outside=int((m&~roi).sum());small_total=small_hit=holes_ref=holes_match=0
  for x0,y0,x1,y1 in valid:
   ref=ink[y0:y1,x0:x1];test=m[y0:y1,x0:x1]; lab,n=label(ref); sizes=np.bincount(lab.ravel()); ids=np.flatnonzero((sizes>0)&(sizes<=4)); ids=ids[ids!=0]
   for k in ids:small_total+=1;small_hit+=int(np.any(test & (lab==k)))
   rh=int(label(binary_fill_holes(ref)&~ref)[1]);th=int(label(binary_fill_holes(test)&~test)[1]);holes_ref+=rh;holes_match+=int(rh>0 and rh==th)*rh
  estimates[name]={'paper_rgb':modes[name].tolist() if name in modes else None,'reference_ink_recall':true/ref_n if ref_n else None,'reference_paper_false_admission':false/pn if pn else None,'foreground_pixels':int(m.sum()),'foreground_outside_ocr_boxes':outside,'border_foreground_fraction':float(m[border].mean()),'small_components':small_total,'small_components_hit':small_hit,'reference_holes':holes_ref,'holes_equal_count':holes_match}
  if (setname=='corpus' and ((doc=='historical') or (doc=='receipts' and page in (4,6,7,8,9)))) or (setname!='corpus' and doc in ('black_border','reverse_page','reverse_panel','dark_table-108','reverse_page-108','reverse_panel-108','yellow')):
   Image.fromarray((m*255).astype('uint8')).save(O/'masks'/f'{setname}-{doc}-{page:02d}-{name}.png')
 fg=masks['corner'];fg_rgb=upper_median(a[fg]) if fg.any() else cp
 adobe_cov=None
 if adobe_objects is not None and ref_n:
  mask=np.zeros((h,w),bool)
  for o in adobe_objects:
   x0,y0,x1,y1=o['box'];x0=max(0,int(x0));y0=max(0,int(y0));x1=min(w,int(np.ceil(x1)));y1=min(h,int(np.ceil(y1)));mask[y0:y1,x0:x1]=True
  adobe_cov=float((ink&mask).sum()/ref_n)
 row={'set':setname,'document':doc,'page':page,'width':w,'height':h,'dpi':300,'source_polarity_reference':'light_on_dark' if reverse else 'dark_on_light','ocr_symbols':len(boxes),'usable_reference_boxes':len(valid),'reference_text_ink_pixels':ref_n,'reference_paper_pixels':pn,'source_text_ink_rgb':rgb_ref.tolist() if rgb_ref is not None else None,'source_local_paper_rgb':paper_rgb.tolist() if paper_rgb is not None else None,'corner_paper_rgb':cp.tolist(),'corner_ink_rgb':fg_rgb.tolist(),'adobe_visible_bbox_overlap_reference_ink':adobe_cov,'estimators':estimates,**info}
 rows.append(row);print(setname,doc,page,'boxes',len(valid),'ink',ref_n,flush=True)
if '--controls-only' not in sys.argv:
 for doc in ('historical','receipts','financial','mixed','forms'):
  report=json.loads((R/'local/ink33r'/f'{doc}.pdf.json').read_text())
  for i,p in enumerate(report['pages'],1):
   a=np.asarray(Image.open(R/'local/ink33r/renders'/doc/f'{i:02d}-source.png').convert('RGB'));m=json.loads((R/'local/ink33r/maps'/doc/f'{i:02d}.json').read_text());do('corpus',doc,i,a,p,False,m['adobe_objects'])
for group,folder,reported,truthpath in [('control','controls','control-measured','controls-truth.json'),('supplemental','controls-supplemental','control-supplemental-measured','supplemental-truth.json'),('positive','positive-controls','control-positive-measured','positive-controls-truth.json')]:
 truth=json.loads((R/'ink37'/truthpath).read_text())
 for name,info in truth['cases'].items():
  path=R/'local/ink37'/folder/(name+'.pdf'); reportpath=R/'local/ink37'/reported/(name+'.pdf.json')
  if not path.exists() or not reportpath.exists():print('MISSING',group,name,flush=True);continue
  report=json.loads(reportpath.read_text());pdf=pikepdf.open(path);obj=next(o for o in pdf.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');a=np.asarray(Image.open(io.BytesIO(obj.read_raw_bytes())).convert('RGB'));pdf.close()
  if (a.shape[1],a.shape[0])!=(report['pages'][0]['raster_width'],report['pages'][0]['raster_height']):print('SIZE_MISMATCH',group,name,a.shape,flush=True);continue
  do(group,name,1,a,report['pages'][0],name.startswith('reverse') or name == 'photograph')
(E/'estimator-measurements.json').write_text(json.dumps(rows,indent=2)+'\n');print('COMPLETE',len(rows),flush=True)
