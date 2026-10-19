"""Bind independent design review to final actual visible geometry."""
from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parent;rows=[]
for dpi in [300,600]:
 d=B/str(dpi);old=json.loads((d/'source-gate-trial/audit.json').read_text());new=json.loads((d/'final/audit.json').read_text());key=lambda r:(r['page'],r['symbol']);o={key(r):r for r in old['placements']};n={key(r):r for r in new['placements']}
 bad=[k for k in o if k not in n or any(o[k][v]!=n[k][v] for v in ['outline_hash','matrix','bbox_px'])]
 rows.append({'dpi':dpi,'earlier_pdf_sha256':hashlib.sha256((d/'source-gate-trial/final.pdf').read_bytes()).hexdigest(),'final_pdf_sha256':hashlib.sha256((d/'final.pdf').read_bytes()).hexdigest(),'earlier_occurrences':len(o),'final_occurrences':len(n),'changed_visible_outline_or_placement':bad,'all_visible_placements_identical':not bad and o.keys()==n.keys()})
assert rows[0]['all_visible_placements_identical']
(B/'geometry-binding.json').write_text(json.dumps(rows,indent=2))
