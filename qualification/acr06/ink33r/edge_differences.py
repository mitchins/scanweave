#!/usr/bin/env python3
"""Paired vector-minus-raster edge-width proxy per mixed line."""
import json,pathlib,numpy as np
p=pathlib.Path('/data/coding/scanweave/qualification/acr06/ink33r');out={}
for d in ('historical','financial','mixed','receipts','forms'):
 rows=[x for f in p.glob(f'metrics-{d}-*.json') for x in json.loads(f.read_text())['lines']];dif=[]
 for l in rows:
  m=l['metrics']['scanweave'];a=m['edge_vector'];b=m['edge_raster']
  if a is not None and b is not None:dif.append(a-b)
 def q(v):return {'n':len(v),'p10':float(np.percentile(v,10)),'p50':float(np.median(v)),'p90':float(np.percentile(v,90))} if v else None
 out[d]={'lines':len(rows),'edge_vector_minus_raster_300dpi_px':q(dif),'edge_vector_minus_raster_96dpi_px':q([x*96/300 for x in dif])}
(p/'edge-differences.json').write_text(json.dumps(out,indent=2)+'\n')
