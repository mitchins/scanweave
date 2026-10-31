"""Add aggregate verdict and totals to completed R2c reports."""
import json
from pathlib import Path
B=Path(__file__).resolve().parent
p=B/'r2c-pristine.json';j=json.loads(p.read_text());j['preregistered_verdict']='PASS' if all(v['pass'] for v in j['classes'].values()) else 'FAIL';j['class_verdict_by_renderer']={engine:('PASS' if all(v['pass'] for k,v in j['classes'].items() if k.endswith('|'+engine)) else 'FAIL') for engine in ('pdfium','poppler')};p.write_text(json.dumps(j,indent=2)+'\n')
p=B/'r2c-economy.json';j=json.loads(p.read_text());j['totals']={a:{k:sum(s['arms'][a].get(k) or 0 for s in j['sheets']) for k in ('substituted','retired_outlines','added_canonicals','net_outlines_retired','encoded_font_bytes_actual','pdf_bytes')} for a in ('off','cover-2.0','cover-2.0-ceiling')};p.write_text(json.dumps(j,indent=2)+'\n')
