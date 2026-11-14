#!/usr/bin/env python3
"""Record pilot PDF byte hashes only."""
import hashlib,json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];q=P/'pilot/results/runs.json';x=json.loads(q.read_text())
for id,record in x.items():
 key=id.split('/')[-1]
 for row,v in record['rows'].items():
  path=pathlib.Path(v.get('path',B/'pilot/runs'/key/(row+'.pdf')))
  if path.exists():
   with path.open('rb') as f:v['output_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
q.write_text(json.dumps(x,indent=2)+'\n')
