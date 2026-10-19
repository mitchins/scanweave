"""One native-resource packing control. Never used by the converter."""
from pathlib import Path
import pikepdf,json,re,zlib,tempfile,subprocess,hashlib
import numpy as np,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;D=B/'native-control';D.mkdir(exist_ok=True)
source=pikepdf.open(B/'300/final.pdf');q=pikepdf.Pdf.new();q.pages.append(source.pages[0]);page=q.pages[0]
report=json.loads((B/'300/report.json').read_text())['page_reports'][0];items=[]
for i,patch in enumerate(report['patches']):
 if patch['compact_background']:continue
 obj=page.Resources.XObject['/Im'+str(i)];a=np.asarray(pikepdf.PdfImage(obj).as_pil_image().convert('RGB'));items.append((i,a))
q.save(D/'native.pdf',object_stream_mode=pikepdf.ObjectStreamMode.generate,deterministic_id=True)
w=max(a.shape[1] for i,a in items);h=sum(a.shape[0] for i,a in items);canvas=np.full((h,w,3),255,np.uint8);positions={};y=0
for i,a in items:
 ah,aw=a.shape[:2];canvas[y:y+ah,:aw]=a;positions[i]=(0,y,aw,ah);y+=ah
isgray=bool(np.all(canvas[:,:,0]==canvas[:,:,1]) and np.all(canvas[:,:,0]==canvas[:,:,2]));samples=canvas[:,:,0].tobytes() if isgray else canvas.tobytes()
stream=pikepdf.Stream(q,samples);stream.Type=pikepdf.Name.XObject;stream.Subtype=pikepdf.Name.Image;stream.Width=w;stream.Height=h;stream.BitsPerComponent=8;stream.ColorSpace=pikepdf.Name.DeviceGray if isgray else pikepdf.Name.DeviceRGB
page.Resources.XObject.Atlas=stream
content=page.Contents.read_bytes()
def replace(m):
 i=int(m.group(1))
 if i not in positions:return m.group(0)
 x,y,aw,ah=positions[i];return f'q 0 0 1 1 re W n {w/aw:.12g} 0 0 {h/ah:.12g} {-x/aw:.12g} {-(h-y-ah)/ah:.12g} cm /Atlas Do Q'.encode()
page.Contents=pikepdf.Stream(q,re.sub(rb'/Im(\d+) Do',replace,content))
for i in positions:del page.Resources.XObject['/Im'+str(i)]
q.save(D/'atlas.pdf',object_stream_mode=pikepdf.ObjectStreamMode.generate,deterministic_id=True)
metrics={}
for renderer in ['pdfium','poppler']:
 arrays=[]
 for arm in ['native','atlas']:
  p=D/(arm+'.pdf')
  if renderer=='pdfium':doc=pdfium.PdfDocument(str(p));im=doc[0].render(scale=300/72).to_pil().convert('RGB')
  else:
   subprocess.run(['pdftoppm','-singlefile','-r','300','-png',str(p),str(D/(arm+'-'+renderer))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);im=Image.open(D/(arm+'-'+renderer+'.png')).convert('RGB')
  if renderer=='pdfium':im.save(D/(arm+'-'+renderer+'.png'))
  arrays.append(np.asarray(im).astype(np.int16))
 delta=np.abs(arrays[0]-arrays[1]);metrics[renderer]={'pixel_identical':bool(np.all(delta==0)),'changed_pixels':int(np.any(delta!=0,axis=2).sum()),'mae':float(delta.mean()),'max_channel_difference':int(delta.max())}
result={'native_objects':len(items),'atlas_objects':1,'native_pdf_bytes':(D/'native.pdf').stat().st_size,'atlas_pdf_bytes':(D/'atlas.pdf').stat().st_size,'atlas_flate_bytes':len(zlib.compress(samples,6)),'same_native_samples':True,'renderers':metrics,'disposition':'storage diagnostic only; no converter atlas path introduced'}
(D/'metrics.json').write_text(json.dumps(result,indent=2));print(result)
