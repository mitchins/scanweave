"""Inspect crossing marks inside and outside the actual emitted vector fringe."""
import json,math
from pathlib import Path
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1];rows=[]
for dpi in [300,600]:
 d=B/'hard-negative'/str(dpi);pdf=pikepdf.open(d/'final.pdf');report=json.loads((d/'final.json').read_text())['page_reports'][0];source=np.asarray(Image.open(d/'page00.png').convert('RGB'));original=np.asarray(Image.open(R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page00.png').convert('RGB'));added=(source!=original).any(2)
 # Read actual lossless native image pixels at their source coordinates.
 kept=np.zeros(added.shape,bool);changed=np.zeros_like(kept)
 images={}
 import hashlib
 for x in pdf.pages[0].Resources.XObject.values():
  a=np.asarray(pikepdf.PdfImage(x).as_pil_image().convert('RGB'));images[(int(x.Width),int(x.Height),hashlib.sha256(a.tobytes()).hexdigest())]=a
 for p in report['patches']:
  if p['compact_background']:continue
  a=images[(p['w'],p['h'],p['rgb_sha256'])];x0,y0,x1,y1=map(int,p['bbox_px']);kept[y0:y1,x0:x1]=True;changed[y0:y1,x0:x1]|=(a!=source[y0:y1,x0:x1]).any(2)
 ops=[i for i in pikepdf.parse_content_stream(pdf.pages[0]) if str(i.operator)!='Do'];pdf.pages[0].Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(ops));pdf.save(d/'vector-only.pdf');vec=np.asarray(pdfium.PdfDocument(d/'vector-only.pdf')[0].render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L'))
 final=np.asarray(pdfium.PdfDocument(d/'final.pdf')[0].render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L'));ink=original.mean(2)<225;near=ink.copy();r=dpi//300
 for dy in range(-r,r+1):
  for dx in range(-r,r+1):near|=np.roll(np.roll(ink,dy,0),dx,1)
 outside=added&(vec>=250);band=added&near&~ink;affected=outside&changed
 rows.append({'dpi':dpi,'added_rule_pixels':int(added.sum()),'rule_pixels_in_source_mask_fringe':int(band.sum()),'native_changed_rule_fringe':int((band&changed).sum()),'changed_rule_outside_actual_vector':int(affected.sum()),'rule_outside_vector_native_exact':int((outside&kept&~changed).sum()),'rule_outside_vector_without_native':int((outside&~kept).sum()),'outside_vector_render_luma_mean':float(final[outside].mean()),'pdfium_line_mean_abs_sample_error':float(abs(final[outside].astype(float)-245).mean()),'pdfium_line_max_sample_error':float(abs(final[outside].astype(float)-245).max()),'pdfium_line_samples_lighter_than_252':int((final[outside]>252).sum()),'poppler_line_samples_lighter_than_252':int((np.asarray(Image.open(d/'poppler.png').convert('L'))[outside]>252).sum()),'poppler_line_mean_abs_sample_error':float(abs(np.asarray(Image.open(d/'poppler.png').convert('L'))[outside].astype(float)-245).mean()),'poppler_line_max_sample_error':float(abs(np.asarray(Image.open(d/'poppler.png').convert('L'))[outside].astype(float)-245).max()),'outside_vector_source_luma_mean':float(source.mean(2)[outside].mean()),'render_extrema_without_native':[int(final[outside&~kept].min()),int(final[outside&~kept].max())] if (outside&~kept).any() else None})
(B/'hard-negative-audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
