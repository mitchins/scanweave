"""One tiny exactly two-level native-detail patch as a stencil mask. Diagnostic only."""
from pathlib import Path
import pikepdf,json,numpy as np,subprocess,tempfile,zlib
import pypdfium2 as pdfium
from PIL import Image

MASK_PDF = 'mask.pdf'

B=Path(__file__).resolve().parent;D=B/'mask-control';D.mkdir(exist_ok=True);p=pikepdf.open(B/'real/scanweave/scan-linn.pdf');pg=p.pages[0];chosen=None
for name,obj in pg.Resources.XObject.items():
 a=np.asarray(pikepdf.PdfImage(obj).as_pil_image().convert('RGB'));vals=np.unique(a)
 if len(vals)==2 and vals[-1]==255 and np.all(a[:,:,0]==a[:,:,1]) and np.all(a[:,:,0]==a[:,:,2]):chosen=(name,obj,a[:,:,0],vals);break
assert chosen is not None
name,obj,a,values=chosen;h,w=a.shape;original_stream=len(obj.read_raw_bytes());p.save(D/'native.pdf',object_stream_mode=pikepdf.ObjectStreamMode.generate,deterministic_id=True)
# PDF stencil bit zero paints the lower gray, bit one is transparent.
packed=np.packbits(a==255,axis=1,bitorder='big').tobytes();mask=pikepdf.Stream(p,packed);mask.Type=pikepdf.Name.XObject;mask.Subtype=pikepdf.Name.Image;mask.ImageMask=True;mask.BitsPerComponent=1;mask.Width=w;mask.Height=h
pg.Resources.XObject[name]=mask
content=pg.Contents.read_bytes();target=(str(name)+' Do').encode();replacement=f'q 1 g 0 0 1 1 re f {int(values[0])/255:.12g} g {name} Do Q'.encode();assert target in content;pg.Contents=pikepdf.Stream(p,content.replace(target,replacement));p.save(D/MASK_PDF,object_stream_mode=pikepdf.ObjectStreamMode.generate,deterministic_id=True)
metrics={}
for renderer in ['pdfium','poppler']:
 arrays=[]
 for arm in ['native','mask']:
  path=D/(arm+'.pdf')
  if renderer=='pdfium':doc=pdfium.PdfDocument(str(path));im=doc[0].render(scale=300/72).to_pil().convert('RGB')
  else:
   with tempfile.TemporaryDirectory() as t:
    prefix=Path(t)/'r';subprocess.run(['pdftoppm','-singlefile','-r','300','-png',str(path),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);im=Image.open(prefix.with_suffix('.png')).convert('RGB').copy()
  arrays.append(np.asarray(im).astype(np.int16))
 diff=np.abs(arrays[0]-arrays[1]);metrics[renderer]={'pixel_identical':bool(np.all(diff==0)),'changed_pixels':int(np.any(diff!=0,axis=2).sum()),'mae':float(diff.mean()),'max_difference':int(diff.max())}
result={'source':'scan-linn','resource':str(name),'width':w,'height':h,'gray_levels':values.tolist(),'original_stream_bytes':original_stream,'mask_payload_deflate_bytes':len(zlib.compress(packed,6)),'native_pdf_bytes':(D/'native.pdf').stat().st_size,'mask_pdf_bytes':(D/MASK_PDF).stat().st_size,'renderers':metrics,'scope':'one two-tone detail/fringe patch; not a general text-mask result; no product mask path'}
saved=pikepdf.open(D/MASK_PDF);result['actual_mask_stream_bytes']=len(saved.pages[0].Resources.XObject[name].read_raw_bytes());(D/'metrics.json').write_text(json.dumps(result,indent=2));print(result)
