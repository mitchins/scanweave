"""Compare completed candidate with baseline in three renderers at 96/300 dpi."""
import pathlib,subprocess,sys,json,math,numpy as np,pypdfium2 as pdfium
from PIL import Image
from scipy.ndimage import binary_dilation
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';inputs=[R/'local/ink33r/historical.pdf',L/'historical-rejected-243.pdf'];results=[];foot=np.asarray(Image.open(L/'p1-footprint-243.png').convert('L'))>0
for dpi in [96,300]:
 for engine in ['pdfium','poppler','mupdf']:
  for page in range(1,6):
   imgs=[]
   for tag,path in zip(['baseline','candidate'],inputs):
    dest=L/'renders'/f'{engine}-{dpi}-{page:02}-{tag}.png';dest.parent.mkdir(exist_ok=True)
    if engine=='pdfium':
     doc=pdfium.PdfDocument(str(path));pg=doc[page-1];im=pg.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB');pg.close();doc.close();im.save(dest)
    elif engine=='poppler':subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-r',str(dpi),'-png','-singlefile',str(path),str(dest.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
    else:
     code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[int(sys.argv[4])-1].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])'
     subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(dest),str(dpi),str(page)],check=True)
    imgs.append(np.asarray(Image.open(dest).convert('RGB')))
   if imgs[0].shape!=imgs[1].shape:raise SystemExit(f'geometry mismatch {engine} {page} {dpi}')
   diff=np.any(imgs[0]!=imgs[1],axis=2);outside=None;raw=None
   if page==1:
    mh,mw=diff.shape;mask=np.asarray(Image.fromarray(foot).resize((mw,mh),Image.Resampling.NEAREST));raw=int((diff&~mask).sum());envelope=binary_dilation(mask,iterations=2);outside=int((diff&~envelope).sum())
   results.append({'engine':engine,'dpi':dpi,'page':page,'changed_pixels':int(diff.sum()),'outside_exact_raster_mask':raw,'outside_2px_render_envelope':outside});print(results[-1],flush=True)
(E/'render-diffs.json').write_text(json.dumps(results,indent=2)+'\n')
