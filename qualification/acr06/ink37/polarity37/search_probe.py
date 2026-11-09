from pathlib import Path
import pypdfium2 as pdfium,re,json
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37')
rows=[]
for doc in ('historical','receipts'):
 pdfs=[pdfium.PdfDocument(root/f'polarity37/{doc}-main.pdf'),pdfium.PdfDocument(root/f'gate37/{doc}-candidate.pdf')]
 for i in range(len(pdfs[0])):
  pages=[pdf[i] for pdf in pdfs];tps=[p.get_textpage() for p in pages]; terms=sorted(set(re.findall(r'[^\W_]+',tps[0].get_text_range(),re.UNICODE)))
  diffs=[]
  for term in terms:
   hits=[]
   for tp in tps:
    f=tp.search(term); found=[]
    while (v:=f.get_next()) is not None:found.append(v)
    f.close(); hits.append(found)
   if hits[0]!=hits[1]:diffs.append({'term':term,'main':hits[0],'candidate':hits[1]})
  rows.append({'document':doc,'page':i+1,'terms':len(terms),'mismatches':diffs})
  for t in tps:t.close()
  for p in pages:p.close()
 for p in pdfs:p.close()
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/baseline-search-probe.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
for row in rows:print(row['document'],row['page'],row['terms'],len(row['mismatches']),row['mismatches'][:2])
