"""Evaluator-only counter areas of actual embedded and original vector paths."""
from pathlib import Path
import json,math,argparse
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.areaPen import AreaPen
from design_geometry import source_positions,load_pdf_font
ap=argparse.ArgumentParser();ap.add_argument('--dpi',type=int,choices=[300,600],default=300);dpi=ap.parse_args().dpi
B=Path(__file__).resolve().parent;pos={(r['page'],r['symbol']):r for r in source_positions(dpi)}
class ContourAreas(AreaPen):
 def __init__(self,gs):super().__init__(gs);self.areas=[]
 def _moveTo(self,p):self.start_value=self.value;super()._moveTo(p)
 def _closePath(self):super()._closePath();self.areas.append(self.value-self.start_value)
def areas(ft,name):
 p=ContourAreas(ft.getGlyphSet());ft.getGlyphSet()[name].draw(p)
 if not p.areas:return 0.
 outer=max(p.areas,key=abs);return sum(abs(a) for a in p.areas if a*outer<0)
rows=[];fonts={};out={}
for arm in ['previous','final']:
 pdf=pikepdf.open(B/str(dpi)/(arm+'.pdf'));audit=json.loads((B/str(dpi)/arm/'audit.json').read_text());cache={};rs=[]
 for r in audit['placements']:
  key=(r['page'],r['symbol']);s=pos[key];ft=fonts.setdefault(s['font_path'],TTFont(s['font_path']));source=areas(ft,ft.getBestCmap()[ord(s['text'])])*(s['font_size_px']/ft['head'].unitsPerEm)**2
  f=load_pdf_font(pdf,r['font'],cache);a,b,c,d,_,_=r['matrix'];actual=areas(f['font'],f['glyph_order'][r['gid']])*abs(a*d-b*c)*(dpi/72/f['upem'])**2
  rs.append({'page':r['page'],'symbol':r['symbol'],'text':s['text'],'source_counter_px2':source,'embedded_counter_px2':actual,'known_ocr_label_conflict':key==(7,'p07s0000'),'signed_error_px2':actual-source,'absolute_error_px2':abs(actual-source)})
 selected=[r for r in rs if r['source_counter_px2']>0]
 out[arm]={'all_occurrences':len(rs),'source_counter_occurrences':len(selected),'mean_absolute_counter_area_error_px2':sum(r['absolute_error_px2'] for r in selected)/len(selected),'mean_relative_absolute_counter_area_error':sum(r['absolute_error_px2']/r['source_counter_px2'] for r in selected)/len(selected),'mean_signed_counter_area_error_px2':sum(r['signed_error_px2'] for r in selected)/len(selected),'spurious_counter_occurrences':sum(r['source_counter_px2']==0 and r['embedded_counter_px2']>.1 for r in rs),'instances':rs}
common=set.intersection(*[{(r['page'],r['symbol']) for r in a['instances']} for a in out.values()])
paired={}
for arm,a in out.items():
 selected=[r for r in a['instances'] if (r['page'],r['symbol']) in common and r['source_counter_px2']>0]
 paired[arm]={'n':len(selected),'mean_absolute_counter_area_error_px2':sum(r['absolute_error_px2'] for r in selected)/len(selected),'mean_relative_absolute_counter_area_error':sum(r['absolute_error_px2']/r['source_counter_px2'] for r in selected)/len(selected),'mean_signed_counter_area_error_px2':sum(r['signed_error_px2'] for r in selected)/len(selected)}
out['paired_common_counter_instances']=paired
(B/('counter-geometry.json' if dpi==300 else 'counter-geometry-600.json')).write_text(json.dumps({'method':__doc__,'known_ocr_conflict':'p07s0000 has supplied c for pristine e; original-font control uses cmap c, while normal product traces the source observation. Product instances remain scored as emitted.','note':'Opposite-winding contour area relative to largest outer; original and embedded glyph scales are actual source metrics/text-matrix determinant. No bbox normalization; Adobe CFF not measured by this helper.','arms':out},indent=2));print({k:{a:b for a,b in v.items() if a!='instances'} for k,v in out.items()})
