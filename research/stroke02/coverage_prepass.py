"""Dev-only coverage sidecar: pooled OCR-line ink; never changes source pixels."""
import json,os,pathlib,re,subprocess,sys,time
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from lxml import html
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B,O=c.B,c.O;root=O/'pages';root.mkdir(exist_ok=True); key=sys.argv[1];run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dest=root/key;dest.mkdir(exist_ok=True);t0=time.monotonic()
source=run['rows']['src']['path'];subprocess.run(['pdfimages','-f','1','-l','1','-png',source,str(dest/'source')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
files=list(dest.glob('source-*.png'))
if len(files)!=1:raise RuntimeError(f'expected one original image, found {len(files)}')
rgb=np.asarray(Image.open(files[0]).convert('RGB'));height,width=rgb.shape[:2];coverage=np.zeros((height,width),np.uint8);lines=html.parse(str(B/'phase2/runs'/key/'selected.hocr'));records=[]
pat=re.compile(r'\bbbox (\d+) (\d+) (\d+) (\d+)');chars=re.compile(r'x_bboxes (\d+) (\d+) (\d+) (\d+)')
for line in lines.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocr_line ")]'):
 m=pat.search(line.get('title',''))
 if not m:continue
 x0,y0,x1,y1=map(int,m.groups());x0=max(0,x0-5);y0=max(0,y0-5);x1=min(width,x1+5);y1=min(height,y1+5)
 if x1-x0<8 or y1-y0<8 or (x1-x0)*(y1-y0)>2_000_000:continue
 boxes=[]
 for el in line.xpath('.//*[@title]'):
  b=chars.search(el.get('title',''))
  if b:
   a,b0,d,e=map(int,b.groups());a=max(x0,a-1);d=min(x1,d+1);b0=max(y0,b0-1);e=min(y1,e+1)
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
 alpha=np.clip((dif@direction)/den,0,1);allowed=np.zeros(alpha.shape,bool)
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
 sigma=float(np.clip(np.median(widths),.3,1.5));latent=c.bounded_inverse(alpha,sigma,30);latent*=allowed
 # Enclosed near-paper pixels remain raster evidence, never latent ink.
 noise=max(.005,float(1.4826*np.median(np.abs(lum[~allowed]-np.median(lum[~allowed]))))) if (~allowed).any() else .01
 ink=alpha>.25;holes=ndi.binary_fill_holes(ink,structure=np.ones((3,3)))&~ink;veto=holes&(np.abs(lum)<=2*noise);latent[veto]=0
 target=coverage[y0:y1,x0:x1];np.maximum(target,np.rint(latent*255).astype(np.uint8),out=target)
 records.append({'bbox':[x0,y0,x1,y1],'sigma':sigma,'edges':len(widths),'noise_proxy':noise,'veto_pixels':int(veto.sum()),'boxes':len(boxes)})
Image.fromarray(coverage).save(dest/'coverage.png',compress_level=3);(dest/'prepass.json').write_text(json.dumps({'key':key,'source':source,'dims':[width,height],'lines':records,'wall_seconds':time.monotonic()-t0},indent=2));files[0].unlink();print(key,'lines',len(records),'seconds',round(time.monotonic()-t0,2),flush=True)
