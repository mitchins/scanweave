#!/usr/bin/env python3
"""Check that adding the opt-in field does not alter default policy JSON."""
import json
from pathlib import Path
root=Path('/data/coding/scanweave/qualification/acr06/local/bg150'); out=Path('/data/coding/scanweave/qualification/acr06/bg150/default-policies.json')
def policies(obj):
 if isinstance(obj,dict):
  for key,value in obj.items():
   if key=='policy' and isinstance(value,dict): yield value
   yield from policies(value)
 elif isinstance(obj,list):
  for value in obj: yield from policies(value)
result={}
for name in ['financial','forms','historical','mixed','receipts']:
 a=list(policies(json.loads((root/'baseline'/f'{name}.pdf.json').read_text())))
 b=list(policies(json.loads((root/'release-default'/f'{name}.pdf.json').read_text())))
 result[name]={'baseline_policy_count':len(a),'final_policy_count':len(b),'equal':a==b}
out.write_text(json.dumps(result,indent=2)+'\n')
