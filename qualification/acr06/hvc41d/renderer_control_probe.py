import pathlib,subprocess,json,math,numpy as np,pypdfium2 as pdfium
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';inputs=[R/'local/hvc41b/controls/control/white/baseline.pdf',L/'patch-control.pdf'];out={}
for dpi in [96,300]:
 for renderer in ['pdfium','poppler','mupdf']:
  imgs=[]
  for k,p in enumerate(inputs):
   dest=L/f'probe-{renderer}-{dpi}-{k}.png'
   if renderer=='pdfium':
    d=pdfium.PdfDocument(str(p));pg=d[0];im=pg.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB');pg.close();d.close();im.save(dest)
   elif renderer=='poppler':subprocess.run(['pdftoppm','-f','1','-l','1','-r',str(dpi),'-png','-singlefile',str(p),str(dest.with_suffix(''))],check=True)
   else:
    code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[0].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])'
    subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(p),str(dest),str(dpi)],check=True)
   imgs.append(np.asarray(Image.open(dest).convert('RGB')))
  if imgs[0].shape!=imgs[1].shape:raise ValueError('geometry mismatch')
  diff=np.any(imgs[0]!=imgs[1],axis=2);h,w=diff.shape; a,b,c,d=718,359,746,396
  # conservative 3 source-pixel ownership envelope and one renderer pixel for antialiasing
  x0=max(0,math.floor((a-3)*dpi/300)-1);y0=max(0,math.floor((b-3)*dpi/300)-1);x1=min(w,math.ceil((c+3)*dpi/300)+1);y1=min(h,math.ceil((d+3)*dpi/300)+1);outside=diff.copy();outside[y0:y1,x0:x1]=False
  out[f'{renderer}-{dpi}']={'changed_pixels':int(diff.sum()),'outside_envelope_pixels':int(outside.sum()),'envelope_render_px':[x0,y0,x1,y1]}
  print(renderer,dpi,out[f'{renderer}-{dpi}'],flush=True)
(E/'renderer-control-probe.json').write_text(json.dumps(out,indent=2)+'\n')
