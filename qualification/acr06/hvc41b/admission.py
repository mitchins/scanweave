#!/usr/bin/env python3
"""Apply pre-frozen OCR-local region admission to existing traced proposals."""
import json,sys,pathlib,collections
import numpy as np
from PIL import Image
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';L=R/'local';wt=np.array([.2126,.7152,.0722]);base=json.loads((L/'ink33r/historical.pdf.json').read_text());out=[]
for page in (1,3,4):
 run=L/('hvc41/trial2' if page==1 else 'hvc41/contact/interior');dump=json.loads((run/'historical'/f'p{page:06}.json').read_text());actualpath=L/('hvc41b/interior' if page==1 else 'hvc41b/border')/f'p{page:06}-outlines.json';actual_ids={x['symbol'] for x in json.loads(actualpath.read_text())['outlines']} if actualpath.exists() else set();src=np.asarray(Image.open(L/'ink33r/renders/historical'/f'{page:02}-source.png').convert('RGB'));h,w=src.shape[:2];lum=src.astype(np.float32)@wt;paper=float(np.array(dump['paper'])@wt);words=[w for line in chars_from_hocr(base['pages'][page-1]['hocr']) for w in line['words']];boxdata={}
 for wi,word in enumerate(words):
  checks=[]
  for c in word['chars']:
   x0,y0,x1,y1=map(int,c['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
   if x1-x0<2 or y1-y0<2: checks.append({'accepted':False,'reason':['invalid_box']});continue
   q=lum[y0:y1,x0:x1];p15,p85=np.percentile(q,[15,85]);dark=q<p85-30;edge=np.concatenate([q[0,:],q[-1,:],q[:,0],q[:,-1]]);frac=float(dark.mean());sur=float((np.abs(edge-p85)<=24).mean());reasons=[]
   if not .05<=frac<=.45:reasons.append('dark_fraction')
   if p85-p15<60:reasons.append('contrast')
   if sur<.70:reasons.append('surround')
   if abs(p85-paper)>24:reasons.append('paper_agreement')
   if dark.sum()<6:reasons.append('ink_pixels')
   checks.append({'accepted':not reasons,'reason':reasons,'bbox':c['box'],'text':c['text'],'dark_fraction':frac,'contrast':float(p85-p15),'surround_fraction':sur,'paper_difference':abs(float(p85)-paper)})
  boxdata[wi]=checks
 for u in dump['units']:
  if not u['emitted_before_containment'] and u['symbol'] not in actual_ids:continue
  wi=int(u['symbol'][1:7]);checks=boxdata.get(wi,[]);accepted=bool(checks) and all(z['accepted'] for z in checks); ii=np.asarray(u['mask_indices'],dtype=np.int64);x=int(u['bbox'][0])+ii%u['crop_w'];y=int(u['bbox'][1])+ii//u['crop_w'];inpage=(x>=0)&(y>=0)&(x<w)&(y<h);x=x[inpage];y=y[inpage];samples=[]
  for ck in checks:
   if 'bbox' not in ck:continue
   x0,y0,x1,y1=map(int,ck['bbox']);sel=(x>=x0)&(x<x1)&(y>=y0)&(y<y1);q=lum[max(y0,0):min(y1,h),max(x0,0):min(x1,w)]
   if not q.size:continue
   sel &= lum[y,x] < np.percentile(q,85)-30
   if np.any(sel):samples.append(src[y[sel],x[sel]])
  ink=np.median(np.concatenate(samples),axis=0).astype(int).tolist() if samples else None
  out.append({'page':page,'symbol':u['symbol'],'ocr_char_unverified':u['text'],'bbox':u['bbox'],'region_checks':checks,'region_admitted':accepted,'current_border_pilot_proposal':u['symbol'] in actual_ids,'source_supported_ink_rgb':ink,'global_ink_rgb':dump['ink'],'outcome':'not emitted: region admission failed' if not accepted else 'not emitted: independent rendered glyph validation not yet completed','validation_metrics':None})
 print('page',page,'proposals',sum(x['page']==page for x in out),'admitted',sum(x['region_admitted'] for x in out if x['page']==page),flush=True)

for page in (1,3,4):
 (E/f'admission-ledger-{page:02}.json').write_text(json.dumps([x for x in out if x['page']==page],indent=2)+'\n')
