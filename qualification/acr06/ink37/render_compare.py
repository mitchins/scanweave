from pathlib import Path
import sys, subprocess
engine=sys.argv[1]
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37'); out=root/'three-engine'/engine; out.mkdir(parents=True,exist_ok=True)
docs = [sys.argv[2]] if len(sys.argv) > 2 else ('historical','financial','mixed','receipts','forms')
for doc in docs:
 for arm in ('main','candidate'):
  path=root/f'{doc}-{arm}.pdf'; target=out/doc; target.mkdir(exist_ok=True)
  if engine=='poppler':
   subprocess.run(['pdftoppm','-r','300','-png',str(path),str(target/arm)],check=True)
  elif engine=='pdfium':
   import pypdfium2
   pdf=pypdfium2.PdfDocument(path)
   for i in range(len(pdf)):
    page=pdf[i]; page.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB').save(target/f'{arm}-{i+1:02d}.png'); page.close()
   pdf.close()
  elif engine=='mupdf':
   import pymupdf
   pdf=pymupdf.open(path)
   for i,p in enumerate(pdf):p.get_pixmap(matrix=pymupdf.Matrix(300/72,300/72),alpha=False).save(target/f'{arm}-{i+1:02d}.png')
   pdf.close()
  else: raise ValueError(engine)
  print(engine,doc,arm,flush=True)
