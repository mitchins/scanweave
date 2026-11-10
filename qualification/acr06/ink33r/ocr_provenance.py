#!/usr/bin/env python3
"""Compare OCR text and geometry independently of volatile hOCR metadata."""
import hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');out=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 old=R/('local/ink33/forms-main.pdf.json' if doc=='forms' else f'local/bg150/baseline/{doc}.pdf.json');new=R/f'local/ink33r/{doc}.pdf.json';a=json.loads(old.read_text());b=json.loads(new.read_text())
 for n,(x,y) in enumerate(zip(a['pages'],b['pages']),1):
  f=lambda s:hashlib.sha256(s.encode()).hexdigest();v=chars_from_hocr(x['hocr']);w=chars_from_hocr(y['hocr']);out.append({'document':doc,'page':n,'old_hocr_sha256':f(x['hocr']),'new_hocr_sha256':f(y['hocr']),'parsed_text_boxes_equal':v==w,'old_parsed_sha256':f(json.dumps(v,sort_keys=True)),'new_parsed_sha256':f(json.dumps(w,sort_keys=True))})
(R/'ink33r/ocr-provenance.json').write_text(json.dumps(out,indent=2)+'\n')
print('changed parsed OCR pages:',[(r['document'],r['page']) for r in out if not r['parsed_text_boxes_equal']])
