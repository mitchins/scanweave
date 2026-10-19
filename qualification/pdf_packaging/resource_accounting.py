import pikepdf,json
from pathlib import Path
B=Path(__file__).resolve().parent

def account(path):
 p=pikepdf.open(path);sets={'font':set(),'unicode_cid':set(),'content':set()}
 for page in p.pages:
  for s in page.Contents if isinstance(page.Contents,pikepdf.Array) else [page.Contents]:sets['content'].add(s.objgen)
 for o in p.objects:
  if not isinstance(o,pikepdf.Dictionary):continue
  for key in ['/FontFile','/FontFile2','/FontFile3']:
   if key in o:sets['font'].add(o[key].objgen)
  for key in ['/ToUnicode','/CIDToGIDMap']:
   if key in o and isinstance(o[key],pikepdf.Stream):sets['unicode_cid'].add(o[key].objgen)
 counts={k:0 for k in ['raster','font','content','unicode_cid','object_stream','xref_stream','other_stream']}
 for o in p.objects:
  if not isinstance(o,pikepdf.Stream):continue
  category=next((k for k,s in sets.items() if o.objgen in s),None)
  if category is None:category='raster' if o.get('/Subtype')==pikepdf.Name.Image else 'object_stream' if o.get('/Type')==pikepdf.Name.ObjStm else 'xref_stream' if o.get('/Type')==pikepdf.Name.XRef else 'other_stream'
  counts[category]+=len(o.read_raw_bytes())
 return dict(pdf_bytes=path.stat().st_size,streams=counts,syntax_overhead=path.stat().st_size-sum(counts.values()))
rows=[]
for dpi in [300,600]:
 row={'dpi':dpi,'baseline':account(B.parent/'clearscan_background'/str(dpi)/'final.pdf'),'native':account(B/str(dpi)/'final.pdf'),'pikepdf':account(B/str(dpi)/'combined.pdf'),'adobe':account(B.parent/'clearscan_background'/str(dpi)/'adobe.pdf')};rows.append(row)
(B/'byte-accounting.json').write_text(json.dumps(rows,indent=2));print(rows)
