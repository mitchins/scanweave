"""Diagnostic only: paint actual embedded outlines as paths, preserving hidden text.
Separates text rasterizer behavior from glyph geometry; not a product path.
"""
import io,sys
from pathlib import Path
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
class Pen(BasePen):
 def __init__(self,gs):super().__init__(gs);self.ops=[]
 def add(self,op,*v):self.ops.append(' '.join(map(str,v))+' '+op)
 def _moveTo(self,p):self.add('m',*p)
 def _lineTo(self,p):self.add('l',*p)
 def _curveToOne(self,a,b,c):self.add('c',*a,*b,*c)
 def _qCurveToOne(self,a,b):
  p=self._getCurrentPoint();self._curveToOne(tuple((p[i]+2*a[i])/3 for i in range(2)),tuple((b[i]+2*a[i])/3 for i in range(2)),b)
 def _closePath(self):self.add('h')
 def _endPath(self):pass
src=Path(sys.argv[1]);dst=Path(sys.argv[2]);pdf=pikepdf.open(src);cache={}
for pg in pdf.pages:
 ops=[];pending=[];mat=[1,0,0,1,0,0];mode=0;size=1;color='0 g';fname=None
 for ins in pikepdf.parse_content_stream(pg):
  op=str(ins.operator);v=ins.operands
  if op=='Tf':fname=str(v[0]);size=float(v[1])
  if op=='Tm':mat=list(map(float,v))
  if op=='Tr':mode=int(v[0])
  if op in ('rg','g'):color=' '.join(map(str,v))+' '+op
  if op=='Tj' and mode==0:
   f=pg.Resources.Font[fname].DescendantFonts[0];key=f.objgen
   if key not in cache:
    ft=TTFont(io.BytesIO(f.FontDescriptor.FontFile2.read_bytes()));cache[key]=(ft,f.CIDToGIDMap.read_bytes())
   ft,mp=cache[key];code=bytes(v[0]);assert len(code)==2;cid=int.from_bytes(code,'big');gid=int.from_bytes(mp[2*cid:2*cid+2],'big');gs=ft.getGlyphSet();pen=Pen(gs);gs[ft.getGlyphOrder()[gid]].draw(pen);up=ft['head'].unitsPerEm
   transform=[x*size/up for x in mat[:4]]+mat[4:];pending.append(('q\n'+' '.join(map(str,transform))+' cm\n'+color+'\n'+'\n'.join(pen.ops)+'\nf\nQ\n').encode())
   ops.append(b'3 Tr\n');ops.append(pikepdf.unparse_content_stream([ins]));ops.append(b'0 Tr\n');continue
  ops.append(pikepdf.unparse_content_stream([ins]))
  if op=='ET':ops.extend(pending);pending=[]
 if pending:ops.append(b"ET\n");ops.extend(pending)
 pg.Contents=pikepdf.Stream(pdf,b'\n'.join(ops))
pdf.save(dst)
