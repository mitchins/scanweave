"""Native PDFium search of numerical strings emitted from supplied OCR."""
from pathlib import Path
import json,re,collections,xml.etree.ElementTree as ET
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;rows=[]
for r in json.loads((B/'final/metrics.json').read_text()):
 if not r['name'].startswith('cord-'):continue
 doc=pdfium.PdfDocument(B/'final'/(r['name']+'.pdf'));t=doc[0].get_textpage();ocr=B.parents[1]/'clearscan_competitive/real'/(r['name']+'.regions.hocr')
 root=ET.parse(ocr);words=[''.join(x.text or '' for x in w.iter() if x.attrib.get('class')=='ocrx_cinfo') for w in root.iter() if w.attrib.get('class')=='ocrx_word']
 tokens=sorted(set(x for word in words for x in re.findall(r'[-+]?\d[\d,.]*\d',word) if len(re.sub(r'\D','',x))>=3));tests=[]
 for token in tokens:
  search=t.search(token);tests.append({'token':token,'found':search.get_next() is not None})
 a=collections.Counter(re.sub(r'\s','',r['pdfium_text']));b=collections.Counter(re.sub(r'\s','',r['poppler_text']));rows.append({'name':r['name'],'numerical_queries':tests,'query_source':'original OCR word tokens, not renderer-inferred concatenations','poppler_only_contiguous_queries':[{'token':q,'native_found':t.search(q).get_next() is not None} for q in sorted(set(re.findall(r'[-+]?\d[\d,.]*\d',r['poppler_text']))-set(tokens)) if len(re.sub(r'\D','',q))>=3],'native_vs_poppler_extra_chars':dict(a-b),'native_vs_poppler_missing_chars':dict(b-a)})
(B/'financial-search.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False));print('queries',sum(len(r['numerical_queries']) for r in rows),'not found',[(r['name'],q['token']) for r in rows for q in r['numerical_queries'] if not q['found']])
