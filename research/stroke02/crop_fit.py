"""Crop-only inverse imaging trial. Produces diagnostic PDFs, not ScanWeave PDFs."""
import io,json,math,pathlib,re,sys
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
from skimage import measure,morphology
from lxml import html
import fitz,pypdfium2 as pdfium
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'stroke01'))
import prototype as st
B=pathlib.Path('/data/coding/scanweave/work/books01');O=B/'stroke02';(O/'crops').mkdir(exist_ok=True);(O/'compare').mkdir(exist_ok=True)
CASES={'8967062':{'target':(1165,748,1236,791),'context':(1135,718,1266,821),'sigma':1.22},'12342014':{'target':(84,360,611,442),'context':(43,319,652,483),'sigma':.93}}

def get_groups(key,target):
 doc=html.parse(str(B/'phase2/runs'/key/'selected.hocr')); groups=[];x0,y0,x1,y1=target
 for word in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
  for node in word:
   found=re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',node.get('title',''))
   if not found:continue
   a,b,c,d=map(int,found.groups());cx=(a+c)/2;cy=(b+d)/2
   if x0+3<=cx<x1-3 and y0+3<=cy<y1-3:groups.append([a,b,c,d])
 return sorted(groups,key=lambda p:(p[1]//15,p[0]))
def gaussian(a,s):return ndi.gaussian_filter(a,sigma=s,mode='nearest')
def bounded_inverse(observed,sigma,steps):
 # Projected gradient descent on ||G_sigma x - y||² plus a small source-local
 # gradient penalty; bounded coverage prevents RL's >1 overshoot.
 x=observed.copy()
 for _ in range(steps):
  err=gaussian(x,sigma)-observed;gradient=gaussian(err,sigma)-.006*ndi.laplace(x);x=np.clip(x-.85*gradient,0,1)
 return x

def pdf_crop(path,key,target,dpi,mode,geom=None):
 doc=pdfium.PdfDocument(str(path));page=doc[0];scale=dpi*mode/72;im=page.render(scale=scale).to_pil().convert('RGB');x0,y0,x1,y1=target;size=((x1-x0)*mode,(y1-y0)*mode)
 if geom:
  theta=math.radians(geom['rotation_degrees']);s=geom['scale_x'];tx,ty=geom['translation_px'];co=math.cos(theta)/s;si=math.sin(theta)/s
  coeff=(co,si,co*(x0-tx)*mode+si*(y0-ty)*mode,-si,co,-si*(x0-tx)*mode+co*(y0-ty)*mode)
  im=im.transform(size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC,fillcolor='white')
 else:im=im.crop((x0*mode,y0*mode,x1*mode,y1*mode))
 return im

def vector_pdf(key,setting):
 conf=CASES[key];target=conf['target'];cx0,cy0,cx1,cy1=conf['context'];x0,y0,x1,y1=target;native=Image.open(O/'native'/f'{key}-000.png').convert('RGB');rgb=np.asarray(native.crop(conf['context']));run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dpi=run['dpi'];z=st.reconstruction(rgb,237.8 if key=='8967062' else 204.3);obs=st.linear(rgb);bg=z['background']; ink=z['ink'];anchor=None
 if key=='8967062' and setting.get('anchor','header')=='header':
  # Explicitly experimental cross-line colour hypothesis; not an assumed truth.
  head=st.reconstruction(np.asarray(native.crop((1570,190,2035,255))),237.8);anchor=head['ink_rgb']; reference=np.broadcast_to(st.linear(np.array(anchor)),obs.shape);mix=setting.get('ink_mix',1.);ink=mix*reference+(1-mix)*ink
 diff=bg-ink;alpha=np.clip(((bg-obs)*diff).sum(-1)/np.maximum((diff*diff).sum(-1),1e-8),0,1);groups=get_groups(key,target);allowed=np.zeros(alpha.shape,bool)
 for a,b,c,d in groups:
  # OCR contributes rectangles only, not the character identity or shape.
  a=max(0,a-cx0-1);b=max(0,b-cy0-1);c=min(rgb.shape[1],c-cx0+1);d=min(rgb.shape[0],d-cy0+1);allowed[b:d,a:c]=True
 observed=alpha*allowed; sigma=conf['sigma']*setting['sigma_multiplier'];latent=bounded_inverse(observed,sigma,setting['steps']);latent*=allowed
 # Small marks are not reconstructed or erased; they stay raster-owned.
 binary=latent>=setting['level'];lab,n=ndi.label(binary,np.ones((3,3)));objects=ndi.find_objects(lab);eligible=np.zeros_like(binary);small=0
 for i,sl in enumerate(objects,1):
  if sl is None:continue
  mask=lab[sl]==i; area=int(mask.sum())
  if area<5:small+=1;continue
  eligible[sl]|=mask
 support=ndi.binary_dilation(eligible,iterations=3)&allowed
 # Remove only supported text, then paint antialiased PDF paths. This crop-only
 # packaging deliberately keeps the source image; it cannot prove compression.
 base=obs.copy();base[support]=bg[support];base=st.srgb(base)[y0-cy0:y1-cy0,x0-cx0:x1-cx0];stream=io.BytesIO();Image.fromarray(base).save(stream,format='PNG')
 doc=fitz.open();page=doc.new_page(width=(x1-x0)*72/dpi,height=(y1-y0)*72/dpi);page.insert_image(page.rect,stream=stream.getvalue());used=0
 colour=np.median(ink[support],axis=0) if support.any() else np.array([0.,0.,0.]);colour=st.srgb(colour)/255
 levels=[(.20,.20),(.40,.25),(.60,1/3),(.80,.5)] if setting.get('layers') else [(setting['level'],1.)]
 for level,opacity in levels:
  shape=page.new_shape();layer_used=0
  contours=measure.find_contours(np.pad((latent*ndi.binary_dilation(eligible,iterations=2)),1),level)
  for c in contours:
   if len(c)<4:continue
   if setting.get('smooth',0)>0 and len(c)>6:
    c=ndi.gaussian_filter1d(c,setting['smooth'],axis=0,mode='wrap')
   pts=[fitz.Point((p[1]-1+cx0-x0+.5)*72/dpi,(p[0]-1+cy0-y0+.5)*72/dpi) for p in c]
   shape.draw_polyline(pts);used+=1;layer_used+=1
  if layer_used:shape.finish(color=None,fill=tuple(map(float,colour)),fill_opacity=opacity,even_odd=True,closePath=True);shape.commit()
 path=O/'crops'/f'{key}-{setting["name"]}.pdf';doc.save(path,deflate=True,garbage=4)
 rescan=gaussian(np.clip(latent,0,1),sigma); window=allowed & (ndi.binary_dilation(observed>.03,iterations=3));rmse=float(np.sqrt(np.mean((rescan[window]-observed[window])**2))) if window.any() else None
 # Score the PDF-rendered candidate itself, rather than only the pre-contour
 # latent field. Use a common OCR-group window and the same local B and K;
 # unchanged raster outside supported pixels can be blurred twice at margins.
 rendered=np.asarray(pdfium.PdfDocument(str(path))[0].render(scale=dpi*2/72).to_pil().convert('RGB'))
 hh=y1-y0;ww=x1-x0; rendered=rendered[:hh*2,:ww*2]; rendered=st.linear(rendered).reshape(hh,2,ww,2,3).mean((1,3))
 sy=slice(y0-cy0,y1-cy0);sx=slice(x0-cx0,x1-cx0); bp=bg[sy,sx];op=obs[sy,sx];kp=st.linear(np.rint(colour*255).astype(np.uint8));di=bp-kp;coverage=np.clip(((bp-rendered)*di).sum(-1)/np.maximum((di*di).sum(-1),1e-8),0,1);rescanned=gaussian(coverage,sigma);prediction=bp*(1-rescanned[...,None])+kp*rescanned[...,None];compare=allowed[sy,sx];pdf_rmse=float(np.sqrt(np.mean((prediction[compare]-op[compare])**2))) if compare.any() else None
 rows=[]
 if key=='8967062':
  for a,b,c,d in groups:
   region=eligible[max(0,b-cy0):min(rgb.shape[0],d-cy0),max(0,a-cx0):min(rgb.shape[1],c-cx0)]; labels,cc=ndi.label(region,np.ones((3,3)));holes=ndi.binary_fill_holes(region)&~region;_,hh=ndi.label(holes);sk=morphology.skeletonize(region);near=ndi.convolve(sk.astype(int),np.ones((3,3),int));terminal=int((sk&(near==2)).sum());width=2*ndi.distance_transform_edt(region)[sk];rows.append({'bbox':[a,b,c,d],'components':int(cc),'holes':int(hh),'skeleton_terminals':terminal,'observed_mask_width_median':float(np.median(width)) if len(width) else None})
 return {'path':str(path),'groups':len(groups),'source_anchor_rgb':anchor,'paint_rgb':np.rint(colour*255).astype(int).tolist(),'sigma':sigma,'latent_rmse':rmse,'pdf_rescan_linear_rgb_rmse':pdf_rmse,'contours':used,'small_components_left_raster':small,'digit_topology':rows}

def main():
 settings=[{'name':'observed','sigma_multiplier':1,'steps':0,'level':.5},{'name':'inverse12','sigma_multiplier':1,'steps':12,'level':.5},{'name':'inverse60','sigma_multiplier':1,'steps':60,'level':.5},{'name':'inverse60_softpsf','sigma_multiplier':.76,'steps':60,'level':.5},{'name':'local12','anchor':'local','sigma_multiplier':1,'steps':12,'level':.5},{'name':'local60','anchor':'local','sigma_multiplier':1,'steps':60,'level':.5},{'name':'local60_tight','anchor':'local','sigma_multiplier':1,'steps':60,'level':.65},{'name':'local12_wide','anchor':'local','sigma_multiplier':1,'steps':12,'level':.35},{'name':'mixed12','ink_mix':.4,'sigma_multiplier':1,'steps':12,'level':.5},{'name':'mixed60','ink_mix':.4,'sigma_multiplier':1,'steps':60,'level':.5},{'name':'mixed12_smooth','ink_mix':.4,'sigma_multiplier':1,'steps':12,'level':.5,'smooth':.75},{'name':'local_observed_low','anchor':'local','sigma_multiplier':1,'steps':0,'level':.25},{'name':'local12_low','anchor':'local','sigma_multiplier':1,'steps':12,'level':.25},{'name':'local12_mid','anchor':'local','sigma_multiplier':1,'steps':12,'level':.32},{'name':'local_layers','anchor':'local','sigma_multiplier':1,'steps':0,'level':.2,'layers':True},{'name':'inverse_layers','anchor':'local','sigma_multiplier':1,'steps':12,'level':.2,'layers':True},{'name':'mixed_layers','ink_mix':.4,'sigma_multiplier':1,'steps':12,'level':.2,'layers':True}];results={};baseline=json.loads(pathlib.Path('/tmp/scanweave-books01/qualification/books01/phase2/results.json').read_text())['pages']
 for key,c in CASES.items():
  run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dpi=run['dpi'];id=run['id'];rows=baseline[id]['rows'];results[key]={}
  for setting in settings:results[key][setting['name']]=vector_pdf(key,setting)
  for zoom in [1,2]:
   images=[]
   for label,row in [('source','src'),('baseline','sw-E'),('MRC','mrc-M'),('Adobe','adobe-E')]:
    info=run['rows'].get(row,{});path=info.get('path');
    if row=='adobe-E' and not path:
     candidates=[B/'runs/adobe'/f'{key}.adobe.pdf',B/'runs/adobe-p2'/f'{key}.adobe.pdf'];path=next((str(p) for p in candidates if p.exists()),None)
    geom=None if row=='src' else rows.get(row,{}).get('geometry');
    if path and pathlib.Path(path).exists() and (not geom or geom.get('status')=='accepted'):images.append((label,pdf_crop(path,key,c['target'],dpi,zoom,geom)))
    else:images.append((label,None))
   for setting in settings:
    path=results[key][setting['name']]['path'];doc=pdfium.PdfDocument(path);images.insert(-2,(setting['name'],doc[0].render(scale=dpi*zoom/72).to_pil().convert('RGB')))
   w=(c['target'][2]-c['target'][0])*zoom;h=(c['target'][3]-c['target'][1])*zoom;sheet=Image.new('RGB',(w,len(images)*(h+22)),'white');draw=ImageDraw.Draw(sheet)
   for i,(label,img) in enumerate(images):
    draw.text((2,i*(h+22)),label if img else label+' unavailable',fill='black')
    if img:sheet.paste(img,(0,i*(h+22)+22))
   sheet.save(O/'compare'/f'{key}-{zoom}x.png')
  print(key,json.dumps(results[key]),flush=True)
 (O/'crop-results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
