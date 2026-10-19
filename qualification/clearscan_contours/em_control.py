"""Diagnostic font-unit conditioning; physical outlines and text stay fixed."""
import io,sys
from pathlib import Path
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
src=Path(sys.argv[1]);dst=Path(sys.argv[2]);factor=float(sys.argv[3]);p=pikepdf.open(src);seen=set()
for pg in p.pages:
 for f in pg.Resources.Font.values():
  d=f.DescendantFonts[0];fd=d.FontDescriptor
  if d.objgen in seen:continue
  seen.add(d.objgen);ft=TTFont(io.BytesIO(fd.FontFile2.read_bytes()),recalcTimestamp=False);old=ft['head'].unitsPerEm;scale_upem(ft,round(old*factor));ft['head'].unitsPerEm=old;buf=io.BytesIO();ft.save(buf);fd.FontFile2=pikepdf.Stream(p,buf.getvalue());fd.FontFile2.Length1=len(buf.getvalue())
  ww=list(d.W);new=[]
  for i in range(0,len(ww),2):new.extend([ww[i],pikepdf.Array([float(w)*factor for w in ww[i+1]])])
  d.W=pikepdf.Array(new)
 ops=[]
 for ins in pikepdf.parse_content_stream(pg):
  if str(ins.operator)=='Tm':
   a,b,c,d,e,f=map(float,ins.operands);ins=pikepdf.ContentStreamInstruction([a/factor,b/factor,c/factor,d/factor,e,f],pikepdf.Operator('Tm'))
  ops.append(ins)
 pg.Contents=pikepdf.Stream(p,pikepdf.unparse_content_stream(ops)+(b'\nET\n' if not any(str(i.operator)=='ET' for i in ops) else b''))
p.save(dst)
