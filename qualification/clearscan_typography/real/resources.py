"""Count actual visible glyph codes in completed real-document PDFs."""
from pathlib import Path
import json
import pikepdf
B=Path(__file__).resolve().parent;rows=json.loads((B/'final/metrics.json').read_text())
for row in rows:
 p=pikepdf.open(B/'final'/(row['name']+'.pdf'));count=0;gids=set()
 for page in p.pages:
  mode=0;font=None
  for i in pikepdf.parse_content_stream(page):
   op=str(i.operator);v=i.operands
   if op=='Tr':mode=int(v[0])
   elif op=='Tf':font=page.Resources.Font[str(v[0])]
   elif op in ('Tj','TJ') and mode in (0,1,2):
    strings=[v[0]] if op=='Tj' else [x for x in v[0] if isinstance(x,pikepdf.String)];d=font.DescendantFonts[0];m=d.CIDToGIDMap.read_bytes()
    for s in strings:
     b=bytes(s)
     for j in range(0,len(b),2):
      cid=int.from_bytes(b[j:j+2],'big');gid=int.from_bytes(m[cid*2:cid*2+2],'big');gids.add((font.objgen,gid));count+=1
 row['actual_vector_occurrences']=count;row['actual_used_visible_font_gids']=len(gids)
(B/'final/metrics.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
print([(r['name'],r['actual_vector_occurrences'],r['actual_used_visible_font_gids']) for r in rows])
