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
 # grid_mode=True maps upsampled pixel centres to PDF pixel edges.
 points=(np.column_stack([ring[:,1],ring[:,0]])+.5)/4
 if np.linalg.norm(points[0]-points[-1])<.5:points=points[:-1]
 if len(points)<8:return False
 # Remove consecutive duplicates; periodic smoothing has no OCR shape template.
 diff=np.linalg.norm(np.diff(points,axis=0),axis=1);points=points[np.r_[True,diff>1e-5]]
 if len(points)<8:return False
 # Tiny counters must not be collapsed by the outer-contour smoothing.
 span=np.ptp(points,axis=0);smooth=0 if min(span)<4 else len(points)*.025
 try:tck,_=interpolate.splprep([points[:,0],points[:,1]],s=smooth,per=True,k=3)
 except (ValueError,TypeError):return False
 n=max(8,min(80,int(len(points)/3)));t=np.linspace(0,1,n+1);xy=np.array(interpolate.splev(t,tck)).T;der=np.array(interpolate.splev(t,tck,der=1)).T
 for i in range(n):
  p0=xy[i];p3=xy[i+1];dt=t[i+1]-t[i];p1=p0+der[i]*dt/3;p2=p3-der[i+1]*dt/3
  def pt(v):return fitz.Point((v[0]+origin[0])*scale,(v[1]+origin[1])*scale)
  shape.draw_bezier(pt(p0),pt(p1),pt(p2),pt(p3))
 return True

def generate(key,sigma,style):
 config=c.CASES[key];target=config['target'];bounds=config['context'];cx,cy,_,_=bounds;x0,y0,x1,y1=target;native=Image.open(O/'native'/f'{key}-000.png').convert('RGB');rgb=np.asarray(native.crop(bounds));obs=c.st.linear(rgb);z=c.st.reconstruction(rgb,237.8 if key=='8967062' else 204.3);bg=z['background'];run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dpi=run['dpi'];regions=DATA[key];groups=c.get_groups(key,target)
 base=obs.copy(); jobs=[]; all_masks=[];fallback=[]
 weights=np.array([r['core_pixels'] for r in regions],float);line_direction=np.average(np.array([r['core_direction_linear'] for r in regions]),axis=0,weights=weights);line_t=float(np.median([r['best']['t'] for r in regions if r['best']]))
 for idx,r in enumerate(regions):
  a,b,d,e=r['bbox']; grid=[v for v in r['grid'] if abs(v['sigma']-sigma)<.001]
  if not grid:continue
  # Choose profile fit per sigma; mass minimization is performed only after
  # forward and topology checks, never by OCR character identity.
  pick=min(grid,key=lambda x:(x['rmse'],x['width_mad_px']));t=pick['t'];direction=np.array(r['core_direction_linear']);
  if style=='r3' and key=='8967062': direction=line_direction;t=line_t
  denom=max(float(direction@direction),1e-8);relative=np.clip(((bg-obs)*direction).sum(-1)/(t*denom),0,1)
  # Region padding supplies blur support; output stays inside its source region.
  xa=max(0,a-cx-4);xb=min(rgb.shape[1],d-cx+4);ya=max(0,b-cy-4);yb=min(rgb.shape[0],e-cy+4);sub=relative[ya:yb,xa:xb];latent=c.bounded_inverse(sub,sigma,30)
  # Clip to the group, plus one source pixel for edge evidence.
  allowed=np.zeros_like(latent,bool); xlo=max(0,a-cx-xa-1);xhi=min(latent.shape[1],d-cx-xa+1);ylo=max(0,b-cy-ya-1);yhi=min(latent.shape[0],e-cy-ya+1);allowed[ylo:yhi,xlo:xhi]=True;latent*=allowed
  # The counter-favoured alternative uses a lower local isocontour only for
  # the empirically located counter region; its actual rescan must still pass.
  threshold=({'counter':.25,'counter35':.35,'counter40':.40}.get(style,.5) if key=='8967062' and idx==0 and COUNTER['decision']=='counter' else .5)
  if style=='holelayers' and key=='8967062' and idx==0:
   # Preserve the observed counter hypothesis in every tonal layer.
   for hx,hy in COUNTER['hole_pixel_coords_source']:
    xx=hx-(cx+xa);yy=hy-(cy+ya)
    if 0<=yy<latent.shape[0] and 0<=xx<latent.shape[1]:latent[yy,xx]=0
  # Find source-paper pixels enclosed by observed ink; they are vetoed in every layer.
  local_res=((bg[ya:yb,xa:xb]-obs[ya:yb,xa:xb])@np.array([.2126,.7152,.0722]));veto=np.zeros_like(latent,bool)
  if style=='r3':
   observed_ink=local_res>max(.02,float(direction@np.array([.2126,.7152,.0722]))*.25)
   enclosed=ndi.binary_fill_holes(observed_ink,structure=np.ones((3,3)))&~observed_ink
   veto=enclosed&(local_res<=2*r['noise_linear_mad']);latent[veto]=0
   # Until a post-PDF forward check is established, counter-bearing groups
   # are kept wholly raster, including their background pixels.
   if veto.any():
    fallback.append({'bbox':r['bbox'],'reason':'enclosed paper protection','veto_pixels':int(veto.sum())});continue
  binary=latent>=threshold
  relevant=groups
  eligible,forbidden,small,cross=c.protected_components(binary,relevant,cx+xa,cy+ya);support=ndi.binary_dilation(eligible,iterations=3)&allowed&~forbidden;latent*=ndi.binary_dilation(eligible,iterations=2)&~forbidden
  ky=slice(ya,yb);kx=slice(xa,xb);paper=np.median(bg[ky,kx][support],axis=0) if support.any() else np.median(bg[ky,kx].reshape(-1,3),axis=0);ink=np.clip(paper-t*direction,0,1);base_sub=base[ky,kx]
  if style=='r3':
   # A tapered, ink-derived footprint avoids hard support-box boundaries.
   footprint=ndi.gaussian_filter((latent>.05).astype(float),max(.4,sigma));blend=np.clip(footprint*1.5,0,1);base_sub[:]=base_sub*(1-blend[...,None])+bg[ky,kx]*blend[...,None]
  else:base_sub[support]=bg[ky,kx][support]
  # Bicubic 4x coverage, marching squares and fitted cubic Beziers.
  up=np.clip(ndi.zoom(latent,4,order=3,grid_mode=True,mode='grid-constant'),0,1);bm=up>=threshold;_,cc=ndi.label(bm,np.ones((3,3)));_,holes=ndi.label(ndi.binary_fill_holes(bm)&~bm);sk=morphology.skeletonize(bm);nb=ndi.convolve(sk.astype(int),np.ones((3,3),int));width=2*ndi.distance_transform_edt(bm)[sk]/4
  globalmask=np.zeros(rgb.shape[:2],bool);globalmask[ya:yb,xa:xb]=latent>=threshold
  jobs.append({'_global':globalmask,'join':False,'style':style,'threshold':threshold,'idx':idx,'bbox':r['bbox'],'t':t,'sigma':sigma,'noise':r['noise_linear_mad'],'direction':direction,'paper':paper,'ink':ink,'latent':latent,'up':up,'origin':(xa+cx-x0,ya+cy-y0),'small':small,'cross':cross,'components':int(cc),'holes':int(holes),'terminals':int((sk&(nb==2)).sum()),'width_median':float(np.median(width)) if len(width) else None,'width_mad':float(np.median(np.abs(width-np.median(width)))) if len(width) else None,'mass_px':float(np.sum(up)/16),'mask':bm,'veto':veto,'base_slice':(xa,ya,xb,yb)})
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
  levels=[(.20,.20),(.40,.25),(.60,1/3),(.80,.5)] if style in ('layers','holelayers','r3') else [(job['threshold'],1.)]
  for level,opacity in levels:
   shape=page.new_shape();count=0
   layer=job['up'].copy(); contour_level=level
   if style=='r3':
    veto4=ndi.zoom(job['veto'].astype(np.uint8),4,order=0,grid_mode=True,mode='grid-constant')>0
    mask=layer>=level;mask[veto4]=False
    # Split the local noise allowance evenly between the four layers. A layer
    # that cannot meet it is removed; no unsupported counter ink is painted.
    contrast=float((job['direction']*job['t'])@np.array([.2126,.7152,.0722]))
    if veto4.any():
     for radius in range(0,16):
      candidate=mask&~ndi.binary_dilation(veto4,iterations=radius) if radius else mask
      predicted=ndi.gaussian_filter(candidate.astype(float),4*job['sigma'])*opacity*contrast
      if float(predicted[veto4].max())<=job['noise']/len(levels):break
     else:candidate=np.zeros_like(mask)
     mask=candidate
    layer=mask.astype(float);contour_level=.5
   for ring in measure.find_contours(np.pad(layer,1),contour_level):
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
  a,b,d,e=job['bbox'];xx=slice(max(0,a-x0),min(ww,d-x0));yy=slice(max(0,b-y0),min(hh,e-y0));direction=job['direction'];t=job['t'];di=direction*t;denom=max(float(di@di),1e-8);coverage=np.clip(((Btarget-rendered)*di).sum(-1)/denom,0,1);prediction=Btarget-di*ndi.gaussian_filter(coverage,sigma)[...,None];err=((prediction-Itarget)@np.array([.2126,.7152,.0722]))[yy,xx];job['pdf_rescan_luma_rmse']=float(np.sqrt(np.mean(err**2)));job['ink_srgb']=c.st.srgb(job['ink']).tolist()
  cov4=np.clip(((paper4-actual4)*di).sum(-1)/denom,0,1);y4=slice(max(0,b-y0)*4,min(hh,e-y0)*4);x4=slice(max(0,a-x0)*4,min(ww,d-x0)*4);region_cov=cov4[y4,x4];job['pdf_mass_px']=float(region_cov.sum()/16);mask4=region_cov>=.5;_,n4=ndi.label(mask4,np.ones((3,3)));_,h4=ndi.label(ndi.binary_fill_holes(mask4)&~mask4);job['pdf_components']=int(n4);job['pdf_holes']=int(h4);job['pdf_layer_topology']={}
  for level in [.2,.4,.6,.8]:
   mask=region_cov>=level;_,num=ndi.label(mask,np.ones((3,3)));_,holes=ndi.label(ndi.binary_fill_holes(mask)&~mask);job['pdf_layer_topology'][str(level)]=[int(num),int(holes)]
 for job in jobs:
  for k in ['direction','paper','ink','latent','up','mask','veto','_global']:job.pop(k)
 return {'pdf':str(path),'groups':jobs,'fallback':fallback}

def main():
 # Candidate creation only. The old within-MAD gate was invalid and is not
 # used for acceptance; fair_compare compares all PDFs with the same blur fit.
 all_results={}
 for key in c.CASES:
  sigmas=[.3,.5,.7,.93,1.22]
  all_results[key]=[generate(key,s,style) for style in (['solid','layers','counter','counter35','counter40','holelayers','r3'] if key=='8967062' else ['solid','layers']) for s in sigmas]
  print(key, len(all_results[key]), 'candidate PDFs', flush=True)
 out={'runs':all_results,'noise_note':'legacy rescan score is diagnostic only, not an acceptance test; use oracle-calibration and fair-compare'}
 (O/'joint-render.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
