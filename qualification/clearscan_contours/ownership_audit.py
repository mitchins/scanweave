"""Actual emitted raster/vector overlap at each vector occurrence.
Dark=sample<170, measured without independent glyph alignment. Superseded-source
pixels that differ from a recovered outline are not automatically missing ink.
Raster-only PDF removes text objects, leaving the original image placements.
"""
import json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
import pikepdf,pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
for dpi in (300,600):
 out=B/str(dpi)/'final';pdf=pikepdf.open(B/str(dpi)/'final.pdf');audit=json.loads((out/'audit.json').read_text());report=json.loads((B/str(dpi)/'final.json').read_text());rows=[]
 for page in pdf.pages:
  keep=[];inside=False
  for i in pikepdf.parse_content_stream(page):
   op=str(i.operator)
   if op=='BT':inside=True
   if not inside:keep.append(i)
   if op=='ET':inside=False
  page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(keep))
 path=out/'raster-only.pdf';pdf.save(path);doc=pdfium.PdfDocument(path);vec=pdfium.PdfDocument(out/'stages/S4-vector-only.pdf')
 for pi in range(8):
  source=np.asarray(Image.open(ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page{pi:02}.png').convert('L'));ras=np.asarray(doc[pi].render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L'));v=np.asarray(vec[pi].render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L'));obs={o['symbol_id']:o for o in report['page_reports'][pi]['reconstruction']['observations']}
  for a in audit['placements']:
   if a['page']!=pi or a['symbol'] not in obs:continue
   o=obs[a['symbol']];x0,y0,x1,y1=map(int,o['bbox_px']);s=source[y0:y1,x0:x1]<170;r=ras[y0:y1,x0:x1]<170;vv=v[y0:y1,x0:x1]<170
   rows.append({'page':pi,'id':a['symbol'],'bbox':o['bbox_px'],'original_dark_px':int(s.sum()),'raster_dark_px':int(r.sum()),'vector_dark_px':int(vv.sum()),'original_dark_still_in_raster_px':int((s&r).sum()),'raster_vector_double_dark_px':int((r&vv).sum()),'source_dark_uncovered_px':int((s&~(r|vv)).sum())})
 totals={k:sum(r[k] for r in rows) for k in rows[0] if k.endswith('_px')};(out/'ownership-audit.json').write_text(json.dumps({'method':__doc__,'renderer':'PDFium nextafter exact-size','totals':totals,'occurrences':rows},indent=2));print(dpi,totals,flush=True)
