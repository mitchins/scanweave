"""Paired same-position vertical-stem intervals; unmatched intervals reported separately."""
import json,statistics
from pathlib import Path
B=Path(__file__).resolve().parent;out={}
for dpi in [300,600]:
 d=json.loads((B/f'design-geometry-{dpi}-representative.json').read_text());maps={}
 for a in d['details']:
  rows={}
  for r in a['occurrences']:
   for s in r['stem_widths']['errors_px']:
    key=(r['page'],r['symbol'],s['y_px'],*(round(x,6) for x in s['source_interval_px']));rows[key]=s['signed_width_error_px']
  maps[a['arm']]=rows
 common=set.intersection(*(set(x) for x in maps.values()));out[str(dpi)]={'common_intervals':len(common),'source_units':'pixels at stated scan DPI','arms':{}}
 for arm,m in maps.items():
  errors=[m[k] for k in common];out[str(dpi)]['arms'][arm]={'available_intervals':len(m),'unpaired_intervals':len(set(m)-common),'mean_signed_error_px':statistics.mean(errors),'mean_absolute_error_px':statistics.mean(abs(e) for e in errors),'error_std_px':statistics.pstdev(errors)}
(B/'paired-widths.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
