import json,sys,re,collections
from pathlib import Path
root=Path(sys.argv[1]);name=sys.argv[2];a,b=[json.load(open(root/f'{name}-{x}-1.pdf.json')) for x in ('main','candidate')]
def walk(a,b,p=''):
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(a.keys()|b.keys()):
   if k.endswith('_ms') or k in ('stage_timings','stage_timings_ms'):continue
   if k not in a or k not in b:yield (p+'/'+k,'missing');continue
   yield from walk(a[k],b[k],p+'/'+k)
 elif isinstance(a,list) and isinstance(b,list):
  if len(a)!=len(b):yield (p,f'length {len(a)}->{len(b)}');return
  for i,(x,y) in enumerate(zip(a,b)):yield from walk(x,y,p+'/'+str(i))
 elif a!=b:yield (p,'different')
diffs=list(walk(a,b));print(json.dumps(diffs,indent=2));
