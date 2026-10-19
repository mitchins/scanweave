"""Same source samples as a full-page image vs native patch composition."""
import json,math,zlib,subprocess
from pathlib import Path
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1];rows=[]
for dpi in [300,600]:
 d=B/'hard-negative'/str(dpi);a=np.asarray(Image.open(d/'page00.png').convert('L'));o=np.asarray(Image.open(R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page00.png').convert('L'));mask=a!=o
 p=pikepdf.Pdf.new();pg=p.add_blank_page(page_size=(432,216));x=pikepdf.Stream(p,zlib.compress(a.tobytes(),9));x.Type=pikepdf.Name.XObject;x.Subtype=pikepdf.Name.Image;x.Width=a.shape[1];x.Height=a.shape[0];x.ColorSpace=pikepdf.Name.DeviceGray;x.BitsPerComponent=8;x.Filter=pikepdf.Name.FlateDecode;x.Interpolate=False;pg.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=x));pg.Contents=pikepdf.Stream(p,b'q 432 0 0 216 0 0 cm /Im0 Do Q');p.save(d/'source-raster.pdf')
 q=pikepdf.open(d/'final.pdf');inside=False;ops=[]
 for i in pikepdf.parse_content_stream(q.pages[0]):
  op=str(i.operator)
  if op=='BT':inside=True
  if not inside:ops.append(i)
  if op=='ET':inside=False
 q.pages[0].Contents=pikepdf.Stream(q,pikepdf.unparse_content_stream(ops));q.save(d/'native-background.pdf')
 for arm in ['source-raster','native-background','final']:
  path=d/(arm+'.pdf')
  for renderer in ['pdfium','poppler']:
   if renderer=='pdfium':im=pdfium.PdfDocument(path)[0].render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L')
   else:
    subprocess.run(['pdftoppm','-singlefile','-r',str(dpi),'-gray','-png',str(path),str(d/(arm+'-poppler'))],check=True,capture_output=True);im=Image.open(d/(arm+'-poppler.png')).convert('L')
   r=np.asarray(im);im.save(d/(arm+'-'+renderer+'.png'));delta=r[mask].astype(float)-a[mask];rows.append({'dpi':dpi,'arm':arm,'renderer':renderer,'source_pixels':int(mask.sum()),'mean_luma':float(r[mask].mean()),'mean_absolute_sample_error':float(abs(delta).mean()),'max_lightening':float(delta.max()),'max_darkening':float(-delta.min()),'samples_lighter_than_252':int((r[mask]>252).sum())})
(B/'patch-sampling-control.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
