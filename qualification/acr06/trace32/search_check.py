import pypdfium2 as pdf,sys,re,json,subprocess
paths=sys.argv[1:]; docs=[pdf.PdfDocument(n) for n in paths];assert len(docs[0])==len(docs[1]);results=[]
for i in range(len(docs[0])):
 pages=[d[i].get_textpage() for d in docs];texts=[p.get_text_range() for p in pages];assert texts[0]==texts[1]
 words=list(dict.fromkeys(w for w in re.findall(r'[^\W\d_]{4,}',texts[0],re.UNICODE)))[:3]
 for word in words:
  pairs=[]
  for p in pages:
   s=p.search(word,match_case=True);hits=[]
   while (hit:=s.get_next()) is not None:hits.append(hit)
   pairs.append(hits)
  assert pairs[0]==pairs[1] and pairs[0],(i,word,pairs)
  results.append({'page':i+1,'word':word,'hits':pairs[0]})
texts=[subprocess.check_output(['pdftotext','-raw',n,'-']) for n in paths];assert texts[0]==texts[1]
print(json.dumps(results,ensure_ascii=False))
