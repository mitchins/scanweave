"""Fit candidate Gaussian edge profiles; uncertainty remains explicit."""
import json,pathlib,sys
import numpy as np
from scipy import ndimage as ndi,optimize,special
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'stroke01'))
import prototype as p
B=pathlib.Path('/data/coding/scanweave/work/books01');O=B/'stroke02'; C={'8967062':(1585,203,2022,242),'12342014':(84,360,611,442)}
def fit(img):
 obs=p.linear(img);g=p.rgb_luma(obs); profiles=[];x=np.arange(-5,6,dtype=float)
 # Only one-dimensional edges with a clear plateau on both sides are attempted.
 for axis in [0,1]:
  image=g if axis==1 else g.T
  for row in image:
   grad=np.abs(np.diff(row));spots=np.where(grad>.025)[0]
   for idx in spots:
    i=int(idx)
    if i<6 or i+6>=len(row):continue
    v=row[i-5:i+6];lo=float(np.median(v[:3]));hi=float(np.median(v[-3:]));contrast=abs(hi-lo)
    if contrast<.08 or np.ptp(v[:3])>contrast*.25 or np.ptp(v[-3:])>contrast*.25:continue
    if ((np.diff(v)*(hi-lo))<-.025*contrast).sum()>2:continue
    def fun(q):return q[0]+q[1]*special.ndtr((x-q[2])/q[3])-v
    q=optimize.least_squares(fun,[lo,hi-lo,0.,.8],bounds=([-1.,-2.,-2.,.2],[2.,2.,2.,3.]),max_nfev=45)
    rmse=float(np.sqrt(np.mean(fun(q.x)**2)))
    if rmse<.04*contrast and abs(q.x[1])>.08:
     profiles.append({'sigma':float(q.x[3]),'contrast':contrast,'rmse':rmse,'clamped':bool(q.x[3]<.22 or q.x[3]>2.98)})
 if profiles:
  values=np.array([v['sigma'] for v in profiles]);ci=np.quantile(values,[.1,.25,.5,.75,.9]); return {'n':len(profiles),'sigma_quantiles':ci.tolist(),'boundary_fit_count':sum(v['clamped'] for v in profiles)}
 return {'n':0,'sigma_quantiles':None,'boundary_fit_count':0}
out={}
for key,box in C.items():
 im=Image.open(O/'native'/f'{key}-000.png').convert('RGB');a=np.asarray(im.crop(box));out[key]={'roi':box,'fit':fit(a)}
(O/'psf-fits.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
