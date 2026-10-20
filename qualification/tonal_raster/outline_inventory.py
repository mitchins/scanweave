"""Actual painted TrueType GIDs, separate from Unicode text-character counts."""
import json,io
from pathlib import Path
import pikepdf
from fontTools.ttLib import TTFont
B=Path(__file__).resolve().parent;out=[]
for path in list((B/'collections').glob('*.pdf'))+list((B/'baseline-collections').glob('*.pdf'))+list((B/'300').glob('final.pdf'))+list((B/'600').glob('final.pdf'))+list((B/'control-runs').glob('*.pdf')):
 q=pikepdf.open(path);painted=set();uses=0;fonts={};page_rows=[]
 for page in q.pages:
  page_start=uses;page_set=set();font=None;mode=0
  for operands,operator in pikepdf.parse_content_stream(page):
   op=str(operator)
   if op=='Tf':font=page.Resources.Font.get(str(operands[0]))
   elif op=='Tr':mode=int(operands[0])
   elif op in ['Tj','TJ'] and mode!=3 and font is not None:
    desc=font.DescendantFonts[0];mapping=desc.get('/CIDToGIDMap');
    if not isinstance(mapping,pikepdf.Stream):continue
    mapping=mapping.read_bytes();fid=desc.FontDescriptor.FontFile2.objgen
    items=[operands[0]] if op=='Tj' else [x for x in operands[0] if isinstance(x,pikepdf.String)]
    for item in items:
     data=bytes(item)
     for i in range(0,len(data)-1,2):
      cid=int.from_bytes(data[i:i+2],'big');gid=int.from_bytes(mapping[cid*2:cid*2+2],'big');uses+=1;painted.add((fid,gid));page_set.add((fid,gid))
  page_rows.append({'draws':uses-page_start,'unique_gids':len(page_set)})
 for obj in q.objects:
  if isinstance(obj,pikepdf.Dictionary) and '/FontFile2' in obj:
   stream=obj.FontFile2;tt=TTFont(io.BytesIO(stream.read_bytes()));total=sum(getattr(tt['glyf'][n],'numberOfContours',0)!=0 for n in tt.getGlyphOrder());fonts[str(stream.objgen)]={'glyphs':tt['maxp'].numGlyphs,'nonempty_outlines':total,'encoded_bytes':len(stream.read_raw_bytes())}
 out.append({'pdf':str(path),'visible_glyph_draws':uses,'unique_painted_gids':len(painted),'uses_per_outline':uses/len(painted) if painted else None,'fonts':fonts,'pages':page_rows})
(B/'outline-inventory.json').write_text(json.dumps(out,indent=2));print([(r['pdf'],r['visible_glyph_draws'],r['unique_painted_gids']) for r in out])
