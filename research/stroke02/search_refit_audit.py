"""Compare literal PDFium search on fixed, locally sampled OCR words.

Only counts and query indexes are published; OCR text stays local.
"""
import hashlib,json,pathlib,random
from lxml import html
import pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01');R=B/'stroke02/pages-refit';Q=pathlib.Path('/tmp/scanweave-books01/qualification/books01/corpus.frozen.json');out=[]
for page in json.loads(Q.read_text())['pages']:
 if page['split']!='dev':continue
 key=page['id'].split('/')[-1];d=R/key;metrics=json.loads((d/'metrics.json').read_text())
 if metrics['status']!=0:out.append({'id':page['id'],'status':metrics['status']});continue
 run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());doc=html.parse(str(B/'phase2/runs'/key/'selected.hocr'));words=[];seen=set()
 for word in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
  chars=word.xpath(".//span[@class='ocrx_cinfo']");value=''.join(node.text_content() for node in chars) if chars else ''.join(word.itertext()).strip()
  if len(value)>=4 and not any(c in value for c in ('\ufffe','\ufffd')) and value.casefold() not in seen:seen.add(value.casefold());words.append(value)
 seed=int.from_bytes(hashlib.sha256(page['id'].encode()).digest()[:8],'big');random.Random(seed).shuffle(words);words=words[:20]
 def search(path):
  pdf=pdfium.PdfDocument(str(path));text=pdf[0].get_textpage();return [text.search(w,match_case=False).get_next() is not None for w in words]
 a=search(run['rows']['sw-E']['path']);b=search(d/'candidate.pdf');out.append({'id':page['id'],'queries':len(words),'baseline_hits':sum(a),'candidate_hits':sum(b),'lost_query_indices':[i for i,(x,y) in enumerate(zip(a,b)) if x and not y],'gained_query_indices':[i for i,(x,y) in enumerate(zip(a,b)) if y and not x]})
pathlib.Path(__file__).with_name('search-refit-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'pages':len(out),'queries':sum(x.get('queries',0) for x in out),'baseline_hits':sum(x.get('baseline_hits',0) for x in out),'candidate_hits':sum(x.get('candidate_hits',0) for x in out),'lost':sum(len(x.get('lost_query_indices',[])) for x in out),'gained':sum(len(x.get('gained_query_indices',[])) for x in out)},indent=2))
