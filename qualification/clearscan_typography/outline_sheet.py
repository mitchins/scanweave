"""Evaluator-only exact vector paths; each column uses the same physical frame."""
from pathlib import Path
import json,html
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from design_geometry import source_positions,load_pdf_font
B=Path(__file__).resolve().parent;ROOT=B.parents[1];dpi=300
positions=source_positions(dpi);pos={(r['page'],r['symbol']):r for r in positions};arms={}
for arm in ['previous','final']:
 doc=pikepdf.open(B/'300'/(arm+'.pdf'));audit=json.loads((B/'300'/arm/'audit.json').read_text());arms[arm]=(doc,{(r['page'],r['symbol']):r for r in audit['placements']},{})
selected=[]
for pi,ch in [(0,'e'),(0,'6'),(0,'8'),(0,'g'),(6,'a'),(3,'!'),(0,'カ'),(0,'ナ'),(0,'な'),(0,'か')]:
 candidates=[r for r in positions if r['page']==pi and r['text']==ch and (pi,r['symbol']) in arms['final'][1]]
 if candidates:selected.append(candidates[0])
width=1020;rowh=260;out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{len(selected)*rowh+40}" viewBox="0 0 {width} {len(selected)*rowh+40}"><rect width="100%" height="100%" fill="white"/>']
for i,label in enumerate(['Pristine design outline','Previous embedded outline','Final embedded outline']):out.append(f'<text x="{i*340+5}" y="20" font-size="14">{label}</text>')
for ri,r in enumerate(selected):
 pi=r['page'];sid=r['symbol'];t=json.loads((ROOT/f'qualification/experiments/m1g/fixture/dpi300/oracle/page{pi:02}.truth.json').read_text());truth=next(x for x in t['records'] if x['id']==sid);x0,y0,_,_=truth['bbox']
 for ci,arm in enumerate(['pristine','previous','final']):
  if arm=='pristine':
   ft=TTFont(r['font_path']);name=ft.getBestCmap()[ord(r['text'])];k=r['font_size_px']/ft['head'].unitsPerEm;mat=[k,0,0,-k,r['x_px'],r['baseline_px']]
  else:
   doc,placements,cache=arms[arm];a=placements.get((pi,sid))
   if a is None:continue
   pf=load_pdf_font(doc,a['font'],cache);ft=pf['font'];name=pf['glyph_order'][a['gid']];sx,b,c,sy,tx,ty=a['matrix'];upem=pf['upem'];H=float(doc.pages[pi].MediaBox[3])*dpi/72;mat=[sx/upem*dpi/72,-b/upem*dpi/72,c/upem*dpi/72,-sy/upem*dpi/72,tx*dpi/72,H-ty*dpi/72]
  pen=SVGPathPen(ft.getGlyphSet());ft.getGlyphSet()[name].draw(pen)
  out.append(f'<text x="{ci*340+5}" y="{ri*rowh+45}" font-size="12">{html.escape(r["text"])} / p{pi} {sid}</text>')
  out.append(f'<g transform="translate({ci*340+10},{ri*rowh+55}) scale(3.2) translate({-x0},{-y0})"><path transform="matrix({" ".join(map(str,mat))})" d="{pen.getCommands()}" fill="#222"/></g>')
out.append('</svg>');(B/'300/isolated-vector-outlines.svg').write_text('\n'.join(out));print(len(selected),'families')
