#!/usr/bin/env python3
"""Compare frozen #33 mixed-line statistics and summarize all new usable lines.

Classification and metrics are produced by measure.py; original and new
mixed-line populations differ, so the comparison does not imply pairing.
"""
import collections,json,pathlib
import numpy as np
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');old=R/'ink33';new=R/'ink33r';local=R/'local/ink33r'; docs=('historical','financial','mixed','receipts','forms');methods=('source','scanweave','adobe','a','b','c')
def stats(v):
 a=np.array([x for x in v if x is not None and np.isfinite(x)],dtype=float)
 return {'n':int(a.size),'p10':float(np.percentile(a,10)),'p50':float(np.median(a)),'p90':float(np.percentile(a,90))} if a.size else None
comparison={}
for doc in docs:
 if not (new/f'summary-{doc}.json').exists(): continue
 prev=json.loads((old/f'summary-{doc}.json').read_text()); now=json.loads((new/f'summary-{doc}.json').read_text()); op=json.loads((old/f'prepare-{doc}.json').read_text());npages=json.loads((new/f'prepare-{doc}.json').read_text())
 comparison[doc]={'old_mixed_lines':prev['mixed_lines'],'new_mixed_lines':now['mixed_lines'],'old_mixed_words':prev['mixed_words'],'new_mixed_words':now['mixed_words'],'old_scan_vector_coverage':prev['scan_vector_coverage_on_measured_chars'],'new_scan_vector_coverage':now['scan_vector_coverage_on_measured_chars'],'old_visible_by_page':[x['scan_visible'] for x in op],'new_visible_by_page':[x['scan_visible'] for x in npages],'old_metrics':prev['metrics'],'new_metrics':now['metrics']}
 lines=[line for path in sorted(new.glob(f'all-lines-{doc}-*.json')) for line in json.loads(path.read_text())['lines']];words=[word for line in lines for word in line['words']]; chars=[c for path in sorted((local/'raw-chars').glob(f'chars-{doc}-*.json')) for c in json.loads(path.read_text())]
 sums={'document':doc,'lines':len(lines),'words':len(words),'characters':len(chars),'classes':dict(collections.Counter(c['class'] for c in chars)),'methods':{}}
 for name in methods:
  valid=[c for c in chars if c['measure']['source'] and c['measure'][name]]
  sums['methods'][name]={'line_tone_iqr':stats([x['metrics'][name]['tone_iqr'] for x in lines]),'line_vector_raster_gap':stats([x['metrics'][name]['gap'] for x in lines]),'line_ssim':stats([x['metrics'][name]['ssim'] for x in lines]),'word_tone_iqr':stats([x['metrics'][name]['tone_iqr'] for x in words]),'word_vector_raster_gap':stats([x['metrics'][name]['gap'] for x in words]),'character_abs_tone_error':stats([abs(x['measure'][name]['tone']-x['measure']['source']['tone']) for x in valid]),'character_signed_tone_error':stats([x['measure'][name]['tone']-x['measure']['source']['tone'] for x in valid]),'character_coverage':stats([x['measure'][name]['density'] for x in valid]),'character_edge':stats([x['measure'][name]['edge'] for x in valid]),'character_roughness':stats([x['measure'][name]['roughness'] for x in valid])}
 (new/f'all-summary-{doc}.json').write_text(json.dumps(sums,indent=2)+'\n')
(new/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
