"""Diagnostic per-region ink/width fit rendered as subpixel cubic PDF paths."""
import io,json,pathlib,sys
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi,interpolate
from skimage import measure,morphology
import fitz,pypdfium2 as pdfium
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B=c.B;O=c.O;DATA=json.loads((O/'joint-profiles.json').read_text());COUNTER=json.loads((O/'counter-test.json').read_text())

def cubic_ring(shape,ring,origin,scale):
 """Fit a closed cubic curve to 4x marching-squares data, preserve frame."""
 if len(ring)<9:return False
 points=np.column_stack([ring[:,1],ring[:,0]])/4-.375
 if np.linalg.norm(points[0]-points[-1])<.5:points=points[:-1]
 if len(points)<8:return False
 # Remove consecutive duplicates; periodic smoothing has no OCR shape template.
 diff=np.linalg.norm(np.diff(points,axis=0),axis=1);points=points[np.r_[True,diff>1e-5]]
 if len(points)<8:return False
 try:tck,_=interpolate.splprep([points[:,0],points[:,1]],s=len(points)*.025,per=True,k=3)
 except (ValueError,TypeError):return False
 n=max(8,min(80,int(len(points)/3)));t=np.linspace(0,1,n+1);xy=np.array(interpolate.splev(t,tck)).T;der=np.array(interpolate.splev(t,tck,der=1)).T
 for i in range(n):
  p0=xy[i];p3=xy[i+1];dt=t[i+1]-t[i];p1=p0+der[i]*dt/3;p2=p3-der[i+1]*dt/3
  def pt(v):return fitz.Point((v[0]+origin[0])*scale,(v[1]+origin[1])*scale)
  shape.draw_bezier(pt(p0),pt(p1),pt(p2),pt(p3))
 return True

def generate(key,sigma,style):
 config=c.CASES[key];target=config['target'];bounds=config['context'];cx,cy,_,_=bounds;x0,y0,x1,y1=target;native=Image.open(O/'native'/f'{key}-000.png').convert('RGB');rgb=np.asarray(native.crop(bounds));obs=c.st.linear(rgb);z=c.st.reconstruction(rgb,237.8 if key=='8967062' else 204.3);bg=z['background'];run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dpi=run['dpi'];regions=DATA[key];groups=c.get_groups(key,target)
 base=obs.copy(); jobs=[]; all_masks=[]
 for idx,r in enumerate(regions):
  a,b,d,e=r['bbox']; grid=[v for v in r['grid'] if abs(v['sigma']-sigma)<.001]
  if not grid:continue
  # Choose profile fit per sigma; mass minimization is performed only after
  # forward and topology checks, never by OCR character identity.
  pick=min(grid,key=lambda x:(x['rmse'],x['width_mad_px']));t=pick['t'];direction=np.array(r['core_direction_linear']); denom=max(float(direction@direction),1e-8);relative=np.clip(((bg-obs)*direction).sum(-1)/(t*denom),0,1)
  # Region padding supplies blur support; output stays inside its source region.
  xa=max(0,a-cx-4);xb=min(rgb.shape[1],d-cx+4);ya=max(0,b-cy-4);yb=min(rgb.shape[0],e-cy+4);sub=relative[ya:yb,xa:xb];latent=c.bounded_inverse(sub,sigma,30)
  # Clip to the group, plus one source pixel for edge evidence.
  allowed=np.zeros_like(latent,bool); xlo=max(0,a-cx-xa-1);xhi=min(latent.shape[1],d-cx-xa+1);ylo=max(0,b-cy-ya-1);yhi=min(latent.shape[0],e-cy-ya+1);allowed[ylo:yhi,xlo:xhi]=True;latent*=allowed
  # The counter-favoured alternative uses a lower local isocontour only for
  # the empirically located counter region; its actual rescan must still pass.
  threshold=.25 if style=='counter' and key=='8967062' and idx==0 and COUNTER['decision']=='counter' else .5
  binary=latent>=threshold
  relevant=groups
  eligible,forbidden,small,cross=c.protected_components(binary,relevant,cx+xa,cy+ya);support=ndi.binary_dilation(eligible,iterations=3)&allowed&~forbidden;latent*=ndi.binary_dilation(eligible,iterations=2)&~forbidden
  ky=slice(ya,yb);kx=slice(xa,xb);paper=np.median(bg[ky,kx][support],axis=0) if support.any() else np.median(bg[ky,kx].reshape(-1,3),axis=0);ink=np.clip(paper-t*direction,0,1);base_sub=base[ky,kx];base_sub[support]=bg[ky,kx][support]
  # Bicubic 4x coverage, marching squares and fitted cubic Beziers.
  up=np.clip(ndi.zoom(latent,4,order=3),0,1);bm=up>=threshold;_,cc=ndi.label(bm,np.ones((3,3)));_,holes=ndi.label(ndi.binary_fill_holes(bm)&~bm);sk=morphology.skeletonize(bm);nb=ndi.convolve(sk.astype(int),np.ones((3,3),int));width=2*ndi.distance_transform_edt(bm)[sk]/4
  globalmask=np.zeros(rgb.shape[:2],bool);globalmask[ya:yb,xa:xb]=latent>=threshold
  jobs.append({'_global':globalmask,'join':False,'style':style,'threshold':threshold,'idx':idx,'bbox':r['bbox'],'t':t,'sigma':sigma,'noise':r['noise_linear_mad'],'direction':direction,'paper':paper,'ink':ink,'latent':latent,'up':up,'origin':(xa+cx-x0,ya+cy-y0),'small':small,'cross':cross,'components':int(cc),'holes':int(holes),'terminals':int((sk&(nb==2)).sum()),'width_median':float(np.median(width)) if len(width) else None,'width_mad':float(np.median(np.abs(width-np.median(width)))) if len(width) else None,'mass_px':float(np.sum(up)/16),'mask':bm,'base_slice':(xa,ya,xb,yb)})
 # Any proposed contact between independently grouped glyphs is rejected.
 # This does not infer a shape from the OCR label or force a join.
 if key=='8967062':
  for i,left in enumerate(jobs):
   for right in jobs[i+1:]:
    if np.any(ndi.binary_dilation(left['_global'],iterations=1)&right['_global']):left['join']=True;right['join']=True
 # The PDF embeds a source crop for a truthful local visual diagnostic; it is
 # not a ScanWeave PDF and intentionally has no OCR layer.
 doc=fitz.open();page=doc.new_page(width=(x1-x0)*72/dpi,height=(y1-y0)*72/dpi);buf=io.BytesIO();Image.fromarray(c.st.srgb(base)[y0-cy:y1-cy,x0-cx:x1-cx]).save(buf,format='PNG');page.insert_image(page.rect,stream=buf.getvalue())
 for job in jobs:
  levels=[(.20,.20),(.40,.25),(.60,1/3),(.80,.5)] if style=='layers' else [(job['threshold'],1.)]
  for level,opacity in levels:
   shape=page.new_shape();count=0
   for ring in measure.find_contours(np.pad(job['up'],1),level):
    ring=ring-1
    if cubic_ring(shape,ring,job['origin'],72/dpi):count+=1
   if count:
    color=c.st.srgb(job['ink'])/255;shape.finish(color=None,fill=tuple(map(float,color)),fill_opacity=opacity,even_odd=True,closePath=True);shape.commit()
 path=O/'crops'/f'{key}-joint-{style}-{sigma:.2f}.pdf';doc.save(path,deflate=True,garbage=4)
 # Re-read the actual antialiased PDF and independently simulate a scan. Error
 # is in linear luminance inside each OCR/group box; noise is local background
 # MAD and includes its known limitations. PDF pixels outside rewritten regions
 # may be reblurred and this makes the test conservative around edges.
 rendered=np.asarray(pdfium.PdfDocument(str(path))[0].render(scale=dpi*2/72).to_pil().convert('RGB'));hh=y1-y0;ww=x1-x0;rendered=c.st.linear(rendered[:hh*2,:ww*2]).reshape(hh,2,ww,2,3).mean((1,3));Btarget=bg[y0-cy:y1-cy,x0-cx:x1-cx];Itarget=obs[y0-cy:y1-cy,x0-cx:x1-cx]
 # Topology is measured on the actual PDF paths at 4x, not on a pre-fit mask.
 # The 4x render is diagnostic only; visual comparisons remain 1x and 2x.
 actual4=np.asarray(pdfium.PdfDocument(str(path))[0].render(scale=dpi*4/72).to_pil().convert('RGB'))[:hh*4,:ww*4];actual4=c.st.linear(actual4);paper4=ndi.zoom(Btarget,(4,4,1),order=1)[:hh*4,:ww*4]
 for job in jobs:
  a,b,d,e=job['bbox'];xx=slice(max(0,a-x0),min(ww,d-x0));yy=slice(max(0,b-y0),min(hh,e-y0));direction=job['direction'];t=job['t'];di=direction*t;denom=max(float(di@di),1e-8);coverage=np.clip(((Btarget-rendered)*di).sum(-1)/denom,0,1);prediction=Btarget-di*ndi.gaussian_filter(coverage,sigma)[...,None];err=((prediction-Itarget)@np.array([.2126,.7152,.0722]))[yy,xx];job['pdf_rescan_luma_rmse']=float(np.sqrt(np.mean(err**2)));job['within_noise']=job['pdf_rescan_luma_rmse']<=job['noise'];job['ink_srgb']=c.st.srgb(job['ink']).tolist()
  cov4=np.clip(((paper4-actual4)*di).sum(-1)/denom,0,1);y4=slice(max(0,b-y0)*4,min(hh,e-y0)*4);x4=slice(max(0,a-x0)*4,min(ww,d-x0)*4);region_cov=cov4[y4,x4];job['pdf_mass_px']=float(region_cov.sum()/16);mask4=region_cov>=.5;_,n4=ndi.label(mask4,np.ones((3,3)));_,h4=ndi.label(ndi.binary_fill_holes(mask4)&~mask4);job['pdf_components']=int(n4);job['pdf_holes']=int(h4)
 for job in jobs:
  for k in ['direction','paper','ink','latent','up','mask','_global']:job.pop(k)
 return {'pdf':str(path),'groups':jobs}

def main():
 all_results={}; finals={}
 for key in c.CASES:
  sigmas=[.93,1.1,1.22,1.35,1.48] if key=='8967062' else [.65,.8,.93,1.06,1.18]; runs=[generate(key,s,style) for style in (['solid','layers','counter'] if key=='8967062' else ['solid','layers']) for s in sigmas];all_results[key]=runs; decisions=[]
  for idx,reg in enumerate(DATA[key]):
   consistent=[];by_style={}
   for style in (['solid','layers','counter'] if key=='8967062' else ['solid','layers']):
    available=[j for run in runs for j in run['groups'] if j['idx']==idx and j['style']==style];signatures={(x['pdf_components'],x['pdf_holes']) for x in available};stable=len(available)==len(sigmas) and len(signatures)==1
    passing=[x for x in available if x['within_noise'] and stable and not x['join'] and x['cross']==0 and (key!='8967062' or idx!=0 or COUNTER['decision']!='counter' or x['pdf_holes']>=1)]
    consistent.extend(passing);by_style[style]={'topology_stable':stable,'topology_signatures':[list(x) for x in sorted(signatures)],'passing':len(passing)}
   best=min(consistent,key=lambda x:(x['pdf_mass_px'],x['width_mad'] if x['width_mad'] is not None else float('inf'))) if consistent else None
   decisions.append({'bbox':reg['bbox'],'sigma_grid':sigmas,'by_style':by_style,'counter_evidence':COUNTER['decision'] if key=='8967062' and idx==0 else None,'consistent_set_size':len(consistent),'selected_sigma':best['sigma'] if best else None,'selected_style':best['style'] if best else None,'decision':'vector' if best else 'raster'})
  finals[key]=decisions
  print(key,json.dumps(decisions),flush=True)
 out={'runs':all_results,'decisions':finals,'noise_note':'local paper residual MAD; not independently measured sensor noise; PDF raster fallback near boundaries may be reblurred','policy':'within noise + same component/hole counts over full measured sigma grid + no cross-group component + counter test; minimum mass among passing'}
 (O/'joint-render.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
