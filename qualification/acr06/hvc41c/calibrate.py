#!/usr/bin/env python3
"""Context evidence on development controls only; never tests historical pages."""
import pathlib,json,sys,io,hashlib,collections
import numpy as np,pikepdf
from PIL import Image
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41c';L=R/'local';wt=np.array([.2126,.7152,.0722]);out=[]
cases=[('white','control','white',1),('financial-01','financial',None,1),('financial-02','financial',None,2),('reverse-panel','control','reverse_panel',1),('small-receipt','supplemental','small_receipt',1),('black-border','control','black_border',1),('photograph','control','photograph',1)]
for name,group,case,page in cases:
 if group=='financial':
  source=np.asarray(Image.open(L/'ink33r/renders/financial'/f'{page:02}-source.png').convert('RGB'));meta=json.loads((L/'ink33r/financial.pdf.json').read_text())['pages'][page-1];arts=json.loads((L/'hvc41b/corpus/financial'/f'p{page:06}-outlines.json').read_text())['artwork']
 else:
  folders={'control':('controls','control-measured'),'supplemental':('controls-supplemental','control-supplemental-measured')};f,g=folders[group];pdf=pikepdf.open(L/'ink37'/f/f'{case}.pdf');obj=next(o for o in pdf.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');source=np.asarray(Image.open(io.BytesIO(obj.read_raw_bytes())).convert('RGB'));pdf.close();meta=json.loads((L/'ink37'/g/f'{case}.pdf.json').read_text())['pages'][0];arts=json.loads((L/'hvc41b/controls'/group/case/'p000001-outlines.json').read_text())['artwork']
 lum=source.astype(np.float32)@wt;h,w=lum.shape;words=[word for line in chars_from_hocr(meta['hocr']) for word in line['words']];excluded=np.zeros((h,w),bool);protected=[]
 for region in meta.get('protected_regions',[]):
  pts=region.get('polygon',[]) if isinstance(region,dict) else []
  if not pts:protected.append((0,0,w,h));continue
  protected.append((int(min(p[0] for p in pts)),int(min(p[1] for p in pts)),int(np.ceil(max(p[0] for p in pts))),int(np.ceil(max(p[1] for p in pts)))))
 for x0,y0,x1,y1 in protected:excluded[max(0,y0-1):min(h,y1+1),max(0,x0-1):min(w,x1+1)]=True
 for x in arts:
  x0,y0,x1,y1=map(int,x['bbox']);excluded[max(0,y0-1):min(h,y1+1),max(0,x0-1):min(w,x1+1)]=True
 for word in words:
  x0,y0,x1,y1=map(int,word['box']);excluded[max(0,y0-1):min(h,y1+1),max(0,x0-1):min(w,x1+1)]=True
 excluded[:2]=True;excluded[-2:]=True;excluded[:,:2]=True;excluded[:,-2:]=True
 for wi,word in enumerate(words):
  x0,y0,x1,y1=map(int,word['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1);padding=max(4,min(18,round(.35*max(1,y1-y0))));a=max(0,x0-padding);b=max(0,y0-padding);c=min(w,x1+padding);d=min(h,y1+padding);ring=lum[b:d,a:c][~excluded[b:d,a:c]];reason=[];paper=float(np.median(ring)) if len(ring) else None
  if len(ring)<32:reason.append('insufficient_exterior_ring')
  if paper is not None and paper<70:reason.append('dark_surround')
  if len(ring)>=32 and np.percentile(ring,90)-np.percentile(ring,10)>25:reason.append('inconsistent_surround')
  q=lum[y0:y1,x0:x1];ink=(q<paper-30) if paper is not None else np.zeros(q.shape,bool);count=int(ink.sum());frac=float(ink.mean()) if ink.size else 0.0
  if count<6:reason.append('insufficient_dark_ink')
  if frac<.02 or frac>.75:reason.append('ink_fraction')
  contrast=paper-float(np.median(q[ink])) if count else None
  if contrast is None or contrast<100:reason.append('low_contrast')
  if any(a<x1 and c>x0 and b<y1 and d>y0 for a,b,c,d in protected):reason.append('protected_overlap')
  # Any ownership artwork bbox intersecting the word makes evidence ambiguous.
  if any(x['bbox'][0]<x1 and x['bbox'][2]>x0 and x['bbox'][1]<y1 and x['bbox'][3]>y0 for x in arts):reason.append('artwork_bbox_overlap')
  out.append({'control':name,'word_index':wi,'word_id':word['id'],'text_ocr_unverified':''.join(x['text'] for x in word['chars']),'bbox':word['box'],'ring_pixels':len(ring),'paper_luma':paper,'ring_luma_p10_p90':(np.percentile(ring,[10,90]).tolist() if len(ring) else None),'dark_ink_pixels':count,'dark_fraction':frac,'contrast':contrast,'admitted':not reason,'reasons':reason})
 print(name,'words',len(words),'admitted',sum(x['admitted'] for x in out if x['control']==name),flush=True)
(E/'calibration-words.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
