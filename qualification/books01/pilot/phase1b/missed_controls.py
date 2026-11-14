#!/usr/bin/env python3
"""Record provisionally visible fresh-control changes not flagged by text detectors."""
import json,pathlib
Q=pathlib.Path(__file__).resolve().parents[1];p=Q/'results/phase1b/fresh-controls.json';x=json.loads(p.read_text());cal=json.loads((Q/'results/phase1b/calibration.json').read_text())['detectors'];examples=[]
for row in x['controls']:
 kinds=row['taxonomy'];visible=any(k in kinds for k in ['blur_texture','colour_shift','wrong_shape','missing_ink','spurious_ink_halo']);scores=row['scores'];flag=any(scores and scores.get(k) is not None and cal[k]['threshold'] is not None and scores[k]>=cal[k]['threshold'] for k in ['glyph_shape','missing_ink','spurious_ink']);row['text_detector_flagged']=bool(flag);row['visible_change_not_flagged_by_text_detectors']=bool(visible and not flag)
 if visible and not flag:examples.append({'control_id':row['control_id'],'page':row['page'],'row':row['row'],'taxonomy':kinds,'assessment':'AI-assessed, provisional (not human-adjudicated); nonblinded'})
x['visible_change_not_flagged_examples']=examples;x['missed_change_note']='Visible change is provisional and broader than wrong-glyph damage; text detectors do not include a dedicated text-colour/texture classifier.';p.write_text(json.dumps(x,indent=2)+'\n')
