#!/usr/bin/env python3
"""Verify counterfactual page streams have only pairs of rg insertions around
visible text shows, with all original instructions unchanged and in order."""
import json,pathlib,pikepdf
R=pathlib.Path('/data/coding/scanweave'); E=R/'qualification/acr06/ink33r'; O=R/'qualification/acr06/local/ink33r'; B=R/'qualification/acr06/local/bg150/baseline'
def encode(i): return pikepdf.unparse_content_stream([i])
def check(a,b):
 original=list(pikepdf.parse_content_stream(a)); changed=list(pikepdf.parse_content_stream(b)); j=0; tr=0; stack=[]; count=0
 for ins in original:
  op=str(ins.operator)
  if op=='q': stack.append(tr)
  elif op=='Q' and stack: tr=stack.pop()
  elif op=='Tr': tr=int(ins.operands[0])
  if j>=len(changed): raise ValueError('missing original instruction')
  if encode(ins)==encode(changed[j]): j+=1; continue
  if op in ('Tj','TJ',"'",'"') and tr in (0,2,4,6) and j+2<len(changed) and str(changed[j].operator)=='rg' and encode(ins)==encode(changed[j+1]) and str(changed[j+2].operator)=='rg': j+=3; count+=1; continue
  raise ValueError(f'unexpected edit around {op} at changed instruction {j}')
 if j!=len(changed): raise ValueError('trailing extra instructions')
 return count
out={}
for g in ['historical','financial','mixed','receipts','forms']:
 out[g]={}
 with pikepdf.open(O/f'{g}.pdf') as a:
  for mode in 'abc':
   with pikepdf.open(O/f'{g}-cf-{mode}.pdf') as b:
    if len(a.pages)!=len(b.pages): raise ValueError('page count changed')
    cs=[]
    for x,y in zip(a.pages,b.pages):
     if list(x.MediaBox)!=list(y.MediaBox) or x.get('/CropBox')!=y.get('/CropBox') or x.get('/Rotate')!=y.get('/Rotate'): raise ValueError('page geometry changed')
     cs.append(check(x,y))
    out[g][mode]=cs
(E/'edit-validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
