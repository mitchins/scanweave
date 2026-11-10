import json,sys,pathlib,hashlib,subprocess
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';L=R/'local/hvc41b';engine=sys.argv[1];path=L/'final/historical.pdf';out=L/'renders'/engine;out.mkdir(parents=True,exist_ok=True);rows=[]
if engine=='pdfium':import pypdfium2 as p;doc=p.PdfDocument(str(path))
if engine=='mupdf':import pymupdf as p;doc=p.open(path)
for page in (1,3,4):
 for dpi in (96,300):
  f=out/f'p{page:02}-{dpi}.png'
  if engine=='pdfium':
   pg=doc[page-1];im=pg.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB');im.save(f);width,height=im.size;pg.close()
  elif engine=='mupdf':
   pix=doc[page-1].get_pixmap(matrix=p.Matrix(dpi/72,dpi/72),alpha=False);pix.save(str(f));width,height=pix.width,pix.height
  else:
   stem=f.with_suffix('');subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile','-r',str(dpi),'-png',str(path),str(stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   from PIL import Image
   with Image.open(f) as im:width,height=im.size
  rows.append({'page':page,'dpi':dpi,'engine':engine,'file':str(f),'width':width,'height':height,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()});print(engine,page,dpi,flush=True)
if engine!='poppler':doc.close()
(E/f'render-{engine}.json').write_text(json.dumps(rows,indent=2)+'\n')
