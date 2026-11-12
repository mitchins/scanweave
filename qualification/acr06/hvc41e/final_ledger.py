"""Join the frozen independent review with composed-font and halo measurements."""
import json
from pathlib import Path
root=Path('/data/coding/scanweave/qualification/acr06/hvc41e')
read=lambda n:json.loads((root/n).read_text())
decisions=read('review-decisions.json'); comp={x['proposal']:x for x in read('composition-check.json')['glyphs']}; halo={x['proposal']:x for x in read('halo-composition.json')}; panels={x['proposal']:x for x in read('final-panel-index.json') if x.get('kind')=='emitted_glyph_4x'}
rows=[]
for decision in decisions:
 p=decision['proposal']; row={'frozen_review':decision,'emitted':p in comp}
 if p in comp: row.update(composition=comp[p],halo=halo[p],final_panel=panels[p])
 rows.append(row)
assert len(rows)==54 and len(comp)==38 and all(not row['composition']['interaction_or_metric_change'] for row in rows if row['emitted'])
(root/'final-glyph-ledger.json').write_text(json.dumps(rows,indent=2)+'\n')
