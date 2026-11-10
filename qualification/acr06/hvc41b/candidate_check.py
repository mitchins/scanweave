import pathlib,json,hashlib,subprocess,re
import pypdfium2 as pdfium,pypdfium2.raw as raw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';L=R/'local/hvc41b';paths=[R/'local/ink33r/historical.pdf',L/'final/historical.pdf'];hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths];docs=[pdfium.PdfDocument(str(p)) for p in paths];rows=[]
for i in range(len(docs[0])):
 pages=[d[i] for d in docs];texts=[];vis=[];search=[]
 for pg in pages:
  tp=pg.get_textpage();txt=tp.get_text_range();texts.append(txt);vis.append(sum(1 for o in pg.get_objects() if o.type==raw.FPDF_PAGEOBJ_TEXT and raw.FPDFTextObj_GetTextRenderMode(o.raw) in (0,2,4,6)));word=next((w for w in re.findall(r'[^\W\d_]{4,}',txt) if len(w)>=4),None);st=tp.search(word) if word else None;search.append({'word':word,'found':st.get_next() is not None if st else None});
  if st:st.close()
  tp.close()
 pops=[subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(path),'-'],stdout=subprocess.PIPE,check=True).stdout for path in paths];rows.append({'page':i+1,'visible_text_objects_baseline_candidate':vis,'pdfium_extraction_identical':texts[0]==texts[1],'poppler_extraction_identical':pops[0]==pops[1],'pdfium_search':search,'pdfium_search_identical':search[0]==search[1]})
 for p in pages:p.close()
for d in docs:d.close()
(E/'candidate-check.json').write_text(json.dumps({'files':[str(x) for x in paths],'sha256':hashes,'byte_identical':hashes[0]==hashes[1],'pages':rows},indent=2,ensure_ascii=False)+'\n');print('identical',hashes[0]==hashes[1]);print(rows)
