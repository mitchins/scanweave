#!/usr/bin/env python3
import json,collections
from pathlib import Path
p=Path('/data/coding/scanweave/qualification/acr06/c2b');data=json.loads((p/'measurements.json').read_text());out={}
ks=['eligible_label_at_least_10','any_nonself_fit','any_structural_pass','any_hygiene_band_pass','any_relative_pass','any_absolute_pass','self_admissible_canonical','cover_below_quorum_members','cover_no_self_admissible_remaining','planned_members','legacy_invalid','corrected_reject','combined_reject','final_accepted_before_economy']
for dpi in (200,300,600):
 c=collections.Counter();n=0
 for name,item in data.items():
  if name.startswith('development'):continue
  i=int(name.rsplit('-',1)[1]);d=(200,300,600)[i if name.startswith('font01-') else i//3]
  if d==dpi:c.update(item['counts']);n+=1
 den=c['eligible_label_at_least_10'];out[str(dpi)]={'documents':n,'eligible':den,'stages':{k:{'count':c[k],'rate':c[k]/den} for k in ks}}
(p/'dpi-rates.json').write_text(json.dumps(out,indent=2)+'\n')
