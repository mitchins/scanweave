from pathlib import Path
import sys,subprocess,tempfile,json,hashlib
import numpy as np
engine=sys.argv[1]
if engine != "mupdf":
 from PIL import Image
base=Path('/data/coding/scanweave/qualification/acr06/local');rows=[]
for doc in (sys.argv[2:] or ('historical','financial','mixed','receipts','forms')):
 paths=[base/'ink33r'/f'{doc}.pdf',base/'hvc41/trial2'/f'{doc}.pdf'];equal=paths[0].read_bytes()==paths[1].read_bytes()
 if engine=='pdfium':
  import pypdfium2 as p
  pdfs=[p.PdfDocument(path) for path in paths];num=len(pdfs[0])
 elif engine=='mupdf':
  import pymupdf as p
  pdfs=[p.open(path) for path in paths];num=len(pdfs[0])
 else:
  import pypdfium2 as p
  pdfs=[p.PdfDocument(path) for path in paths];num=len(pdfs[0])
 with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
  for i in range(num):
   for dpi in (96,300):
    images=[]
    for j in range(1 if equal else 2):
     if engine=='pdfium':
      page=pdfs[j][i];im=page.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB');page.close()
     elif engine=='mupdf':
      pix=pdfs[j][i].get_pixmap(matrix=p.Matrix(dpi/72,dpi/72),alpha=False);im=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
     else:
      stem=Path(tmp)/f'{i}-{j}-{dpi}';subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-singlefile','-r',str(dpi),'-png',str(paths[j]),str(stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);im=Image.open(str(stem)+'.png').convert('RGB')
     images.append(np.asarray(im))
    if equal:images.append(images[0])
    r={'engine':engine,'document':doc,'page':i+1,'dpi':dpi,'shape_reference':images[0].shape,'shape_candidate':images[1].shape,'pdf_byte_identical':equal}
    if images[0].shape==images[1].shape:r['changed_pixels']=int(np.any(images[0]!=images[1],axis=2).sum())
    rows.append(r)
 for pdf in pdfs:pdf.close()
 print(engine,doc,flush=True)
Path('/data/coding/scanweave/qualification/acr06/hvc41/render-'+engine+'.json').write_text(json.dumps(rows,indent=2)+'\n')
