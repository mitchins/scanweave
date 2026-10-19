#!/usr/bin/env python3
"""Paired whole-document scorecard. Never normalizes candidates to oracle boxes."""
import json,statistics,hashlib,re
from pathlib import Path
from collections import defaultdict,Counter
B=Path(__file__).resolve().parent;out={}
def read(p):return json.loads(p.read_text())
def mean(v):return statistics.mean(v) if v else None
for dpi in [300,600]:
 b=B/str(dpi);metrics={a:read(b/a/'metrics.json') for a in ['adobe','previous','final']};rows={a:{(r['page'],r['id']):r for r in m['glyphs'] if r['geometry']=='exact' and r['text'].strip()} for a,m in metrics.items()};geo=read(b/'final-geometry.json')['summary'];table={}
 source=next(iter(rows.values()));bins={'damaged (source IoU < .90)':lambda x:x<.9,'moderate (.90 <= source < .97)':lambda x:.9<=x<.97,'healthy (source >= .97)':lambda x:x>=.97}
 for a,m in metrics.items():
  r=rows[a];table[a]={'bytes':m['bytes'],'sha256':m['sha256'],'font_bytes':m['streams'].get('font',0),'raster_bytes':m['streams'].get('raster',0),'pdfium_iou':m['isolated_summary']['exact']['pdfium'],'poppler_iou':m['isolated_summary']['exact']['poppler'],'search_matches_ocr':{k:m['search'][k] for k in ['poppler_matches_ocr','pdfium_matches_ocr']},'ink_area_bias':{ren:geo[a+'/'+ren]['mean_ink_area_bias'] for ren in ['poppler','pdfium']},'counter_mismatches':{ren:geo[a+'/'+ren]['counter_mismatches'] for ren in ['poppler','pdfium']},'strata':{}}
  for label,pred in bins.items():
   keys=[k for k,v in source.items() if pred(v['source_isolated'])];table[a]['strata'][label]={'n':len(keys),'source_iou':mean([source[k]['source_isolated'] for k in keys]),'pdfium_iou':mean([r[k]['pdfium_isolated'] for k in keys]),'poppler_iou':mean([r[k]['poppler_isolated'] for k in keys]),'improved_over_source':sum(r[k]['pdfium_isolated']>source[k]['source_isolated'] for k in keys),'regressed_from_source':sum(r[k]['pdfium_isolated']<source[k]['source_isolated'] for k in keys)}
 for a in ['previous','final']:
  report=read(b/(a+'.json'));audit=read(b/a/'audit.json');visible={(r['page'],r['symbol']) for r in audit['placements']};obs=[(pi,o) for pi,p in enumerate(report['page_reports']) for o in p['reconstruction']['observations']];occ=[(pi,o) for pi,p in enumerate(report['page_reports']) for o in p['reconstruction']['occurrences']];canonical=[(pi,o) for pi,o in occ if (pi,o['symbol_id']) in visible and (o['reused'] or o['repaired'])];fallback=[{'page':pi,**o} for pi,o in occ if (pi,o['symbol_id']) not in visible];table[a].update({'observations':len(obs),'visible_vector_occurrences':audit['painted_occurrences'],'painted_outlines':audit['distinct_painted_outline_hashes'],'assigned_canonical_identities':len({o['prototype_id'] for _,o in canonical}),'canonical_occurrences':len(canonical),'repaired_canonical_occurrences':sum(o['repaired'] for _,o in canonical),'wrong_witness_identity':audit['wrong_witness_identity'],'wrong_witness_typeface':audit['wrong_witness_typeface'],'raster_classes':audit['resource_bytes_by_class'],'stage_timings':report['stage_timings'],'ownership':report['coverage'],'fallback_occurrences':fallback})
  timed=b/(a+'-time.txt')
  if a=='previous':timed=B.parent/'clearscan_typography'/str(dpi)/'final-time.txt'
  if timed.exists():
   t=timed.read_text();table[a]['timing']={'wall':re.search(r'Elapsed \(wall clock\) time.*?: (\S+)',t).group(1),'peak_rss_kib':int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',t).group(1)),'user_seconds':float(re.search(r'User time \(seconds\): ([\d.]+)',t).group(1))}
 families=defaultdict(list)
 for key,r in source.items():families[(('kana' if ord(r['text'][0])>127 else 'italic' if key[0]>=6 else 'serif'),r['text'])].append(key)
 fam=[]
 for (style,ch),keys in families.items():
  z={'style':style,'text':ch,'n':len(keys),'source':mean(source[k]['source_isolated'] for k in keys)}
  for a in rows:z[a]={ren:mean(rows[a][k][ren+'_isolated'] for k in keys) for ren in ['pdfium','poppler']}
  z['pdfium_delta']=z['final']['pdfium']-z['previous']['pdfium'];fam.append(z)
 out[str(dpi)]={'n':len(source),'source_iou':metrics['final']['isolated_summary']['exact']['source'],'arms':table,'families':fam,'best_improvements':sorted(fam,key=lambda r:r['pdfium_delta'],reverse=True)[:10],'worst_improvements':sorted(fam,key=lambda r:r['pdfium_delta'])[:10]}
(B/'scorecard.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print(json.dumps({dpi:{a:{k:v for k,v in z.items() if k in ['bytes','font_bytes','raster_bytes','pdfium_iou','poppler_iou','observations','visible_vector_occurrences','assigned_canonical_identities','canonical_occurrences','painted_outlines']} for a,z in d['arms'].items()} for dpi,d in out.items()},indent=2))
