#!/usr/bin/env python3
"""Compare unchanged surviving mixed lines by page and OCR line ID."""
import json,pathlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');old=R/'ink33';new=R/'ink33r';rows=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 for f in sorted(new.glob(f'metrics-{doc}-*.json')):
  a=json.loads((old/f.name).read_text())['lines'];b=json.loads(f.read_text())['lines'];aa={x['id']:x for x in a};bb={x['id']:x for x in b};common=set(aa)&set(bb);keys=('tone_iqr','gap','tone_error','signed_error','density_vector','density_raster','edge_vector','edge_raster','roughness_vector','roughness_raster','ssim');changed=[]
  for lid in sorted(common):
   for method in ('source','scanweave','adobe'):
    for k in keys:
     x=aa[lid]['metrics'][method][k];y=bb[lid]['metrics'][method][k]
     if (x is None)!=(y is None) or (x is not None and abs(x-y)>1e-6):changed.append({'line':lid,'method':method,'metric':k,'old':x,'new':y})
  rows.append({'document':doc,'page':int(f.stem[-2:]),'old_lines':len(aa),'new_lines':len(bb),'common_lines':len(common),'old_only':sorted(set(aa)-set(bb)),'new_only':sorted(set(bb)-set(aa)),'metric_differences':changed})
(new/'paired-lines.json').write_text(json.dumps(rows,indent=2)+'\n')
print('paired',sum(r['common_lines'] for r in rows),'changed metrics',sum(len(r['metric_differences']) for r in rows),'old only',sum(len(r['old_only']) for r in rows),'new only',sum(len(r['new_only']) for r in rows))
