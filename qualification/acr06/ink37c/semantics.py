from pathlib import Path
import pypdfium2 as pdfium,subprocess,json,re,hashlib
base=Path('/data/coding/scanweave/qualification/acr06/local');rows=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 paths=[base/'ink37/owner37'/f'{doc}.pdf',base/'ink37c'/f'{doc}.pdf']
 if not paths[1].exists():continue
 pdfs=[pdfium.PdfDocument(p) for p in paths]
 for i in range(len(pdfs[0])):
  texts=[];pop=[];counts=[]
  for pdf,path in zip(pdfs,paths):
   p=pdf[i];tp=p.get_textpage();texts.append(tp.get_text_range());terms=sorted(set(re.findall(r'[^\W_]+',texts[0],re.UNICODE)));hits={}
   for term in terms:
    f=tp.search(term);v=[]
    while (hit:=f.get_next()) is not None:v.append(hit)
    f.close();hits[term]=v
   counts.append(hits);tp.close();p.close();pop.append(subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(path),'-'],capture_output=True,check=True).stdout)
  rows.append({'document':doc,'page':i+1,'pdfium_equal':texts[0]==texts[1],'poppler_equal':pop[0]==pop[1],'search_equal':counts[0]==counts[1],'text_sha256':[hashlib.sha256(x.encode()).hexdigest() for x in texts]})
 for p in pdfs:p.close()
 print(doc,flush=True)
Path('/data/coding/scanweave/qualification/acr06/ink37c/semantics.json').write_text(json.dumps(rows,indent=2)+'\n')
