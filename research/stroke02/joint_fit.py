"""Profile-fit t and width per region using its own source ink direction."""
import json,pathlib,sys
import numpy as np
from scipy import ndimage as ndi,optimize,special
from skimage import morphology
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
L=np.array([.2126,.7152,.0722]); O=c.O; B=c.B

def profile_fit(residual,mask,sigma_grid,core_contrast,t_max):
 # Skeleton tangent provides cross sections without using OCR character labels.
 # Each profile has a local baseline, center and width; t is pooled.
 sk=morphology.skeletonize(mask); pts=np.argwhere(sk); chosen=[]
 for y,x in pts:
  neighbours=pts[np.sum((pts-[y,x])**2,axis=1)<=9]
  if len(neighbours)<3:continue
  cov=np.cov(neighbours.T);vals,vec=np.linalg.eigh(cov)
  if vals[-1]<.4 or vals[-1]<vals[0]*1.5:continue
  normal=vec[:,0];chosen.append((y,x,normal))
 if len(chosen)>12:
  chosen=[chosen[i] for i in np.linspace(0,len(chosen)-1,12,dtype=int)]
 sample=np.arange(-4,4.01,.5);profiles=[]
 for y,x,n in chosen:
  yy=y+sample*n[0];xx=x+sample*n[1]
  if yy.min()<0 or xx.min()<0 or yy.max()>=mask.shape[0]-1 or xx.max()>=mask.shape[1]-1:continue
  v=ndi.map_coordinates(residual,[yy,xx],order=1,mode='nearest')
  if v[len(v)//2] < max(v.max()*.55,.008):continue
  # A single-stroke box model is invalid if the line hits a neighbouring
  # stroke, a junction, or a counter edge. Require falling shoulders and one
  # central peak; retain the rejected count separately in later diagnostics.
  vv=ndi.gaussian_filter1d(v,.65);baseline=float(np.median(np.r_[vv[:3],vv[-3:]])); height=float(vv.max()-baseline)
  if height<.01 or int(np.argmax(vv)) not in range(5,12):continue
  if max(float(np.median(vv[:3])-baseline),float(np.median(vv[-3:])-baseline))>height*.35:continue
  peaks=np.where((vv[1:-1]>vv[:-2])&(vv[1:-1]>=vv[2:])&(vv[1:-1]>baseline+height*.45))[0]+1
  if len(peaks)!=1:continue
  profiles.append(v)
 if len(profiles)<2:return {'n_profiles':len(profiles),'grid':[]}
 profiles=np.array(profiles);peak=max(float(core_contrast),.005)
 # Pixel integration approximated with 3 subpixel samples per location.
 def shape(mu,width,sigma):
  q=sample[:,None]+np.array([-1/3,0,1/3]);return (special.ndtr((q-mu+width/2)/sigma)-special.ndtr((q-mu-width/2)/sigma)).mean(axis=1)
 # Diagnostic lower bound: give every cross-section its own amplitude. This
 # tests whether single-box geometry itself can fit without the shared-t rule.
 free=[]
 for sigma in sigma_grid:
  losses=[]
  for v in profiles:
   def fun_free(q):return q[2]+q[3]*shape(q[0],q[1],sigma)-v
   fit_free=optimize.least_squares(fun_free,[0,2,0,peak],bounds=([-1.5,.4,-peak*.4,0],[1.5,7.,peak*.4,1.]),max_nfev=45)
   losses.append(float(np.mean(fun_free(fit_free.x)**2)))
  free.append({'sigma':float(sigma),'rmse':float(np.sqrt(np.mean(losses)))})
 grid=[];prev=None
 for sigma in sigma_grid:
  for t in np.arange(1.,min(2.5,t_max)+.001,.05):
   fits=[]
   for v in profiles:
    def fun(q):return q[2]+(peak*t)*shape(q[0],q[1],sigma)-v
    result=optimize.least_squares(fun,[0,2,0],bounds=([-1.5,.4,-peak*.4],[1.5,7.,peak*.4]),max_nfev=35)
    fits.append((float(np.mean(fun(result.x)**2)),float(result.x[1]),float(result.x[0])))
   grid.append({'sigma':round(float(sigma),3),'t':round(float(t),2),'rmse':float(np.sqrt(np.mean([x[0] for x in fits]))),'median_width_px':float(np.median([x[1] for x in fits])),'width_mad_px':float(np.median(np.abs(np.array([x[1] for x in fits])-np.median([x[1] for x in fits]))))})
 return {'n_profiles':len(profiles),'core_contrast_linear':peak,'grid':grid,'free_amplitude':free}

def analyze(key):
 config=c.CASES[key];target=config['target'];bounds=config['context'];cx,cy,_,_=bounds;native=Image.open(O/'native'/f'{key}-000.png').convert('RGB');rgb=np.asarray(native.crop(bounds));z=c.st.reconstruction(rgb,237.8 if key=='8967062' else 204.3);obs=c.st.linear(rgb);bg=z['background'];residual=(bg-obs)@L
 # Ink direction from centre observations in the region, not another line.
 groups=c.get_groups(key,target);out=[]
 if key=='8967062':regions=groups;sigmas=[.3,.5,.7,.93,1.22]
 else:
  centres=np.array([(g[1]+g[3])/2 for g in groups]);pivot=float(np.median(centres));parts=[[g for g in groups if (g[1]+g[3])/2<=pivot],[g for g in groups if (g[1]+g[3])/2>pivot]];regions=[[min(g[0] for g in q),min(g[1] for g in q),max(g[2] for g in q),max(g[3] for g in q)] for q in parts if q];sigmas=[.3,.5,.7,.93,1.22]
 for a,b,d,e in regions:
  x0=max(0,a-cx-5);y0=max(0,b-cy-5);x1=min(rgb.shape[1],d-cx+5);y1=min(rgb.shape[0],e-cy+5);rr=residual[y0:y1,x0:x1];m=z['alpha'][y0:y1,x0:x1]>.28
  # Outside candidate glyph ink, local residual dispersion estimates texture,
  # noise, and model error together; it is not an independently measured sensor sigma.
  blank=rr[~ndi.binary_dilation(m,iterations=2)]; noise=float(max(.002,1.4826*np.median(np.abs(blank-np.median(blank))))) if len(blank)>10 else float('nan')
  vals=rr[m];q=float(np.quantile(vals,.85)) if len(vals) else 0.;core=m&(rr>=q);vec=np.median((bg-obs)[y0:y1,x0:x1][core],axis=0) if core.any() else np.zeros(3)
  paper=np.median(bg[y0:y1,x0:x1][core],axis=0) if core.any() else np.zeros(3);positive=vec>1e-6;t_max=float(min(2.5,np.min(paper[positive]/vec[positive]))) if positive.any() else 0.
  fit=profile_fit(rr,m,sigmas,float(vec@L),t_max);grid=fit['grid'];best=min(grid,key=lambda x:x['rmse']) if grid else None
  # Statistical tolerance includes estimated nuisance variation and finite profile
  # sampling; report the raw differences, rather than infer a calibrated posterior.
  # No acceptance threshold: observed-paper MAD is not an oracle residual.
  consistent=[]
  out.append({'bbox':[a,b,d,e],'noise_linear_mad':noise,'core_direction_linear':vec.tolist(),'core_pixels':int(core.sum()),'paper_linear':paper.tolist(),'t_max_physical':t_max,'profiles':fit['n_profiles'],'free_amplitude':fit.get('free_amplitude',[]),'best':best,'within_noise':consistent,'grid':grid})
 return out

def main():
 out={k:analyze(k) for k in c.CASES};(O/'joint-profiles.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:[{'bbox':r['bbox'],'noise':r['noise_linear_mad'],'profiles':r['profiles'],'best':r['best'],'within_noise':len(r['within_noise'])} for r in v] for k,v in out.items()},indent=2))
if __name__=='__main__':main()
