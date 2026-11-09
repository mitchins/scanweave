from pathlib import Path
import sys,subprocess
engine=sys.argv[1];base=Path('/data/coding/scanweave/qualification/acr06');out=base/'local/ink37/owner37/source-render'/engine;out.mkdir(parents=True,exist_ok=True)
for doc,n in (('historical',2),('historical',5),('receipts',4)):
 source=Path('/data/coding/scanweave/qualification/pdf_packaging/groups')/f'{doc}-input.pdf';candidate=base/'local/ink37/owner37'/f'{doc}.pdf'
 for dpi in (96,300):
  for arm,path in (('source',source),('candidate',candidate)):
   dest=out/f'{doc}-{n:02}-{dpi}-{arm}.png'
   if engine=='pdfium':
    import pypdfium2 as p
    pdf=p.PdfDocument(path);page=pdf[n-1];page.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(dest);page.close();pdf.close()
   elif engine=='mupdf':
    import pymupdf as p
    pdf=p.open(path);pdf[n-1].get_pixmap(matrix=p.Matrix(dpi/72,dpi/72),alpha=False).save(dest);pdf.close()
   else:
    stem=dest.with_suffix('');subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-singlefile','-r',str(dpi),'-png',str(path),str(stem)],check=True)
  print(engine,doc,n,dpi,flush=True)
