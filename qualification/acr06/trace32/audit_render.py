import sys,subprocess,tempfile
from pathlib import Path
engine,a,b=sys.argv[1:]; scales=(217.3,200,300,600)
if engine=='mupdf':
 import fitz
 docs=[fitz.open(n) for n in (a,b)]
 def render(d,i,dpi):
  p=d[i].get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=False,colorspace=fitz.csRGB)
  return (p.width,p.height,p.n,p.samples)
elif engine=='pdfium':
 import pypdfium2 as pdf
 docs=[pdf.PdfDocument(n) for n in (a,b)]
 def render(d,i,dpi):
  p=d[i].render(scale=dpi/72).to_pil().convert('RGB');return (*p.size,3,p.tobytes())
else:
 from PIL import Image
 docs=[a,b]
 def render(d,i,dpi):
  with tempfile.TemporaryDirectory() as td:
   prefix=str(Path(td)/'page');subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-singlefile','-r',str(dpi),'-png',d,prefix],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
   with Image.open(prefix+'.png') as p:
    p=p.convert('RGB');return (*p.size,3,p.tobytes())
if engine=='poppler':
 import re
 n=[int(re.search(r'^Pages:\s+(\d+)',subprocess.check_output(['pdfinfo',x],text=True),re.M).group(1)) for x in docs]
else:n=[len(d) for d in docs]
assert n[0]==n[1],n
for dpi in scales:
 for i in range(n[0]):
  x,y=[render(d,i,dpi) for d in docs]
  if x[:3]!=y[:3]:print('FAIL',engine,dpi,i+1,'size',x[:3],y[:3],flush=True);sys.exit(1)
  if x[3]!=y[3]:
   count=sum(x[3][j:j+3]!=y[3][j:j+3] for j in range(0,len(x[3]),3));print('FAIL',engine,dpi,i+1,'changed_pixels',count,flush=True);sys.exit(1)
  print('PASS',engine,dpi,i+1,flush=True)
