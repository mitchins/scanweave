"""Native positional and stream text-order checks against supplied OCR."""
from pathlib import Path
import json,re,subprocess,hashlib
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[1];rows=[];norm=lambda s:re.sub(r'\s+','',s)
for dpi in [300,600]:
 base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input';m=json.loads((base/'document.json').read_text())
 for arm in ['previous','final']:
  p=B/str(dpi)/(arm+'.pdf');doc=pdfium.PdfDocument(p)
  for pi,page in enumerate(m['pages']):
   o=json.loads((base/page['ocr_page_path']).read_text());spans={s['id']:s['text'] for s in o['spans']};expected=norm(''.join(spans[s] for s in o['reading_order']))
   text={opt:subprocess.check_output(['pdftotext','-f',str(pi+1),'-l',str(pi+1),opt,str(p),'-'],text=True) for opt in ['-raw','-layout']}
   text['pdfium']=doc[pi].get_textpage().get_text_range()
   row={'dpi':dpi,'arm':arm,'page':pi,'pdf_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nonspace_chars':len(expected),'matches_supplied_ocr':{k:norm(t)==expected for k,t in text.items()}};rows.append(row)
assert all(all(r['matches_supplied_ocr'].values()) for r in rows if r['arm']=='final'),[r for r in rows if r['arm']=='final' and not all(r['matches_supplied_ocr'].values())]
(B/'text-order.json').write_text(json.dumps({'method':__doc__,'pages':rows},indent=2));print('final raw/layout/PDFium order matches supplied OCR on all16pages')
