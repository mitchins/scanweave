"""Evaluator-only font-origin invariance control. Geometry cancels exactly.
Translate font units and compensate text matrices; tests renderer grid phase.
"""
import io,json,math,sys
from pathlib import Path
import numpy as np,pikepdf,pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from PIL import Image
B=Path(__file__).resolve().parent;root=B.parents[1];dpi=300;arm=sys.argv[1] if len(sys.argv)>1 else 'subpixel';base=B/str(dpi);m=json.loads((base/arm/'metrics.json').read_text());truth=[np.asarray(Image.open(root/f'qualification/experiments/m1g/fixture/dpi300/oracle/page{i:02}.png').convert('L')) for i in range(8)]
def evaluate(path):
 doc=pdfium.PdfDocument(path);images=[np.asarray(pg.render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L')) for pg in doc];res=[]
 for r in m['glyphs']:
  if r['geometry']!='exact' or not r['text'].strip():continue
  x0,y0,x1,y1=map(int,r['bbox']);pad=4 if ord(r['text'][0])>127 else 5;sl=np.s_[y0+pad:y1-pad,x0+pad:x1-pad];a=images[r['page']][sl]<170;t=truth[r['page']][sl]<170;res.append(float((a&t).sum()/max(1,(a|t).sum())))
 return float(np.mean(res))
out=[]
for dx,dy in [(x,0) for x in [0,8,16,24,32]]:
 p=pikepdf.open(base/(arm+'.pdf'));seen=set()
 for pg in p.pages:
  for f in pg.Resources.Font.values():
   fd=f.DescendantFonts[0].FontDescriptor;s=fd.FontFile2
   if fd.objgen in seen:continue
   seen.add(fd.objgen);ft=TTFont(io.BytesIO(s.read_bytes()),recalcBBoxes=True,recalcTimestamp=False)
   for name in ft.getGlyphOrder():
    g=ft['glyf'][name]
    if g.numberOfContours:
     g.coordinates.translate((dx,dy));a,l=ft['hmtx'][name];ft['hmtx'][name]=(a,l+dx)
   buf=io.BytesIO();ft.save(buf);fd.FontFile2=pikepdf.Stream(p,buf.getvalue());fd.FontFile2.Length1=len(buf.getvalue())
  ops=[]
  for ins in pikepdf.parse_content_stream(pg):
   if str(ins.operator)=='Tm':
    a,b,c,d,e,f=map(float,ins.operands);ins=pikepdf.ContentStreamInstruction([a,b,c,d,e-(a*dx+c*dy)/2048,f-(b*dx+d*dy)/2048],pikepdf.Operator('Tm'))
   ops.append(ins)
  pg.Contents=pikepdf.Stream(p,pikepdf.unparse_content_stream(ops)+b'\nET\n')
 path=base/f'phase-{dx}-{dy}.pdf';p.save(path);v=evaluate(path);print(dx,dy,v,flush=True);out.append({'dx_fu':dx,'dy_fu':dy,'pdfium_iou':v})
(base/(arm+'-phase-control.json')).write_text(json.dumps(out,indent=2))
