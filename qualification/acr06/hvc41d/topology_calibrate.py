import json,pathlib,numpy as np
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d'; rows=json.loads((E/'calibration-exploratory.json').read_text())['rows'];out=[]
def masks(r):
 a=np.asarray(Image.open(r['panel']).convert('L'))[::4,::4];cw=a.shape[1]//4;x0,y0,x1,y1=map(int,r['ocr_box']);w=x1-x0+6;h=y1-y0+6;return a[20:20+h,2*cw:2*cw+w]>128,a[20:20+h,3*cw:3*cw+w]>128
def guard(a,b):
 ah=nd.binary_fill_holes(a)&~a;bh=nd.binary_fill_holes(b)&~b
 # For each enclosed background component on either side, require an overlapping counterpart.
 for u,v in ((ah,bh),(bh,ah)):
  label,n=nd.label(u)
  for j in range(1,n+1):
   comp=label==j
   if comp.sum()>=2 and not (nd.binary_dilation(comp)&v).any():return False
 return True
for i,r in enumerate(rows):
 a,b=masks(r); holes=nd.binary_fill_holes(b)&~b
 before=guard(a,b);after=guard(a,b|holes) if holes.sum()>=2 else None
 out.append({'index':i,'positive_guard':before,'filled_counter_guard':after,'score':r['tolerant_score'],'area':r['area_ratio'],'fill':r['fill_luminance_error'],'font_hole_pixels':int(holes.sum())})
(E/'topology-calibration.json').write_text(json.dumps(out,indent=2)+'\n')
sel=lambda r:r['score']>=.98 and .8<=r['area']<=1.2 and r['fill'] is not None and r['fill']<=15
print('positive before',sum(sel(r) for r in out),'positive after',sum(sel(r) and r['positive_guard'] for r in out),'/',len(out))
neg=[r for r in out if r['filled_counter_guard'] is not None]
print('filled counter rejected by topology',sum(not r['filled_counter_guard'] for r in neg),'/',len(neg))
print('filled counter survivors',[(r['index'],r['font_hole_pixels']) for r in neg if sel(r) and r['filled_counter_guard']])
