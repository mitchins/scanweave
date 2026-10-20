"""Diagnostic paint ablation; observed witness ink only, no pristine inference.
Rewrites output text color for diagnosis. Any accepted product correction must
be implemented in the normal assembler input, not this evaluator utility.
"""
import json,math
from pathlib import Path
import numpy as np
import pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;ROOT=B.parents[1];dpi=300
base=ROOT/'qualification/experiments/m1g/fixture/dpi300';reference=json.loads((B/'300/previous/metrics.json').read_text());records=[r for r in reference['glyphs'] if r['geometry']=='exact' and 'source_isolated' in r];truths=[np.asarray(Image.open(base/'oracle'/f'page{i:02}.png').convert('L')) for i in range(8)]
result=[]
for arm in ('previous','fit','edgefit'):
 report=json.loads((B/'300'/(arm+'.json')).read_text());pdf=pikepdf.open(B/'300'/(arm+'.pdf'));levels=[]
 for i,page in enumerate(pdf.pages):
  prototypes={g['prototype_id']:g for g in report['page_reports'][i]['reconstruction']['canonical_geometry']};values=[float(np.quantile(g['grayscale'],.05)) for g in prototypes.values() if g['grayscale']];ink=float(np.median(values));levels.append(ink);inside=False;ops=[]
  for ins in pikepdf.parse_content_stream(page):
   op=str(ins.operator)
   if op=='BT':inside=True
   if op=='rg' and inside:ins=pikepdf.ContentStreamInstruction([ink/255]*3,pikepdf.Operator('rg'))
   ops.append(ins)
   if op=='ET':inside=False
  page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(ops))
 path=B/'300'/(arm+'-observed-ink.pdf');pdf.save(path);doc=pdfium.PdfDocument(path);arr=[np.asarray(p.render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L')) for p in doc];scores=[]
 for r in records:
  x0,y0,x1,y1=map(int,r['bbox']);pad=4 if ord(r['text'][0])>127 else 5;sl=(slice(y0+pad,y1-pad),slice(x0+pad,x1-pad));a=arr[r['page']][sl]<170;t=truths[r['page']][sl]<170;scores.append(float((a&t).sum()/max(1,(a|t).sum())))
 row={'arm':arm,'ink_by_page':levels,'pdf':str(path),'glyph_iou':float(np.mean(scores)),'n':len(scores)};result.append(row);print(row,flush=True)
(B/'paint-probe.json').write_text(json.dumps(result,indent=2))
