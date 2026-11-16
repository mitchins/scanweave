#!/usr/bin/env python3
"""STROKE-01 crop-only, CPU research prototype; never used by the converter."""
from __future__ import annotations
import hashlib, io, json, os, pathlib, platform, time, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import local_model
import calibration
import numpy as np
from scipy import ndimage as ndi, optimize
from skimage import morphology, measure
from skimage.color import rgb2lab, deltaE_ciede2000
from PIL import Image, ImageDraw, ImageFont
import scipy, skimage, PIL

B = pathlib.Path('/data/coding/scanweave/work/books01')
OUT = B / 'stroke01' / 'corrected'
NATIVE = B / 'stroke01' / 'native'
R = B / 'phase2' / 'renders'
CASES = {
 '8967062': ((1165,748,1236,791), 'engraved'),
 '8967228': ((1942,148,2309,205), 'engraved'),
 '12342014': ((84,360,611,442), 'serif'),
 'euler_rechenkunst01_1738_0025': ((0,500,500,570), 'fraktur'),
 'luther_babstum_1526_0011': ((400,1700,900,1770), 'fraktur'),
}
FONTS = ['/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf']

def linear(x):
 x=np.asarray(x,dtype=float)/255
 return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):
 x=np.clip(x,0,1); return np.uint8(np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)*255+.5,0,255))
def rgb_luma(x): return x @ np.array([.2126,.7152,.0722])
def topology(m):
 labels,n=ndi.label(m,structure=np.ones((3,3))); holes=ndi.binary_fill_holes(m)&~m; _,h=ndi.label(holes)
 return {'components':int(n),'holes':int(h),'euler':int(n-h)}
def forward(mask,b,k,sigma):
 a=ndi.gaussian_filter(mask.astype(float),sigma,mode='nearest');return np.clip(b*(1-a[...,None])+k*a[...,None],0,1)
def reconstruction(rgb, baseline_paper):
 """Robust local histogram, edge-weighted binary energy, skeleton-width fit."""
 obs=linear(rgb); lum=rgb_luma(obs); h,w=lum.shape
 # Upper local percentile estimates illuminated paper. Context is supplied by crop;
 # no claim of page/border classification is made by this experiment.
 radius=max(9,min(51,(min(h,w)//3)|1))
 small=obs[::4,::4]; window=max(3,(radius//4)|1); bg=np.stack([ndi.zoom(ndi.gaussian_filter(ndi.percentile_filter(small[...,c],80,size=window,mode='nearest'),max(1,window/6)),(h/small.shape[0],w/small.shape[1]),order=1)[:h,:w] for c in range(3)],axis=-1)
 model=local_model.estimate(obs,bg); ink=model['ink']; alpha=model['alpha'];core=model['core'];contrast=model['contrast'];noise=model['noise'];uncertainty=model['uncertainty']
 # These features are calibrated on the synthetic training fonts after this run.
 confidence=float(contrast/max(noise,.002)); decline=bool(contrast<max(.05,6*noise) or not model['components'])
 prob=np.clip(alpha,0,1)
 m1=alpha>=.5
 # Binary pairwise Potts energy, optimized by iterated conditional modes. It is
 # inspired by edge-aware objectives, not Howe's exact Laplacian/graph cut.
 grad=np.hypot(ndi.sobel(lum,axis=0),ndi.sobel(lum,axis=1))/8
 unary=np.clip((alpha-.42)*2,-1,1);edge=np.exp(-grad/.035); m2=m1.copy()
 for _ in range(12):
  padded=np.pad(m2.astype(float),1); neighbours=padded[:-2,1:-1]+padded[2:,1:-1]+padded[1:-1,:-2]+padded[1:-1,2:]; cost=unary+.16*edge*(neighbours-2); new=cost>0
  new &= model['support']
  if np.array_equal(new,m2):break
  m2=new
 # Use the observed skeleton as the geometric seed; optimize a common scale applied
 # to per-skeleton local widths, using a Gaussian forward scan and an unsupported
 # ink penalty. Width expansion can still bridge components; no topology guarantee.
 skeleton=morphology.skeletonize(m2);dist=ndi.distance_transform_edt(m2)
 if skeleton.any():
  d,idx=ndi.distance_transform_edt(~skeleton,return_indices=True); radii=dist[tuple(idx)]
  def objective(v):
   radius_scale,sigma=v;coverage=np.clip((radii*radius_scale+.5-d),0,1);pred=forward(coverage,bg,ink,sigma)
   fit=np.mean(np.minimum((pred-obs)**2,.01));unsupported=np.mean(coverage*np.maximum(0,.15-alpha));return fit+.012*unsupported+.0001*(radius_scale-1)**2
  result=optimize.minimize(objective,[1.,.8],method='L-BFGS-B',bounds=[(.65,1.25),(.35,2.)],options={'maxiter':35,'ftol':1e-8}); scale,sigma=map(float,result.x)
  a3=np.clip(radii*scale+.5-d,0,1);m3=a3>=.5
 else: scale,sigma=1.,.8;a3=np.zeros_like(alpha);m3=m2.copy()
 # Report fits for all methods under the same fitted scanner sigma.
 baseline=np.abs(rgb_luma(rgb.astype(float))-baseline_paper)>60
 pred=[forward(a,bg,ink,sigma) for a in (baseline.astype(float),alpha,m2.astype(float),a3)]
 fit=[float(np.sqrt(np.mean((z-obs)**2))) for z in pred]
 return {'alpha':alpha,'probability':prob,'masks':[baseline,m1,m2,m3], 'background':bg,'ink':ink,'pred':pred,'confidence':confidence,'decline':decline,'contrast':contrast,'noise':noise,'sigma':sigma,'width_scale':scale,'fit':fit,'skeleton':skeleton,'core':core,'background_rgb':srgb(np.median(bg.reshape(-1,3),axis=0)).tolist(),'ink_rgb':srgb(np.median(ink[model['eligible']],axis=0) if model['eligible'].any() else np.median(ink.reshape(-1,3),axis=0)).tolist(),'uncertainty':uncertainty,'components':model['components'],'support':model['support'],'labels':model['labels'],'proposed':model['proposed']}

def scores(gt,pred):
 gt=gt.astype(bool);pred=pred.astype(bool);ge=gt^ndi.binary_erosion(gt);pe=pred^ndi.binary_erosion(pred);near_gt=ndi.binary_dilation(ge,iterations=1);near_pred=ndi.binary_dilation(pe,iterations=1)
 precision=(pe&near_gt).sum()/max(pe.sum(),1);recall=(ge&near_pred).sum()/max(ge.sum(),1);f=2*precision*recall/max(precision+recall,1e-9)
 gtlabels,gn=ndi.label(gt,structure=np.ones((3,3)));plabels,pn=ndi.label(pred,structure=np.ones((3,3)));joins=0
 for i in range(1,pn+1):
  labs=np.unique(gtlabels[plabels==i]); joins+=max(0,int((labs>0).sum())-1)
 return {'boundary_f1':float(f),'missing_fraction':float((gt&~pred).sum()/max(gt.sum(),1)), 'false_ink_fraction':float((pred&~gt).sum()/max(gt.sum(),1)), 'gt_topology':topology(gt),'topology':topology(pred),'false_joins':int(joins)}

def synthetic():
 out=[];rng=np.random.default_rng(20261116);rng2=np.random.default_rng(20261117)
 for fontpath in FONTS:
  for glyph in ['6','1','3','e','a','f','rn']:
   for mode in ['clear','faded','broken','no_evidence','two_inks']:
    dpi=500 if mode in ('faded','no_evidence') else 300
    fontsize=60 if dpi==500 else 42; size=(fontsize*(4 if mode=='two_inks' else 3),fontsize*2)
    font=ImageFont.truetype(fontpath,fontsize*4);canvas=Image.new('L',(size[0]*4,size[1]*4),0);ImageDraw.Draw(canvas).text((fontsize*2,fontsize*2),glyph,font=font,fill=255,stroke_width=0)
    clean=np.asarray(canvas.resize(size,Image.Resampling.LANCZOS),dtype=float)/255;gt=clean>=.5
    h,w=clean.shape;yy,xx=np.indices((h,w));paper=.79+.035*xx/w+.018*np.sin(yy/17)+.03*np.exp(-((xx-w*.7)**2+(yy-h*.4)**2)/(w*h*.15));bg=np.stack([paper*1.04,paper,paper*.91],-1).clip(0,1);k=np.array([.085,.08,.073]);alpha=clean.copy()
    if mode=='faded':alpha*=.35
    if mode=='broken':
     ys,xs=np.where(gt); cut=int((xs.min()+xs.max())/2); alpha[:,cut:cut+3]*=.04
    if mode=='no_evidence':alpha*=.015
    observed=forward(alpha,bg,k,1.15 if dpi==500 else .8); blob=np.zeros_like(clean,dtype=bool)
    if mode=='two_inks':
     blob=((xx-w*.82)/(.17*w))**2+((yy-h*.50)/(.36*h))**2<1;ba=ndi.gaussian_filter(blob.astype(float),.8);brown=np.array([.32,.14,.045]);observed=observed*(1-ba[...,None])+brown*ba[...,None]
    observed=np.clip(observed+(rng2 if mode=='two_inks' else rng).normal(0,.007,observed.shape),0,1);buf=io.BytesIO();Image.fromarray(srgb(observed)).save(buf,format='JPEG',quality=78,subsampling=2);rgb=np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert('RGB'))
    corners=[np.median(q.reshape(-1,3),axis=0) for q in [rgb[:6,:6],rgb[:6,-6:],rgb[-6:,:6],rgb[-6:,-6:]]]; estimated=float(rgb_luma(np.sort(np.array(corners),axis=0)[2]));z=reconstruction(rgb,estimated)
    if fontpath==FONTS[0] and glyph in ('6','rn'):
     pieces=[Image.fromarray(srgb(bg*(1-clean[...,None])+k*clean[...,None])),Image.fromarray(rgb)]+[Image.fromarray(np.uint8((~m)*255)).convert('RGB') for m in z['masks']]; board=Image.new('RGB',(size[0]*3,(size[1]+16)*2),'white'); labels=['clean GT','observed','baseline mask','local mask','energy mask','geometry mask']; draw=ImageDraw.Draw(board)
     for ix,piece in enumerate(pieces):
      pos=((ix%3)*size[0],(ix//3)*(size[1]+16)); draw.text(pos,labels[ix],fill='black'); board.paste(piece,(pos[0],pos[1]+16))
     board.save(OUT/'panels'/f'synthetic-{glyph}-{mode}.png')
    region=(xx<int(w*.62)) if mode=='two_inks' else np.ones_like(gt,dtype=bool)
    out.append({'font':pathlib.Path(fontpath).name,'glyph':glyph,'mode':mode,'dpi':dpi,'declined':z['decline'],'confidence':z['confidence'],'uncertainty':z['uncertainty'],'methods':{name:scores(gt & region,mask & region) for name,mask in zip(['baseline','local','energy','geometry'],z['masks'])},'fit':z['fit'],'blob_core_fraction':float((z['core']&blob).sum()/max(1,blob.sum())),'blob_supported_fraction':float((z['support']&blob).sum()/max(1,blob.sum()))})
 return out

def real(gate):
 out={}
 for key,(target,kind) in CASES.items():
  img=Image.open(NATIVE/f'{key}-000.png').convert('RGB'); x0,y0,x1,y1=target;pad=max(30,(y1-y0)//2); box=(max(0,x0-pad),max(0,y0-pad),min(img.width,x1+pad),min(img.height,y1+pad)); rgb=np.asarray(img.crop(box));run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());report=json.loads(pathlib.Path(run['rows']['sw-E']['path']+'.json').read_text());paper=report['conversion']['page_reports'][0]['polarity_paper_luminance'];t=time.perf_counter();z=reconstruction(rgb,paper);elapsed=time.perf_counter()-t
  # Crop metrics use observation-space fit; no real latent GT is claimed.
  accepted=calibration.accepts({'declined':z['decline'],'confidence':z['confidence'],'uncertainty':z['uncertainty']},gate)
  row={'class':kind,'target_bbox':target,'context_bbox':box,'baseline_paper_luma':paper,'local_background_rgb':z['background_rgb'],'ink_rgb':z['ink_rgb'],'contrast_linear':z['contrast'],'noise_linear':z['noise'],'confidence_heuristic':z['confidence'],'decline':z['decline'],'calibrated_accept':accepted,'psf_sigma_px':z['sigma'],'width_scale':z['width_scale'],'rescan_rmse_linear':dict(zip(['baseline_mask','local','energy','geometry'],z['fit'])),'geometry_topology':topology(z['masks'][3]),'baseline_topology':topology(z['masks'][0]),'foreground_fraction':[float(m.mean()) for m in z['masks']],'seconds':elapsed,'core_samples':int(z['core'].sum()),'ink_uncertainty':z['uncertainty'],'components':[{**c,'ink':srgb(c['ink']).tolist(),'bbox_source':[c['bbox'][0]+box[0],c['bbox'][1]+box[1],c['bbox'][2]+box[0],c['bbox'][3]+box[1]]} for c in z['components']],'background_luma_percentiles':np.percentile(rgb_luma(z['background']),[10,50,90]).tolist(),'core_luma_percentiles':np.percentile(rgb_luma(linear(rgb))[z['core']],[10,50,90]).tolist(),'alpha_percentiles':np.percentile(z['alpha'],[10,50,90,99]).tolist(),'probability_percentiles':np.percentile(z['probability'],[10,50,90,99]).tolist()}
  # Compare target pixels to the source using a fixed local-paper-minus-20
  # diagnostic. This is not a semantic stroke ground truth.
  tx0,ty0,tx1,ty1=x0-box[0],y0-box[1],x1-box[0],y1-box[1]
  source=rgb[ty0:ty1,tx0:tx1];gray=rgb_luma(source.astype(float));threshold=float(np.percentile(gray,95)-20); ink_truth=gray<threshold
  local_rgb=srgb(np.where(z['support'][...,None],z['background']*(1-z['alpha'][...,None])+z['ink']*z['alpha'][...,None],linear(rgb)))[ty0:ty1,tx0:tx1]
  base_path=R/key/'sw-E'/'pdfium-aligned.png'; target_rows={}
  variants={'local':local_rgb}
  if base_path.exists():variants['baseline']=np.asarray(Image.open(base_path).convert('RGB').crop(target))
  for label,render in variants.items():
   if render.shape!=source.shape:continue
   lum_render=rgb_luma(render.astype(float));de=deltaE_ciede2000(rgb2lab(source),rgb2lab(render));target_rows[label]={'source_ink_recall':float((lum_render[ink_truth]<threshold).mean()) if ink_truth.any() else None,'source_ink_mean_delta_e2000':float(de[ink_truth].mean()) if ink_truth.any() else None,'mean_abs_rgb_difference':float(np.abs(render.astype(float)-source.astype(float)).mean())}
  row['target_diagnostics']=target_rows;row['rendered_support_fraction']=float(z['support'][ty0:ty1,tx0:tx1].mean());out[key]=row
  # Image panels show the same original source coordinates for all rows.
  c=(x0-box[0],y0-box[1],x1-box[0],y1-box[1]);layers=[('source',Image.fromarray(rgb).crop(c))]
  for label,name in [('baseline','sw-E')]:
   p=R/key/name/'pdfium-aligned.png';layers.append((label,Image.open(p).convert('RGB').crop(target) if p.exists() else None))
  for name,a in [('local',z['alpha']),('energy',z['masks'][2]),('geometry',z['masks'][3])]:
   clean=z['background']*(1-a[...,None])+z['ink']*a[...,None];clean=np.where(z['support'][...,None],clean,linear(rgb));layers.append((name,Image.fromarray(srgb(clean)).crop(c)))
  delta=np.abs(z['pred'][3]-linear(rgb)); residual=Image.fromarray(np.uint8(np.clip(delta*5*255,0,255)));layers.append(('rescan residual x5 linear',residual.crop(c)))
  for label,name in [('MRC','mrc-M'),('Adobe','adobe-E')]:
   p=R/key/name/'pdfium-aligned.png';layers.append((label,Image.open(p).convert('RGB').crop(target) if p.exists() else None))
  scale=3;w=(x1-x0)*scale;h=(y1-y0)*scale;sheet=Image.new('RGB',(w,len(layers)*(h+20)),'white');draw=ImageDraw.Draw(sheet)
  for i,(label,im) in enumerate(layers):
   draw.text((2,i*(h+20)),label if im else label+' unavailable / unregistered',fill='black')
   if im:sheet.paste(im.resize((w,h),Image.Resampling.NEAREST),(0,i*(h+20)+20))
  sheet.save(OUT/'panels'/f'{key}.png')
  if not accepted:
   for idx in (2,3,4):
    draw.text((2,idx*(h+20)),layers[idx][0]+' after gate: source raster',fill='black');sheet.paste(layers[0][1].resize((w,h),Image.Resampling.NEAREST),(0,idx*(h+20)+20))
  sheet.save(OUT/'panels'/f'{key}-gated.png')
  for name,arr in [('alpha',z['alpha']),('probability',z['probability']),('core',z['core']),('skeleton',z['skeleton'])]:Image.fromarray(np.uint8(np.asarray(arr)*255)).save(OUT/'panels'/f'{key}-{name}.png')
 return out

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'panels').mkdir(exist_ok=True);start=time.perf_counter();syn=synthetic();gate=calibration.calibrate(syn);
 for row in syn:row['calibrated_accept']=calibration.accepts(row,gate)
 (OUT/'gate.json').write_text(json.dumps(gate,indent=2));(OUT/'synthetic.json').write_text(json.dumps(syn,indent=2));print('synthetic',len(syn),'gate',gate,flush=True);rows=real(gate);(OUT/'real.json').write_text(json.dumps(rows,indent=2));meta={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'skimage':skimage.__version__,'Pillow':PIL.__version__,'font_sha256':{x:hashlib.sha256(pathlib.Path(x).read_bytes()).hexdigest() for x in FONTS},'elapsed_s':time.perf_counter()-start};(OUT/'versions.json').write_text(json.dumps(meta,indent=2));print('done',meta['elapsed_s'],flush=True)
if __name__=='__main__':main()
