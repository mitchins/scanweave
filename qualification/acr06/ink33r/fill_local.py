#!/usr/bin/env python3
"""Audit visible text fills against OCR-local source paper evidence.

Paper is the median of per-word 85th-percentile source luminances, using the
same OCR boxes and Rec.709 luminance as measure.py. A separate per-object test
uses the 85th percentile within its source-coordinate bounding box expanded
by two pixels; both are proxies and are reported without assuming polarity.
"""
import json, pathlib
import numpy as np
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); E=R/'ink33r';O=R/'local/ink33r'
def lum(x):return np.asarray(x,dtype=float)@np.array([.2126,.7152,.0722])
def local(im,b,pad=0):
 h,w=im.shape[:2];x0=max(0,int(np.floor(b[0]))-pad);y0=max(0,int(np.floor(b[1]))-pad);x1=min(w,int(np.ceil(b[2]))+pad);y1=min(h,int(np.ceil(b[3]))+pad)
 return float(np.percentile(lum(im[y0:y1,x0:x1]),85)) if x1>x0 and y1>y0 else None
def rgb(space,c):
 if space=='/DeviceRGB' and len(c)==3:return [round(255*float(x),4) for x in c]
 if space=='/DeviceGray' and len(c)==1:return [round(255*float(c[0]),4)]*3
 return None
runs=json.loads((E/'operator-audit.json').read_text());out=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 for i,op in enumerate(runs[doc]['scanweave']['pages'],1):
  data=json.loads((O/'maps'/doc/f'{i:02d}.json').read_text());im=np.asarray(Image.open(O/'renders'/doc/f'{i:02d}-source.png').convert('RGB'))
  papers=[v for line in data['lines'] for word in line['words'] if word.get('box') and (v:=local(im,word['box'])) is not None];paper=float(np.median(papers)) if papers else None
  fills=[]
  for key,count in op['visible_fill_shows'].items():
   space,color=json.loads(key);c=rgb(space,color);y=float(lum(c)) if c is not None else None;fills.append({'space':space,'rgb_255':c,'luminance':y,'show_operators':count,'above_page_local_paper':y>paper if y is not None and paper is not None else None})
  local_flag=[];local_n=0
  for obj in data['scan_objects']:
   if obj.get('rgba') is None:continue
   y=float(lum(obj['rgba'][:3]));background=local(im,obj['box'],2)
   if background is not None:
    local_n+=1
    if y>background:local_flag.append({'box':obj['box'],'rgb':obj['rgba'][:3],'fill_luminance':y,'object_local_paper_p85':background})
  out.append({'document':doc,'page':i,'page_local_paper_luminance':paper,'paper_word_boxes':len(papers),'visible_fills':fills,'visible_object_local_checked':local_n,'visible_object_above_local_count':len(local_flag),'visible_object_above_local_examples':local_flag[:10]})
(E/'fill-local.json').write_text(json.dumps(out,indent=2)+'\n')
for r in out:
 for f in r['visible_fills']:
  if f['above_page_local_paper']:print('PAGE FLAG',r['document'],r['page'],f,flush=True)
 if r['visible_object_above_local_count']:print('OBJECT FLAG',r['document'],r['page'],r['visible_object_above_local_count'],flush=True)
