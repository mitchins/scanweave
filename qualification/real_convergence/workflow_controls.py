"""Native JPEG preservation + unsupported geometry fallback on genuine imagery."""
import json,hashlib,subprocess,os,io,tempfile
from pathlib import Path
import pikepdf,pypdfium2 as pdfium,numpy as np
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'workflow';D.mkdir(exist_ok=True);exe=os.environ.get('SCANWEAVE_BIN',str(R/'target/release/scanweave'));checks=[]
source=pikepdf.open(R/'qualification/pdf_packaging/real/input/cord-00.pdf');im=pikepdf.PdfImage(next(iter(source.pages[0].Resources.XObject.values()))).as_pil_image().convert('RGB');buf=io.BytesIO();im.save(buf,format='JPEG',quality=98,subsampling=0);data=buf.getvalue();w,h=im.size;q=pikepdf.Pdf.new();pg=q.add_blank_page(page_size=(w*72/300,h*72/300));image=pikepdf.Stream(q,data);image.Type=pikepdf.Name.XObject;image.Subtype=pikepdf.Name.Image;image.Width=w;image.Height=h;image.BitsPerComponent=8;image.ColorSpace=pikepdf.Name.DeviceRGB;image.Filter=pikepdf.Name.DCTDecode;pg.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image));pg.Contents=pikepdf.Stream(q,f'q {w*72/300} 0 0 {h*72/300} 0 0 cm /I Do Q'.encode());inp=D/'jpeg-input.pdf';out=D/'jpeg-output.pdf';q.save(inp,deterministic_id=True)
subprocess.run([exe,str(inp),str(out)],check=True,env=dict(os.environ,OMP_THREAD_LIMIT='1'),stdout=subprocess.DEVNULL)
r=json.loads(Path(str(out)+'.json').read_text());assert r['pages'][0]['raster_import']=='native_source_samples';assert r['pages'][0]['rasterizer_args'] is None
p=pikepdf.open(out);images=[o for o in p.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name.Image];assert len(images)==1;assert images[0].read_raw_bytes()==data
for renderer in ['pdfium','poppler']:
 def render(path):
  if renderer=='pdfium':return pdfium.PdfDocument(str(path))[0].render(scale=300/72).to_pil().convert('RGB').tobytes()
  with tempfile.TemporaryDirectory() as t:
   dst=Path(t)/'page';subprocess.run(['pdftoppm','-singlefile','-r','300','-png',str(path),str(dst)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);return Image.open(dst.with_suffix('.png')).convert('RGB').tobytes()
 a,b=render(inp),render(out);assert a==b,renderer;checks.append({'case':'native-jpeg-passthrough','renderer':renderer,'pixel_identical':True,'input_bytes':inp.stat().st_size,'output_bytes':out.stat().st_size,'image_encoded_bytes':len(data),'source_stream_unchanged':True,'note':'JPEG import control made from genuine receipt imagery; not added to the frozen corpus'})
# Unsupported page geometry must route through Poppler rather than copying
# an image with an incompatible transform/clip.
geometry=pikepdf.Pdf.new()
for rotation in [0,90]:
 geometry.pages.append(source.pages[0]);g=geometry.pages[-1];width,height=map(float,g.MediaBox[2:]);g.CropBox=pikepdf.Array([12,24,width-12,height-24]);g.Rotate=rotation
inp=D/'geometry-input.pdf';out=D/'geometry-output.pdf';geometry.save(inp,deterministic_id=True);subprocess.run([exe,str(inp),str(out),'--dpi','72'],check=True,env=dict(os.environ,OMP_THREAD_LIMIT='1'),stdout=subprocess.DEVNULL);r=json.loads(Path(str(out)+'.json').read_text());assert all(x['raster_import']=='Poppler' for x in r['pages']);sizes=[tuple(p.get_size()) for p in pdfium.PdfDocument(str(out))];expected=[(width-24,height-48),(height-48,width-24)];assert all(max(abs(a-b) for a,b in zip(s,e))<.001 for s,e in zip(sizes,expected));checks.append({'case':'crop-rotation-fallback','sizes':sizes,'expected':expected,'native_copy_rejected':True})
(B/'workflow-controls.json').write_text(json.dumps(checks,indent=2));print('PASS',checks)
