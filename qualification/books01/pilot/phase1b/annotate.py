#!/usr/bin/env python3
"""Attach Adobe configuration and provisional-review labels to calibration rows."""
import json,pathlib
Q=pathlib.Path(__file__).resolve().parents[1];R=Q/'results/phase1b';label='Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew)';provisional='AI-assessed, provisional (not human-adjudicated)'
for name in ['reference.json','calibration.json','fresh-controls.json','triage-summary.json','human-panel-index.json']:
 p=R/name;x=json.loads(p.read_text());status=provisional+'; fresh controls nonblinded' if name=='fresh-controls.json' else provisional;x['assessment']=status;x['adobe_configuration']=label
 for field in ['raw_scores','controls','crops']:
  for row in x.get(field,[]):
   row['assessment']=status
   if row.get('row')=='adobe-E' or row.get('original_flagged_row')=='adobe-E' or 'adobe-E' in row.get('provisional_positive_rows',[]):row['adobe_configuration']=label
 for group in x.get('examples',{}).values():
  for values in group.values():
   for row in values:
    row['assessment']=provisional
    if row.get('row')=='adobe-E':row['adobe_configuration']=label
 p.write_text(json.dumps(x,indent=2)+'\n')
