"""Exercise an embedded research Type3 font in an extraction-neutral pattern on a control PDF."""
import pathlib,pikepdf,pypdfium2 as pdfium,subprocess,json,hashlib,numpy as np
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';base=R/'local/hvc41b/controls/control/white/baseline.pdf';o=json.loads((R/'local/hvc41b/controls/control/white/p000001-outlines.json').read_text())['outlines'][0]
def extract(p):
 d=pdfium.PdfDocument(str(p));pg=d[0];t=pg.get_textpage();s=t.get_text_range();arr=np.asarray(pg.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB')).copy();t.close();pg.close();d.close();return s,subprocess.check_output(['pdftotext','-layout',str(p),'-']).decode(),arr
def pdf_path(svg):
 pen=RecordingPen();parse_path(svg,pen);ops=[];current=None;start=None
 for op,points in pen.value:
  if op=='moveTo':current=points[0];start=current;ops.append(f'{current[0]} {current[1]} m')
  elif op=='lineTo':current=points[0];ops.append(f'{current[0]} {current[1]} l')
  elif op=='qCurveTo':
   if len(points)!=2 or points[-1] is None:raise ValueError('unsupported quadratic sequence')
   ctrl,end=points;c1=(current[0]+2*(ctrl[0]-current[0])/3,current[1]+2*(ctrl[1]-current[1])/3);c2=(end[0]+2*(ctrl[0]-end[0])/3,end[1]+2*(ctrl[1]-end[1])/3);ops.append(f'{c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]} c');current=end
  elif op=='curveTo':a,b,c=points;ops.append(f'{a[0]} {a[1]} {b[0]} {b[1]} {c[0]} {c[1]} c');current=c
  elif op=='closePath':ops.append('h');current=start
  else:raise ValueError(op)
 return ' '.join(ops)
ref=extract(base);pdf=pikepdf.open(base);pg=pdf.pages[0];g=pdf.make_stream(('2048 0 d0 '+pdf_path(o['path_svg'])+' f').encode());font=pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.Type3,Name=pikepdf.Name.FResearch,FontBBox=pikepdf.Array([-32768,-32768,32767,32767]),FontMatrix=pikepdf.Array([1/2048,0,0,1/2048,0,0]),CharProcs=pikepdf.Dictionary(g=g),Encoding=pikepdf.Dictionary(Type=pikepdf.Name.Encoding,Differences=pikepdf.Array([1,pikepdf.Name.g])),FirstChar=1,LastChar=1,Widths=pikepdf.Array([2048]),Resources=pikepdf.Dictionary());font=pdf.make_indirect(font);mt=' '.join(str(x) for x in o['matrix']);pat=pdf.make_stream(f'BT /FR 1 Tf 1 0 0 rg {mt} Tm <01> Tj ET'.encode());pat.Type=pikepdf.Name.Pattern;pat.PatternType=1;pat.PaintType=1;pat.TilingType=1;pat.BBox=pikepdf.Array([0,0,432,576]);pat.XStep=432;pat.YStep=576;pat.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(FR=font));pg.Resources.Pattern=pikepdf.Dictionary(Research=pat);pg.Contents=pikepdf.Array([pg.Contents,pdf.make_stream(b'q /Pattern cs /Research scn 170 478 11 25 re f Q')]);f=L/'type3-control.pdf';pdf.save(f);pdf.close();v=extract(f);diff=np.any(ref[2]!=v[2],axis=2);ys,xs=np.nonzero(diff);out={'pdfium_equal':v[0]==ref[0],'poppler_equal':v[1]==ref[1],'changed_pixels':int(diff.sum()),'changed_bbox_source_px':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if xs.size else None,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()};(E/'type3-control-probe.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
