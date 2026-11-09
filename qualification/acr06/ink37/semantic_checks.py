from pathlib import Path
import pypdfium2 as pdfium
import pikepdf, hashlib, json, subprocess, os, re
root=Path('/data/coding/scanweave/qualification/acr06'); loc=root/'local/ink37'; rows=[]; env=dict(os.environ,LD_LIBRARY_PATH='/data/coding/scanweave/tools/dist/lib')
for doc in ('historical','financial','mixed','receipts','forms'):
 paths=[loc/f'{doc}-{arm}.pdf' for arm in ('main','candidate')]; pdfs=[pdfium.PdfDocument(p) for p in paths]
 for i in range(len(pdfs[0])):
  texts=[]; pops=[]
  for pdf,path in zip(pdfs,paths):
   page=pdf[i]; tp=page.get_textpage(); texts.append(tp.get_text_range()); tp.close(); page.close()
   pops.append(subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),'-enc','UTF-8',str(path),'-'],capture_output=True,check=True).stdout)
  terms=sorted(set(re.findall(r'[^\W_]+', texts[0], re.UNICODE)))
  searches=[]
  for pdf in pdfs:
   page=pdf[i]; tp=page.get_textpage(); counts={}
   for term in terms:
    finder=tp.search(term); matches=[]
    while (hit:=finder.get_next()) is not None: matches.append(hit)
    finder.close(); counts[term]=matches
   searches.append(counts); tp.close(); page.close()
  mismatches=[t for t in terms if searches[0][t]!=searches[1][t]]
  rows.append({'document':doc,'page':i+1,'search_terms':len(terms),'search_mismatches':mismatches,'pdfium_identical':texts[0]==texts[1],'pdfium_main_sha256':hashlib.sha256(texts[0].encode()).hexdigest(),'pdfium_candidate_sha256':hashlib.sha256(texts[1].encode()).hexdigest(),'poppler_identical':pops[0]==pops[1],'poppler_main_sha256':hashlib.sha256(pops[0]).hexdigest(),'poppler_candidate_sha256':hashlib.sha256(pops[1]).hexdigest()})
 for pdf in pdfs:pdf.close()
 for arm,p in zip(('main','candidate'),paths):
  c=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(p)],capture_output=True,text=True,env=env)
  rows.append({'document':doc,'arm':arm,'qpdf_exit':c.returncode,'qpdf_output':c.stdout+c.stderr})
  fonts={}
  with pikepdf.open(p) as pdf:
   for o in pdf.objects:
    try:
     for key in ('/FontFile','/FontFile2','/FontFile3'):
      if key in o:
       data=o[key].read_bytes(); fonts[hashlib.sha256(data).hexdigest()]=data
    except (ValueError, TypeError, AttributeError): pass
  for sha,data in fonts.items():
   path=loc/f'{sha}.font'; path.write_bytes(data)
   c=subprocess.run(['/data/coding/scanweave/tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(path)],capture_output=True,text=True)
   rows.append({'document':doc,'arm':arm,'font_sha256':sha,'ots_exit':c.returncode,'ots_output':c.stdout+c.stderr})
(root/'ink37/semantic-checks.json').write_text(json.dumps(rows,indent=2)+'\n')
