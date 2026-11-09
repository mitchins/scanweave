from pathlib import Path
import json,hashlib
root=Path('/data/coding/scanweave/qualification/acr06'); loc=root/'local/ink37'; out=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 p=loc/f'{doc}-candidate.pdf.json'
 if not p.exists(): continue
 a=json.loads((loc/f'{doc}-main.pdf.json').read_text()); b=json.loads(p.read_text())
 for ix,(x,y) in enumerate(zip(a['conversion']['page_reports'],b['conversion']['page_reports']),1):
  out.append({'document':doc,'page':ix,'fallback':y.get('colour_fallback'),'main_coverage':x['coverage'],'candidate_coverage':y['coverage'],'main_occurrences':len(x['occurrences']),'candidate_occurrences':len(y['occurrences']),'main_reasons':x['fallback_reasons'],'candidate_reasons':y['fallback_reasons'],'main_suppressed':x['raster_ink_pixels_suppressed'],'candidate_suppressed':y['raster_ink_pixels_suppressed']})
(root/'ink37/report-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
