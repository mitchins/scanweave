#!/usr/bin/env python3
"""Compare local OCR-contrast proxy with exact pristine synthetic ink cores."""
import hashlib,io,json,pathlib,sys
import numpy as np,pikepdf
from PIL import Image
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r');from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');W=np.array([.2126,.7152,.0722],np.float32);rows=[]
for group,folder,reported,truthfile in [('control','controls','control-measured','controls-truth.json'),('supplemental','controls-supplemental','control-supplemental-measured','supplemental-truth.json'),('positive','positive-controls','control-positive-measured','positive-controls-truth.json')]:
 truth=json.loads((R/'ink37'/truthfile).read_text())
 for name,info in truth['cases'].items():
  pdfpath=R/'local/ink37'/folder/f'{name}.pdf';pngpath=R/'local/ink37'/folder/f'{name}.png';reportpath=R/'local/ink37'/reported/f'{name}.pdf.json'
  if not all(x.exists() for x in (pdfpath,pngpath,reportpath)):continue
  assert hashlib.sha256(pngpath.read_bytes()).hexdigest()==info['png_sha256'];assert hashlib.sha256(pdfpath.read_bytes()).hexdigest()==info['pdf_sha256'];pristine=np.asarray(Image.open(pngpath).convert('RGB'));pdf=pikepdf.open(pdfpath);im=next(o for o in pdf.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');src=np.asarray(Image.open(io.BytesIO(im.read_raw_bytes())).convert('RGB'));pdf.close();h,w=src.shape[:2];y=src.astype(np.float32)@W;meta=json.loads(reportpath.read_text())['pages'][0];ref=np.zeros((h,w),bool);roi=np.zeros((h,w),bool);reverse=name.startswith('reverse') or name=='photograph'
  for line in chars_from_hocr(meta['hocr']):
   for word in line['words']:
    for c in word['chars']:
     x0,y0,x1,y1=map(int,c['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
     if x1-x0<2 or y1-y0<2:continue
     z=y[y0:y1,x0:x1];bg=np.percentile(z,15 if reverse else 85);ink=z>bg+30 if reverse else z<bg-30;paper=z<bg+10 if reverse else z>bg-10
     if ink.sum()<3 or paper.sum()<3:continue
     ref[y0:y1,x0:x1]|=ink;roi[y0:y1,x0:x1]=True
  col=np.asarray(info['ink_rgb'],np.int16);truthmask=np.all(np.abs(pristine.astype(np.int16)-col)<=1,axis=2)&roi;core=int(truthmask.sum());hit=int((truthmask&ref).sum())
  def upper(a):return np.partition(a,len(a)//2,axis=0)[len(a)//2]
  cp=upper(np.array([upper(src[yy:yy+6,xx:xx+6].reshape(-1,3)) for xx,yy in ((0,0),(w-6,0),(0,h-6),(w-6,h-6))]));mid=y[h//10:9*h//10,w//10:9*w//10];cl=src[h//10:9*h//10,w//10:9*w//10];hist=np.bincount(np.minimum((mid/8).astype(int),31).ravel(),minlength=32);mode=int(hist.argmax());poss=np.flatnonzero(hist>=mid.size*.02);bright=int(poss[-1]) if len(poss) else mode
  rgb=lambda k:upper(cl[(mid>=k*8)&(mid<(k+1)*8)].reshape(-1,3));vals={'corner':cp,'interior_mode':rgb(mode),'bright_mode':rgb(bright),'interior_median':upper(cl.reshape(-1,3))};masks={k:np.abs(y-float(v@W))>60 for k,v in vals.items()};tile=np.zeros((h,w),bool)
  for yy in range(0,h,128):
   for xx in range(0,w,128):
    z=y[yy:yy+128,xx:xx+128];tile[yy:yy+128,xx:xx+128]=np.abs(z-np.median(z))>60
  masks['tile_median_128']=tile
  background=([35,39,45] if name=='reverse_panel' else [28,32,36] if name.startswith('reverse_panel-') else info.get('paper_rgb'));papermask=(np.all(np.abs(pristine.astype(np.int16)-np.array(background,np.int16))<=1,axis=2)&roi) if background else np.zeros((h,w),bool);paper_n=int(papermask.sum());direct={k:{'pristine_core_recall':float(m[truthmask].mean()) if core else None,'pristine_paper_false_admission':float(m[papermask].mean()) if paper_n else None,'pristine_paper_pixels':paper_n} for k,m in masks.items()}
  rows.append({'set':group,'case':name,'png_sha256':info['png_sha256'],'pdf_sha256':info['pdf_sha256'],'reference_polarity':'light' if reverse else 'dark','pristine_ink_core_pixels_in_accepted_boxes':core,'reference_core_recall':hit/core if core else None,'reference_pixels':int(ref.sum()),'direct_pristine_core_and_paper':direct,'note':'Exact RGB core; excludes antialiasing and may include same-colour artwork in OCR boxes. Not full truth segmentation.'});print(group,name,core,hit/core if core else None,flush=True)
(R/'hvc41/reference-controls.json').write_text(json.dumps(rows,indent=2)+'\n');print('COMPLETE',len(rows),flush=True)
