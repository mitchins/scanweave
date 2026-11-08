#!/usr/bin/env python3
import sys
from pathlib import Path
from PIL import ImageChops
root=Path('/data/coding/scanweave/qualification/acr06/local/trace32'); engine=sys.argv[1]
if engine=='pdfium':
 import pypdfium2 as pdf
 docs=[pdf.PdfDocument(str(root/(n+'.pdf'))) for n in ('profile','experimental')]
 def render(d,i,dpi): return d[i].render(scale=dpi/72).to_pil().convert('RGB')
else:
 import fitz
 docs=[fitz.open(str(root/(n+'.pdf'))) for n in ('profile','experimental')]
 def render(d,i,dpi):
  from PIL import Image
  p=d[i].get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=False,colorspace=fitz.csRGB)
  return Image.frombytes('RGB',(p.width,p.height),p.samples)
assert len(docs[0])==len(docs[1])
for dpi in (217.3,200,300,600):
 for i in range(len(docs[0])):
  a,b=[render(d,i,dpi) for d in docs]
  if a.size!=b.size: print('FAIL',engine,dpi,i+1,'size',a.size,b.size,flush=True);sys.exit(1)
  diff=ImageChops.difference(a,b); box=diff.getbbox()
  if box: print('FAIL',engine,dpi,i+1,'bbox',box,'changed pixels',sum(1 for p in diff.getdata() if p!=(0,0,0)),flush=True);sys.exit(1)
  print('PASS',engine,dpi,i+1,flush=True)
