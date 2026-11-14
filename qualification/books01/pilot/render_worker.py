#!/usr/bin/env python3
"""One renderer/page/resolution per process: warm once, measure five runs."""
import json, pathlib, resource, subprocess, sys, time
from PIL import Image
pdf,renderer,dpi,out=sys.argv[1],sys.argv[2],int(sys.argv[3]),pathlib.Path(sys.argv[4]); out.parent.mkdir(parents=True,exist_ok=True); samples=[]
if renderer=='pdfium':
 import pypdfium2 as p
 doc=p.PdfDocument(pdf);page=doc[0]
 def render():return page.render(scale=dpi/72).to_pil().convert('RGB')
elif renderer=='mupdf':
 import fitz
 doc=fitz.open(pdf);page=doc[0]
 def render():
  x=page.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=False,colorspace=fitz.csRGB);return Image.frombytes('RGB',[x.width,x.height],x.samples)
elif renderer=='poppler':
 def render():
  cmd=['/usr/bin/pdftoppm','-cropbox','-f','1','-l','1','-singlefile','-r',str(dpi),'-png',pdf,str(out.with_suffix(''))];p=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
  return None
else:raise ValueError(renderer)
render()
for i in range(5):
 start=time.perf_counter(); im=render();samples.append(time.perf_counter()-start)
if im is not None:im.save(out)
r=resource.getrusage(resource.RUSAGE_SELF);c=resource.getrusage(resource.RUSAGE_CHILDREN); s=sorted(samples)
print(json.dumps({'samples_seconds':samples,'median_seconds':s[2],'p95_seconds':s[-1],'p95_method':'nearest-rank n=5','peak_rss_kib':max(r.ru_maxrss,c.ru_maxrss),'peak_rss_scope':'render worker and largest child, includes interpreter','output':str(out),'output_bytes':out.stat().st_size}))
