"""Actual embedded TrueType complexity; includes hidden semantic glyphs."""
import json,io
from pathlib import Path
import pikepdf
from fontTools.ttLib import TTFont
B=Path(__file__).resolve().parent;out={}
for dpi in [300,600]:
 out[str(dpi)]={}
 for arm in ['previous','final']:
  p=pikepdf.open(B/str(dpi)/(arm+'.pdf'));seen=set();rows=[]
  for obj in p.objects:
   if isinstance(obj,pikepdf.Dictionary) and '/FontFile2' in obj:
    s=obj.FontFile2
    if s.objgen in seen:continue
    seen.add(s.objgen);f=TTFont(io.BytesIO(s.read_bytes()));g=f['glyf'];rows.append({'font_bytes':len(s.read_raw_bytes()),'glyphs':len(f.getGlyphOrder()),'nonempty_outlines':sum(g[n].numberOfContours!=0 for n in f.getGlyphOrder()),'contours':sum(g[n].numberOfContours for n in f.getGlyphOrder()),'points':sum(len(g[n].getCoordinates(g)[0]) for n in f.getGlyphOrder() if g[n].numberOfContours)})
  out[str(dpi)][arm]=rows
(B/'outline-complexity.json').write_text(json.dumps(out,indent=2))
