"""Small Type 3 font for isolated research outlines; never changes ScanWeave defaults."""
import pikepdf
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen

def pdf_path(svg):
 p=RecordingPen();parse_path(svg,p);ops=[];cur=None;start=None
 for op,points in p.value:
  if op=='moveTo':cur=points[0];start=cur;ops.append(f'{cur[0]} {cur[1]} m')
  elif op=='lineTo':cur=points[0];ops.append(f'{cur[0]} {cur[1]} l')
  elif op=='qCurveTo':
   if len(points)!=2 or points[-1] is None:raise ValueError('unsupported quadratic sequence')
   ctrl,end=points;c1=(cur[0]+2*(ctrl[0]-cur[0])/3,cur[1]+2*(ctrl[1]-cur[1])/3);c2=(end[0]+2*(ctrl[0]-end[0])/3,end[1]+2*(ctrl[1]-end[1])/3);ops.append(f'{c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]} c');cur=end
  elif op=='curveTo':a,b,c=points;ops.append(f'{a[0]} {a[1]} {b[0]} {b[1]} {c[0]} {c[1]} c');cur=c
  elif op=='closePath':ops.append('h');cur=start
  else:raise ValueError(op)
 return ' '.join(ops)

def pattern(pdf,proposals,page_width,page_height):
 if not 0<len(proposals)<=255:raise ValueError('font capacity exceeded')
 procs=pikepdf.Dictionary();diff=pikepdf.Array([1]);ops=[]
 for index,g in enumerate(proposals,1):
  name='g'+str(index);procs['/'+name]=pdf.make_stream(('2048 0 d0 '+pdf_path(g['outline']['path_svg'])+' f').encode());diff.append(pikepdf.Name('/'+name));m=' '.join(str(x) for x in g['outline']['matrix']);rgb=' '.join(f'{x/255:.8f}' for x in g['fill_rgb']);ops.append(f'BT /FR 1 Tf {rgb} rg {m} Tm <{index:02x}> Tj ET')
 font=pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.Type3,Name=pikepdf.Name.FResearch,FontBBox=pikepdf.Array([-32768,-32768,32767,32767]),FontMatrix=pikepdf.Array([1/2048,0,0,1/2048,0,0]),CharProcs=procs,Encoding=pikepdf.Dictionary(Type=pikepdf.Name.Encoding,Differences=diff),FirstChar=1,LastChar=len(proposals),Widths=pikepdf.Array([2048]*len(proposals)),Resources=pikepdf.Dictionary()))
 pat=pdf.make_stream(('\n'.join(ops)).encode());pat.Type=pikepdf.Name.Pattern;pat.PatternType=1;pat.PaintType=1;pat.TilingType=1;pat.BBox=pikepdf.Array([0,0,page_width,page_height]);pat.XStep=page_width;pat.YStep=page_height;pat.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(FR=font));return pat
