"""Compare counter vs filled-counter forward predictions inside observed hole."""
import json,pathlib,sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B=c.B;O=c.O;L=np.array([.2126,.7152,.0722]);p=json.loads((O/'joint-profiles.json').read_text())['8967062'][0];config=c.CASES['8967062'];cx,cy,_,_=config['context'];a,b,d,e=p['bbox'];im=Image.open(O/'native/8967062-000.png').convert('RGB');rgb=np.asarray(im.crop(config['context']));obs=c.st.linear(rgb);z=c.st.reconstruction(rgb,237.8);alpha=z['alpha'];seed=alpha[b-cy:e-cy,a-cx:d-cx]>=.25;holes=ndi.binary_fill_holes(seed)&~seed; labels,n=ndi.label(holes)
if n:
 counts=np.bincount(labels.ravel());counts[0]=0;hole=labels==np.argmax(counts)
else:hole=np.zeros(seed.shape,bool)
region=np.zeros(alpha.shape,bool);region[b-cy:e-cy,a-cx:d-cx]=hole
# Both hypotheses have identical coverage everywhere outside this observed
# candidate counter; filling changes only this region before simulated blur.
observed=((z['background']-obs)@L);direction=float(np.array(p['core_direction_linear'])@L);noise=p['noise_linear_mad'];rows=[]
for sigma in [.93,1.1,1.22,1.35,1.48]:
 for t in np.arange(1.,min(2.5,p['t_max_physical'])+.001,.05):
  relative=np.clip(observed/max(direction*t,1e-8),0,1); latent=c.bounded_inverse(relative,sigma,30)
  with_hole=latent.copy(); without=latent.copy(); with_hole[region]=0; without[region]=np.maximum(without[region],.5)
  w=direction*t*ndi.gaussian_filter(with_hole,sigma);f=direction*t*ndi.gaussian_filter(without,sigma)
  er1=float(np.sqrt(np.mean((w[region]-observed[region])**2))) if region.any() else None;er2=float(np.sqrt(np.mean((f[region]-observed[region])**2))) if region.any() else None
  rows.append({'sigma':sigma,'t':round(float(t),2),'with_counter_rmse':er1,'filled_rmse':er2,'difference_filled_minus_counter':er2-er1 if er1 is not None else None})
# A directional result is called decisive here only if every physically valid
# grid point prefers the same model by > 2 measured local-noise RMS. This is a
# conservative sensitivity test, not a formal calibrated likelihood ratio.
deltas=[r['difference_filled_minus_counter'] for r in rows if r['difference_filled_minus_counter'] is not None];decisive='counter' if deltas and min(deltas)>2*noise else 'filled' if deltas and max(deltas)<-2*noise else 'ambiguous'
out={'region_bbox':p['bbox'],'hole_pixels':int(region.sum()),'hole_pixel_coords_source':[[int(x+cx),int(y+cy)] for y,x in np.argwhere(region)],'local_noise_linear_mad':noise,'t_max_physical':p['t_max_physical'],'rule':'same direction at every tested sigma/t and RMSE advantage >2x local noise','decision':decisive,'delta_range':[min(deltas),max(deltas)] if deltas else None,'rows':rows}
(O/'counter-test.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
