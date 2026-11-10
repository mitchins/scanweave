#!/usr/bin/env python3
"""Summarize frozen prior all-line measurements using the same quantiles as compare.py."""
import json,pathlib
import numpy as np
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'ink33r';old=R/'local/ink33/raw-chars'
def stats(vals):
 a=np.array([x for x in vals if x is not None and np.isfinite(x)],dtype=float)
 return {'n':int(a.size),'p10':float(np.percentile(a,10)),'p50':float(np.median(a)),'p90':float(np.percentile(a,90))} if a.size else None
for doc in ('historical','financial','mixed','receipts','forms'):
 lines=[x for p in sorted(E.glob(f'old-all-lines-{doc}-*.json')) for x in json.loads(p.read_text())['lines']];words=[x for l in lines for x in l['words']];chars=[x for p in sorted(old.glob(f'chars-{doc}-*.json')) for x in json.loads(p.read_text())];out={'document':doc,'lines':len(lines),'words':len(words),'characters':len(chars),'methods':{}}
 for method in ('source','scanweave','adobe'):
  v=[c for c in chars if c['measure']['source'] and c['measure'][method]]
  out['methods'][method]={'line_tone_iqr':stats([x['metrics'][method]['tone_iqr'] for x in lines]),'line_vector_raster_gap':stats([x['metrics'][method]['gap'] for x in lines]),'line_ssim':stats([x['metrics'][method]['ssim'] for x in lines]),'word_tone_iqr':stats([x['metrics'][method]['tone_iqr'] for x in words]),'word_vector_raster_gap':stats([x['metrics'][method]['gap'] for x in words]),'character_abs_tone_error':stats([abs(x['measure'][method]['tone']-x['measure']['source']['tone']) for x in v]),'character_signed_tone_error':stats([x['measure'][method]['tone']-x['measure']['source']['tone'] for x in v]),'character_coverage':stats([x['measure'][method]['density'] for x in v]),'character_edge':stats([x['measure'][method]['edge'] for x in v]),'character_roughness':stats([x['measure'][method]['roughness'] for x in v])}
 (E/f'old-all-summary-{doc}.json').write_text(json.dumps(out,indent=2)+'\n')
