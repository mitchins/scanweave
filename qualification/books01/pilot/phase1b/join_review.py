#!/usr/bin/env python3
"""Join prior provisional crop verdicts to rows without copying GT text or the panel key."""
import hashlib,json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[2]; Q=P/'pilot';review=Q/'review/adjudication.json';a=json.loads(review.read_text());idx={x['crop_id']:x for x in json.loads((B/'pilot/blind/blind-index.json').read_text())};key=json.loads((B/'pilot/blind-key.json').read_text());out=[]
for number,verdict in a['crops'].items():
 cid='crop-'+number; meta=idx[cid]; mapping=key[cid]['labels'];panels={mapping[label]:types for label,types in verdict.get('panels',{}).items()};confirmed=[mapping[label] for label in verdict.get('confirmed',{})];out.append({'crop_id':cid,'page':meta['page'],'bbox':meta['bbox'],'original_detector':meta['detector'],'original_flagged_row':key[cid]['flagged_row'],'review_verdict':verdict['detector_verdict'],'provisional_positive_rows':confirmed,'panel_taxonomy_by_row':panels,'assessment':'AI-assessed, provisional (not human-adjudicated)'})
(Q/'results/phase1b').mkdir(exist_ok=True);(Q/'results/phase1b/reference.json').write_text(json.dumps({'assessment':'AI-assessed, provisional (not human-adjudicated)','review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),'crops':out},indent=2)+'\n')
