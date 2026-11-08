import fitz,sys
from pathlib import Path
root=Path('/data/coding/scanweave/qualification/acr06/local/trace32'); docs=[fitz.open(str(root/(n+'.pdf'))) for n in ('profile','experimental')]
assert len(docs[0])==len(docs[1])
for dpi in (217.3,200,300,600):
 for i in range(len(docs[0])):
  a,b=[d[i].get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=False,colorspace=fitz.csRGB) for d in docs]
  if (a.width,a.height,a.n)!=(b.width,b.height,b.n): print('FAIL',dpi,i+1,'size',flush=True);sys.exit(1)
  if a.samples!=b.samples:
   count=sum(a.samples[j:j+3]!=b.samples[j:j+3] for j in range(0,len(a.samples),3)); print('FAIL',dpi,i+1,'changed pixels',count,flush=True);sys.exit(1)
  print('PASS',dpi,i+1,flush=True)
