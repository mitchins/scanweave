from pathlib import Path
import pypdfium2 as pdfium, subprocess,json
root=Path('/data/coding/scanweave/qualification/acr06'); loc=root/'local/ink37'; rows=[]
for doc in ('historical','financial'):
 paths=[loc/f'{doc}-{arm}.pdf' for arm in ('main','occurrence')]
 if not all(p.exists() for p in paths):continue
 pdfs=[pdfium.PdfDocument(p) for p in paths]
 for i in range(len(pdfs[0])):
  texts=[]; pops=[]
  for pdf,p in zip(pdfs,paths):
   page=pdf[i]; tp=page.get_textpage(); texts.append(tp.get_text_range()); tp.close(); page.close()
   pops.append(subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),'-enc','UTF-8',str(p),'-'],capture_output=True,check=True).stdout)
  rows.append({'document':doc,'page':i+1,'pdfium_identical':texts[0]==texts[1],'poppler_identical':pops[0]==pops[1]})
 for pdf in pdfs:pdf.close()
(root/'ink37/occurrence-semantics.json').write_text(json.dumps(rows,indent=2)+'\n')
