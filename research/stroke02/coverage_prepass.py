"""Dev-only coverage sidecar: pooled OCR-line ink; never changes source pixels."""
import json,os,pathlib,re,subprocess,sys,time
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from lxml import html
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B,O=c.B,c.O;root=O/'pages-extensions';root.mkdir(exist_ok=True); key=sys.argv[1];run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dest=root/key;dest.mkdir(exist_ok=True);t0=time.monotonic()
source=run['rows']['src']['path'];subprocess.run(['pdfimages','-f','1','-l','1','-png',source,str(dest/'source')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
files=list(dest.glob('source-*.png'))
if len(files)!=1:raise RuntimeError(f'expected one original image, found {len(files)}')
rgb=np.asarray(Image.open(files[0]).convert('RGB'));height,width=rgb.shape[:2];coverage=np.zeros((height,width),np.uint8);paper_veto=np.zeros((height,width),np.uint8);lines=html.parse(str(B/'phase2/runs'/key/'selected.hocr'));records=[];declined=[]
pat=re.compile(r'\bbbox (\d+) (\d+) (\d+) (\d+)');chars=re.compile(r'x_bboxes (\d+) (\d+) (\d+) (\d+)')
regions=[]
for line in lines.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocr_line ")]'):
 words=[]
 for word in line.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
  m=pat.search(word.get('title',''))
  if m:words.append((tuple(map(int,m.groups())),word))
 words.sort(key=lambda x:x[0][0]);groups=[]
 for box,word in words:
  if not groups:groups.append([(box,word)]);continue
  previous=groups[-1][-1][0];word_height=max(1,box[3]-box[1],previous[3]-previous[1])
  if box[0]-previous[2]>2*word_height:groups.append([])
  groups[-1].append((box,word))
 for group in groups:
  bound=(min(w[0][0] for w in group),min(w[0][1] for w in group),max(w[0][2] for w in group),max(w[0][3] for w in group))
  charboxes=[]
  for _,word in group:
   for el in word.xpath('.//*[@title]'):
    match=chars.search(el.get('title',''))
    if match:charboxes.append(tuple(map(int,match.groups())))
  regions.append((bound,charboxes))
for (left,top,right,bottom),source_boxes in regions:
 x0=max(0,left-5);y0=max(0,top-5);x1=min(width,right+5);y1=min(height,bottom+5)
 if x1-x0<8 or y1-y0<8 or (x1-x0)*(y1-y0)>2_000_000:continue
 boxes=[]
 for a,b0,d,e in source_boxes:
  a=max(x0,a-1);d=min(x1,d+1);b0=max(y0,b0-1);e=min(y1,e+1)
  if d>a and e>b0:boxes.append((a,b0,d,e))
 if not boxes:continue
 im=c.st.linear(rgb[y0:y1,x0:x1]);paper=np.quantile(im.reshape(-1,3),.9,axis=0);dif=paper-im;lum=dif@np.array([.2126,.7152,.0722]);cores=[]
 for a,b0,d,e in boxes:
  patch=dif[b0-y0:e-y0,a-x0:d-x0];v=lum[b0-y0:e-y0,a-x0:d-x0]
  if v.size<4:continue
  threshold=np.quantile(v,.9);sel=patch[v>=threshold]
  if len(sel):cores.append(np.median(sel,axis=0))
 if len(cores)<3:continue
 direction=np.median(np.array(cores),axis=0);den=float(direction@direction)
 if den<.01:continue
 relative=np.maximum((dif@direction)/den,0);alpha=np.clip(relative,0,1);allowed=np.zeros(alpha.shape,bool)
 for a,b0,d,e in boxes:allowed[b0-y0:e-y0,a-x0:d-x0]=True
 # Estimate edge widths from local gradient profiles; weak/ambiguous pages fall back.
 gray=im@np.array([.2126,.7152,.0722]);gx=np.abs(np.diff(gray,axis=1));inds=np.argwhere(gx>.05);rng=np.random.default_rng(1201);inds=inds[rng.choice(len(inds),min(100,len(inds)),replace=False)] if len(inds) else []
 widths=[]
 for yy,xx in inds:
  if xx<4 or xx+6>=gray.shape[1]:continue
  z=gray[yy,xx-4:xx+7]; lo=float(np.median(z[:2]));hi=float(np.median(z[-2:]));delta=hi-lo
  if abs(delta)<.08:continue
  norm=(z-lo)/delta
  if np.sum(np.diff(norm)<-.1)>1:continue
  a=np.where(norm>=.16)[0];b=np.where(norm>=.84)[0]
  if len(a) and len(b):widths.append(abs(int(b[0])-int(a[0]))/2.)
 if len(widths)<4:continue
 sigma=float(np.clip(np.median(widths),.3,1.5))
 positive=direction>1e-6;tmax=float(min(1.5,np.min(paper[positive]/direction[positive]))) if positive.any() else 0
 if tmax<1:continue
 # Fit the pooled ink-strength scalar against local forward residual. This is
 # a bounded grid diagnostic, not a calibrated confidence interval.
 samples=[]
 for strength in np.linspace(1,tmax,4):
  latent0=c.bounded_inverse(np.clip(relative/strength,0,1),sigma,10)
  prediction=ndi.gaussian_filter(latent0,sigma)*strength
  samples.append((float(np.mean((prediction[allowed]-relative[allowed])**2)),float(strength)))
 _,strength=min(samples);alpha=np.clip(relative/strength,0,1);latent=c.bounded_inverse(alpha,sigma,30);latent*=allowed
 ink_rgb=c.st.srgb(np.clip(paper-strength*direction,0,1)).tolist()
 # A fit pinned at the blur or ink-strength bound is not identified. Never
 # paint its extrapolated colour or admit its coverage as evidence.
 if sigma>=1.49 or (tmax>1.02 and strength>=tmax-1e-6):
  declined.append({'bbox':[x0,y0,x1,y1],'sigma':sigma,'t':strength,'tmax':tmax,'ink_rgb':ink_rgb,'reason':'fit_at_parameter_bound'})
  continue
 # Enclosed near-paper pixels remain raster evidence, never latent ink.
 noise=max(.005,float(1.4826*np.median(np.abs(lum[~allowed]-np.median(lum[~allowed]))))) if (~allowed).any() else .01
 ink=alpha>.25;holes=ndi.binary_fill_holes(ink,structure=np.ones((3,3)))&~ink;veto=holes&(np.abs(lum)<=2*noise);latent[veto]=0;paper_veto[y0:y1,x0:x1][veto]=255
 target=coverage[y0:y1,x0:x1];np.maximum(target,np.rint(latent*255).astype(np.uint8),out=target)
 records.append({'bbox':[x0,y0,x1,y1],'sigma':sigma,'t':strength,'ink_rgb':ink_rgb,'edges':len(widths),'noise_proxy':noise,'veto_pixels':int(veto.sum()),'boxes':len(boxes)})
coverage[paper_veto>0]=0;Image.fromarray(coverage).save(dest/'coverage.png',compress_level=3);Image.fromarray(paper_veto).save(dest/'paper-veto.png',compress_level=3);(dest/'prepass.json').write_text(json.dumps({'key':key,'source':source,'dims':[width,height],'lines':records,'declined':declined,'wall_seconds':time.monotonic()-t0},indent=2));files[0].unlink();print(key,'lines',len(records),'seconds',round(time.monotonic()-t0,2),flush=True)
