#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json,numpy as np
R=Path('/data/coding/scanweave/qualification/acr06');d=json.loads((R/'local/c2b/truth-pair-details.json').read_text());out={}
for dpi in (300,600):
 v={};eligible=matched=0
 for kind in ('same','different'):
  vals=[];pc=Counter()
  for doc,x in d.items():
   if doc.startswith('font01-') or int(doc.rsplit('-',1)[1])//3 != (1 if dpi==300 else 2):continue
   vals.extend(t['error'] for t in x['best'][kind]['members'].values());pc.update(x['pair_counts'])
   if kind=='same':matched+=x['match_counts'].get('matched',0);eligible+=sum(x['match_counts'].values())
  v[kind]={'members_with_tested_pair':len(vals),'best_above_0_08':sum(x>.08 for x in vals),'best_error_quantiles':{str(q):float(np.quantile(vals,q)) for q in (0,.1,.25,.5,.75,.9,1)},'tested_pairs':pc[kind],'tested_pairs_above_0_08':pc[kind+'_above_008']}
 out[str(dpi)]={'eligible':eligible,'matched':matched,'match_rate':matched/eligible,'designs':v}
(R/'c2b/design-aggregate.json').write_text(json.dumps(out,indent=2)+'\n')
