"""Collect existing measurements; no additional image matching."""
from pathlib import Path
import json,hashlib,re
B=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
resources=json.loads((B/'resources.json').read_text());bg=json.loads((B/'background-metrics.json').read_text());rows=[]
for dpi in [300,600]:
 row={'dpi':dpi,'arms':{}}
 for arm in ['previous','final','adobe']:
  d=B/str(dpi);m=json.loads((d/arm/'metrics.json').read_text());a=json.loads((d/arm/'audit.json').read_text());r=next(r for r in resources['documents'] if r['dpi']==dpi and r['arm']==arm);assert sha(d/(arm+'.pdf'))==m['sha256']==r['accounting']['sha256']
  v={'pdf_bytes':m['bytes'],'sha256':m['sha256'],'stream_bytes':m['streams'],'glyph_iou':m['isolated_summary']['exact'],'vector_occurrences':a['painted_occurrences'],'distinct_painted_outlines':a['distinct_painted_outline_hashes'],'resource_class_bytes':r['resource_class_bytes'],'background':{x['renderer']:x for x in bg if x['dpi']==dpi and x['arm']==arm},'search':{k:v for k,v in m['search'].items() if k.endswith('_matches_ocr')}}
  if arm!='adobe':
   report=json.loads((d/(arm+'.json')).read_text());prs=report['page_reports'];v['observations']=sum(len(p['reconstruction']['observations']) for p in prs);v['accepted_canonical_ids']=len({o['prototype_id'] for p in prs for o in p['reconstruction']['occurrences'] if o['repaired'] or o['reused']});v['canonical_replacements']=sum(o['repaired'] or o['reused'] for p in prs for o in p['reconstruction']['occurrences']);v['source_mask_pixels_superseded']=sum(p['raster_ink_pixels_suppressed'] for p in prs);v['additional_bright_samples_superseded']=sum(p['antialias_fringe_pixels_suppressed'] for p in prs)
   v['same_font_as_previous']=r.get('same_font_program_as_previous');v['same_text_placements_as_previous']=r.get('same_text_and_placements_as_previous')
   if arm=='final':v['vector_to_final_iou_loss']=-json.loads((d/'final/stages/stage-errors.json').read_text())['means']['composition_delta']
  row['arms'][arm]=v
 rows.append(row)
text=(B/'workspace-tests.log').read_text();count=sum(map(int,re.findall(r'test result: ok\. (\d+) passed',text)));assert count==93 and 'FAILED' not in text
result={'documents':rows,'selected_page':json.loads((B/'stage-a/measurements.json').read_text()),'hard_negative':json.loads((B/'hard-negative-audit.json').read_text()),'sampling_control':json.loads((B/'patch-sampling-control.json').read_text()),'contour_trial':json.loads((B/'contour-trial.json').read_text()),'real':json.loads((B/'real/final/metrics.json').read_text()),'rust_tests_passed':count,'inherited_tests_skipped':['regress_auto_reports_the_selected_candidate','clearscan_repairs_a_damaged_glyph_from_same_document_donors'],'deterministic_300':(B/'300/final.pdf').read_bytes()==(B/'300/repeat.pdf').read_bytes()}
(B/'scorecard.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));print([(r['dpi'],r['arms']['final']['pdf_bytes']) for r in rows],count,result['deterministic_300'])
