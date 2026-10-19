"""Native PDFium search of numerical strings emitted from supplied OCR."""
from pathlib import Path
import json,re,collections
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;rows=[]
for r in json.loads((B/'final/metrics.json').read_text()):
 if not r['name'].startswith('cord-'):continue
 doc=pdfium.PdfDocument(B/'final'/(r['name']+'.pdf'));t=doc[0].get_textpage();tokens=sorted(set(x for x in re.findall(r'[-+]?\d[\d,.]*\d',r['poppler_text']) if len(re.sub(r'\D','',x))>=3));tests=[]
 for token in tokens:
  search=t.search(token);tests.append({'token':token,'found':search.get_next() is not None})
 a=collections.Counter(re.sub(r'\s','',r['pdfium_text']));b=collections.Counter(re.sub(r'\s','',r['poppler_text']));rows.append({'name':r['name'],'numerical_queries':tests,'native_vs_poppler_extra_chars':dict(a-b),'native_vs_poppler_missing_chars':dict(b-a)})
(B/'financial-search.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False));print('queries',sum(len(r['numerical_queries']) for r in rows),'not found',[(r['name'],q['token']) for r in rows for q in r['numerical_queries'] if not q['found']])
