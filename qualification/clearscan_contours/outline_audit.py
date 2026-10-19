#!/usr/bin/env python3
"""Actual embedded-outline complexity and tangent continuity against pristine corners.
An unsupported tangent break is a >15 degree join >0.8 source px from any
pristine >15 degree join. This is a diagnostic, not a glyph-identity gate.
"""
import json,math
from pathlib import Path
from collections import Counter
import numpy as np,pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from design_geometry import source_positions,load_pdf_font
B=Path(__file__).resolve().parent
class Segments(BasePen):
 def __init__(self,gs,tf):super().__init__(gs);self.tf=tf;self.cur=[];self.rings=[]
 def _moveTo(self,p):self.cur=[]
 def _lineTo(self,p):self.cur.append([self.tf(self._getCurrentPoint()),self.tf(p)])
 def _qCurveToOne(self,a,b):self.cur.append([self.tf(self._getCurrentPoint()),self.tf(a),self.tf(b)])
 def _curveToOne(self,a,b,c):self.cur.append([self.tf(self._getCurrentPoint()),self.tf(a),self.tf(b),self.tf(c)])
 def _closePath(self):
  if self.cur:
   if np.linalg.norm(self.cur[-1][-1]-self.cur[0][0])>1e-8:self.cur.append([self.cur[-1][-1],self.cur[0][0]])
   self.rings.append(self.cur);self.cur=[]
 def _endPath(self):self._closePath()
def contours(ft,name,tf):
 gs=ft.getGlyphSet();p=Segments(gs,lambda p:np.asarray(tf(*p),float));gs[name].draw(p);return p.rings
def breaks(rings):
 rows=[]
 for ring in rings:
  for i,seg in enumerate(ring):
   q=ring[(i+1)%len(ring)];incoming=next((seg[-1]-v for v in reversed(seg[:-1]) if np.linalg.norm(seg[-1]-v)>1e-8),None);outgoing=next((v-q[0] for v in q[1:] if np.linalg.norm(v-q[0])>1e-8),None)
   if incoming is None or outgoing is None:continue
   angle=math.degrees(math.acos(np.clip(np.dot(incoming,outgoing)/(np.linalg.norm(incoming)*np.linalg.norm(outgoing)),-1,1)))
   if angle>15:rows.append((seg[-1],angle))
 return rows
results={};fonts={}
for dpi in [300,600]:
 pos={(r['page'],r['symbol']):r for r in source_positions(dpi)};arms={a:json.loads((B/str(dpi)/a/'audit.json').read_text()) for a in ['previous','final']};maps={a:{(r['page'],r['symbol']):r for r in d['placements']} for a,d in arms.items()};pdfs={a:pikepdf.open(B/str(dpi)/(a+'.pdf')) for a in arms};caches={a:{} for a in arms};rows=[]
 targets=[('serif e','e',0),('serif 8','8',0),('serif g','g',0),('serif 6','6',0),('italic a','a',6),('comma',',',0),('exclamation','!',0),('カ','カ',0),('ナ','ナ',0),('な','な',0),('か','か',0)]
 for label,ch,pi in targets:
  keys=[k for k,s in pos.items() if k[0]==pi and s['text']==ch and all(k in maps[a] for a in arms)]
  if not keys:rows.append({'target':label,'status':'raster fallback or no common vector occurrence'});continue
  key=keys[0];s=pos[key];ft=fonts.setdefault(s['font_path'],TTFont(s['font_path']));scale=s['font_size_px']/ft['head'].unitsPerEm;src=contours(ft,ft.getBestCmap()[ord(ch)],lambda x,y:(s['x_px']+x*scale,s['baseline_px']-y*scale));corners=[p for p,_ in breaks(src)];row={'target':label,'page':pi,'id':key[1],'pristine_points':len(ft['glyf'][ft.getBestCmap()[ord(ch)]].getCoordinates(ft['glyf'])[0]),'pristine_corners_over_15_degrees':len(corners),'arms':{}}
  for arm in arms:
   r=maps[arm][key];f=load_pdf_font(pdfs[arm],r['font'],caches[arm]);ft=f['font'];name=f['glyph_order'][r['gid']];a,b,c,d,e,fy=r['matrix'];up=f['upem'];h=float(pdfs[arm].pages[pi].MediaBox[3]);rs=contours(ft,name,lambda x,y:((e+(a*x+c*y)/up)*dpi/72,(h-fy-(b*x+d*y)/up)*dpi/72));bs=breaks(rs);uns=[angle for p,angle in bs if not corners or min(np.linalg.norm(p-q) for q in corners)>.8];g=ft['glyf'][name];row['arms'][arm]={'gid':r['gid'],'points':len(g.coordinates),'contours':g.numberOfContours,'segments':sum(len(r) for r in rs),'tangent_breaks_over_15_degrees':len(bs),'unsupported_tangent_breaks':len(uns),'quadratic_segments':sum(len(seg)==3 for ring in rs for seg in ring),'reused_occurrences':sum(x['gid']==r['gid'] and x['font']==r['font'] for x in arms[arm]['placements'])}
  rows.append(row)
 results[str(dpi)]=rows
(B/'outline-audit.json').write_text(json.dumps({'method':__doc__,'targets':results},indent=2,ensure_ascii=False));print(json.dumps(results,indent=2,ensure_ascii=False))
