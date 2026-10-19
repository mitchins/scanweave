"""Fixed-position rendered geometry, ink-width proxy and counter diagnostics.
All thresholds/cells are shared across source, pristine and both PDF renderers.
No per-candidate rescaling. Width=2*area/4-neighbour perimeter is a proxy,
not a font stem-width estimate. Counter counts are threshold-sensitive.
"""
import json,os
from pathlib import Path
from collections import deque
import numpy as np
from PIL import Image
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
def shape(a):
 m=a<170;ys,xs=np.nonzero(m)
 if not len(xs):return {'area':0,'bbox':None,'centroid':None,'width_proxy':0,'counters':0}
 p=np.pad(m,1);per=int(np.count_nonzero(p[1:]!=p[:-1])+np.count_nonzero(p[:,1:]!=p[:,:-1]));white=~m;seen=np.zeros(m.shape,bool);holes=0;h,w=m.shape
 for y,x in zip(*np.nonzero(white)):
  if seen[y,x]:continue
  q=deque([(y,x)]);seen[y,x]=True;edge=False;n=0
  while q:
   yy,xx=q.popleft();n+=1;edge|=yy==0 or xx==0 or yy==h-1 or xx==w-1
   for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
    y2,x2=yy+dy,xx+dx
    if 0<=y2<h and 0<=x2<w and white[y2,x2] and not seen[y2,x2]:seen[y2,x2]=True;q.append((y2,x2))
  if not edge and n>=2:holes+=1
 return {'area':int(m.sum()),'bbox':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],'centroid':[float(xs.mean()),float(ys.mean())],'width_proxy':2*int(m.sum())/max(1,per),'counters':holes}
for dpi in map(int,os.environ.get('SCANWEAVE_TYPOGRAPHY_DPI','300,600').split(',')):
 base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}';metrics=json.loads((B/str(dpi)/os.environ.get('SCANWEAVE_TYPOGRAPHY_ARM','final')/'metrics.json').read_text());rows=[]
 for pi in range(8):
  truth=np.asarray(Image.open(base/'oracle'/f'page{pi:02}.png').convert('L'));images={'source':np.asarray(Image.open(base/'input'/f'page{pi:02}.png').convert('L'))}
  for arm in ('adobe','previous',os.environ.get('SCANWEAVE_TYPOGRAPHY_ARM','final')):
   for ren in ('poppler','pdfium'):images[arm+'/'+ren]=np.asarray(Image.open(B/str(dpi)/arm/'exact'/f'{ren}-{pi+1}.png').convert('L'))
  for r in metrics['glyphs']:
   if r['geometry']!='exact' or r['page']!=pi or 'source_isolated' not in r:continue
   x0,y0,x1,y1=map(int,r['bbox']);pad=round((4 if ord(r['text'][0])>127 else 5)*dpi/300);sl=(slice(y0+pad,y1-pad),slice(x0+pad,x1-pad));t=shape(truth[sl]);row={'page':pi,'id':r['id'],'text':r['text'],'truth':t,'arms':{}}
   for name,a in images.items():
    s=shape(a[sl]);s['ink_area_bias']=(s['area']-t['area'])/max(1,t['area']);s['counter_delta']=s['counters']-t['counters'];s['width_proxy_bias']=s['width_proxy']-t['width_proxy']
    if s['bbox'] and t['bbox']:s['bbox_delta_px']=[a-b for a,b in zip(s['bbox'],t['bbox'])];s['centroid_distance_px']=float(np.linalg.norm(np.array(s['centroid'])-t['centroid']))
    row['arms'][name]=s
   rows.append(row)
 summary={name:{'n':len(rows),'mean_ink_area_bias':float(np.mean([r['arms'][name]['ink_area_bias'] for r in rows])),'mean_width_proxy_bias_px':float(np.mean([r['arms'][name]['width_proxy_bias'] for r in rows])),'counter_mismatches':sum(r['arms'][name]['counter_delta']!=0 for r in rows),'mean_absolute_bbox_edge_error_px':float(np.mean([abs(v) for r in rows for v in r['arms'][name].get('bbox_delta_px',[])])),'mean_centroid_error_px':float(np.mean([r['arms'][name]['centroid_distance_px'] for r in rows if 'centroid_distance_px' in r['arms'][name]]))} for name in images}
 (B/str(dpi)/(os.environ.get('SCANWEAVE_TYPOGRAPHY_ARM','final')+'-geometry.json')).write_text(json.dumps({'method':__doc__,'summary':summary,'instances':rows},indent=2));print(dpi,summary,flush=True)
