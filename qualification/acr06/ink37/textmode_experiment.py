from pathlib import Path
import pikepdf, pypdfium2 as pdfium, subprocess,json
root=Path('/data/coding/scanweave/qualification/acr06'); loc=root/'local/ink37'; original=loc/'historical-main.pdf'; output=loc/'historical-invisible-experiment.pdf'
with pikepdf.open(original) as doc:
 for page in doc.pages:
  ins=pikepdf.parse_content_stream(page); out=[]
  for inst in ins:
   if str(inst.operator)=='Tr' and int(inst.operands[0]) in (0,2,4,6): out.append(pikepdf.ContentStreamInstruction([3],pikepdf.Operator('Tr')))
   else: out.append(inst)
  page.Contents=doc.make_stream(pikepdf.unparse_content_stream(out))
 doc.save(output)
rows=[]; docs=[pdfium.PdfDocument(p) for p in (original,output)]
for i in range(len(docs[0])):
 texts=[]; pops=[]
 for pdf,p in zip(docs,(original,output)):
  pg=pdf[i]; tp=pg.get_textpage(); texts.append(tp.get_text_range());tp.close();pg.close()
  pops.append(subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(p),'-'],capture_output=True,check=True).stdout)
 rows.append({'page':i+1,'pdfium_identical':texts[0]==texts[1],'poppler_identical':pops[0]==pops[1]})
for pdf in docs:pdf.close()
(root/'ink37/textmode-semantics.json').write_text(json.dumps(rows,indent=2)+'\n')
