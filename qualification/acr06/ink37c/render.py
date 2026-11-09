from pathlib import Path
import sys,subprocess
engine=sys.argv[1];root=Path('/data/coding/scanweave/qualification/acr06/local/ink37c');out=root/'renders'/engine;out.mkdir(parents=True,exist_ok=True)
for doc,n in [('historical',2),('historical',5),('receipts',4)]:
 for dpi in (96,300):
  dst=out/f'{doc}-{n:02d}-{dpi}.png';pdf=root/f'{doc}.pdf'
  if engine=='pdfium':
   import pypdfium2 as p
   x=p.PdfDocument(pdf);page=x[n-1];page.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(dst);page.close();x.close()
  elif engine=='mupdf':
   import pymupdf as p
   x=p.open(pdf);x[n-1].get_pixmap(matrix=p.Matrix(dpi/72,dpi/72),alpha=False).save(dst);x.close()
  else:subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-singlefile','-r',str(dpi),'-png',str(pdf),str(dst.with_suffix(''))],check=True)
  print(engine,doc,n,dpi,flush=True)
