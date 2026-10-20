"""Separate actual PDF CID Unicode transport from renderer word reconstruction."""
import json,re
from pathlib import Path
import pikepdf
B=Path(__file__).resolve().parent
paths=[B/str(d)/'clearscan.pdf' for d in (300,600)]+sorted((B/'real/product').glob('*.pdf'));rows=[]
norm=lambda s:re.sub(r'\s+','',s)
for path in paths:
 pdf=pikepdf.open(path);pages=[]
 for page in pdf.pages:
  fonts={}
  for k,f in page.Resources.Font.items():
   cmap={};s=f.ToUnicode.read_bytes().decode('ascii')
   for section in re.findall(r'beginbfchar(.*?)endbfchar',s,re.S):
    for a,b in re.findall(r'<([a-fA-F0-9]+)>\s*<([a-fA-F0-9]+)>',section):cmap[int(a,16)]=bytes.fromhex(b).decode('utf-16-be')
   fonts[str(k)]=cmap
  f=None;actual=[];chars=[];spans=[];current=None
  for i in pikepdf.parse_content_stream(page):
   op=str(i.operator);v=i.operands
   if op=='Tf':f=str(v[0])
   elif op=='BDC' and len(v)>1 and isinstance(v[1],pikepdf.Dictionary) and '/ActualText' in v[1]:
    current={'actual':str(v[1].ActualText),'cid_text':''};spans.append(current);actual.append(current['actual'])
   elif op in ('Tj','TJ'):
    ss=[v[0]] if op=='Tj' else [s for s in v[0] if isinstance(s,pikepdf.String)]
    for s in ss:
     raw=bytes(s);text=''.join(fonts[f].get(int.from_bytes(raw[j:j+2],'big'),'\ufffd') for j in range(0,len(raw),2));chars.append(text)
     if current is not None:current['cid_text']+=text
   elif op=='EMC':current=None
  mismatches=[s for s in spans if norm(s['actual'])!=norm(s['cid_text'])]
  pages.append({'actual_chars':len(norm(''.join(actual))),'cid_chars':len(norm(''.join(chars))),'exact_nonspace_cid_sequence':norm(''.join(actual))==norm(''.join(chars)),'mismatched_spans':mismatches})
 rows.append({'path':str(path.relative_to(B)),'pages':pages});print(path.name,[r['exact_nonspace_cid_sequence'] for r in pages],flush=True)
(B/'semantic-audit.json').write_text(json.dumps({'method':__doc__,'documents':rows},indent=2,ensure_ascii=False))
