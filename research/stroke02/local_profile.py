"""Crop-equivalent, per-glyph profile fits on supplied native source pixels.

The OCR boxes delimit observations only; their text is never consulted.
"""
import numpy as np
from scipy import ndimage as ndi
import crop_fit as c
import joint_fit
L=np.array([.2126,.7152,.0722])

def fit_context(rgb, boxes, origin, return_model=False):
 z=c.st.reconstruction(rgb,0.0);obs=c.st.linear(rgb);bg=z['background'];residual=(bg-obs)@L;cx,cy=origin;out=[]
 for a,b,d,e in boxes:
  x0=max(0,a-cx-5);y0=max(0,b-cy-5);x1=min(rgb.shape[1],d-cx+5);y1=min(rgb.shape[0],e-cy+5)
  rr=residual[y0:y1,x0:x1];m=z['alpha'][y0:y1,x0:x1]>.28
  blank=rr[~ndi.binary_dilation(m,iterations=2)];noise=float(max(.002,1.4826*np.median(np.abs(blank-np.median(blank))))) if len(blank)>10 else float('nan')
  vals=rr[m];q=float(np.quantile(vals,.85)) if len(vals) else 0.;core=m&(rr>=q);vec=np.median((bg-obs)[y0:y1,x0:x1][core],axis=0) if core.any() else np.zeros(3)
  paper=np.median(bg[y0:y1,x0:x1][core],axis=0) if core.any() else np.zeros(3);pos=vec>1e-6;tmax=float(min(2.5,np.min(paper[pos]/vec[pos]))) if pos.any() else 0.
  fit=joint_fit.profile_fit(rr,m,[.3,.5,.7,.93,1.22],float(vec@L),tmax);best=min(fit['grid'],key=lambda x:x['rmse']) if fit['grid'] else None
  out.append({'bbox':[a,b,d,e],'noise_linear_mad':noise,'core_direction_linear':vec.tolist(),'core_pixels':int(core.sum()),'paper_linear':paper.tolist(),'t_max_physical':tmax,'profiles':fit['n_profiles'],'best':best})
 return (out, z, obs) if return_model else out


def fit_line(rgb, boxes, bound):
 """Fit each glyph with a shared local context, without consulting its label."""
 left,top,right,bottom=bound;pad=max(12,int(round(2.3*(bottom-top))))
 height,width=rgb.shape[:2];x0=max(0,left-pad);y0=max(0,top-pad);x1=min(width,right+pad);y1=min(height,bottom+pad)
 result,model,obs=fit_context(rgb[y0:y1,x0:x1],boxes,(x0,y0),return_model=True)
 return result,model,obs,(x0,y0,x1,y1)
