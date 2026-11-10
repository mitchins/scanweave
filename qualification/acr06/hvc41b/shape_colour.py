#!/usr/bin/env python3
"""Render isolated pre-font-quantization paths; diagnostics only, never admission."""
import json,pathlib,math,collections,sys
import numpy as np
from PIL import Image
import pikepdf,pypdfium2 as pdfium
from fontTools.svgLib.path import parse_path
from fontTools.pens.basePen import BasePen
N=int(sys.argv[1]);mode='interior' if N==1 else 'border';R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41b';E=R/'hvc41b';D=json.loads((L/mode/f'p{N:06}-outlines.json').read_text());ledger={x['symbol']:x for x in json.loads((E/f'admission-ledger-{N:02}.json').read_text())};props=[x for x in D['outlines'] if x['symbol'] in ledger];src=np.asarray(Image.open(R/'local/ink33r/renders/historical'/f'{N:02}-source.png').convert('RGB'));ref=np.asarray(Image.open(R/'local/hvc41/masks'/f'corpus-historical-{N:02}-reference-ink.png').convert('L'))>0;hh,ww=src.shape[:2];orig=pdfium.PdfDocument(str(R/'local/ink33r/historical.pdf'));page=orig[N-1];pw,ph=page.get_size();page.close();orig.close();sx=pw/ww;sy=ph/hh;wt=np.array([.2126,.7152,.0722]);records=[]
class PdfPen(BasePen):
 def __init__(self,mat,offset):super().__init__(None);self.m=mat;self.off=offset;self.ops=[];self.current=None
 def pt(self,p):return (self.m[0]*p[0]/2048+self.m[4]-self.off[0],self.m[3]*p[1]/2048+self.m[5]-self.off[1])
 def emit(self,p,cmd):
  pts=[self.pt(v) for v in p];self.ops.append(' '.join(f'{n:.6f}' for pair in pts for n in pair)+' '+cmd)
 def _moveTo(self,p):self.emit([p],'m');self.current=p
 def _lineTo(self,p):self.emit([p],'l');self.current=p
 def _curveToOne(self,a,b,c):self.emit([a,b,c],'c');self.current=c
 def _qCurveToOne(self,a,b):
  x,y=self.current;c1=(x+2*(a[0]-x)/3,y+2*(a[1]-y)/3);c2=(b[0]+2*(a[0]-b[0])/3,b[1]+2*(a[1]-b[1])/3);self.emit([c1,c2,b],'c');self.current=b
 def _closePath(self):self.ops.append('h')
 def _endPath(self):pass
page_ink=json.loads((E/'p3-source-ink.json').read_text())['source_text_ink_rgb'] if N==3 else D['ink'];pdfs={k:pikepdf.Pdf.new() for k in ('shape','global','page','local')}
for item in props:
 info=ledger[item['symbol']]; x0,y0,x1,y1=map(int,item['bbox']);x0=max(0,x0-10);y0=max(0,y0-10);x1=min(ww,x1+10);y1=min(hh,y1+10);tw=(x1-x0)*sx;th=(y1-y0)*sy;off=(x0*sx,ph-y1*sy);pen=PdfPen(item['matrix'],off);parse_path(item['path_svg'],pen)
 local=info['source_supported_ink_rgb'];colors={'shape':[0,0,0],'global':D['ink'],'page':page_ink,'local':local or [0,0,0]}
 for kind,pdf in pdfs.items():
  pg=pdf.add_blank_page(page_size=(tw,th));rgb=colors[kind];data='q 1 1 1 rg 0 0 %.6f %.6f re f %.6f %.6f %.6f rg\n%s\nf Q\n'%(tw,th,*[c/255 for c in rgb],'\n'.join(pen.ops));pg.obj['/Contents']=pdf.make_stream(data.encode())
 records.append({'page':N,'symbol':item['symbol'],'ocr_char_unverified':item['text'],'bbox':item['bbox'],'tile_box':[x0,y0,x1,y1],'global_ink_rgb':D['ink'],'page_ink_rgb':page_ink,'local_ink_rgb':local,'region_admitted':info['region_admitted'],'note':'Pre-font-quantization shape.path rendered as an isolated PDF path. Not a rendered emitted font glyph; not proof of character correctness.'})
for kind,pdf in pdfs.items():pdf.save(L/f'p{N}-{kind}-tiles.pdf');pdf.close()
shape=pdfium.PdfDocument(str(L/f'p{N}-shape-tiles.pdf'))
for i,r in enumerate(records):
 x0,y0,x1,y1=r['tile_box'];pg=shape[i];im=pg.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB');pg.close();arr=np.asarray(im);m=(arr@wt)<128;target=ref[y0:y1,x0:x1];mh=min(m.shape[0],target.shape[0]);mw=min(m.shape[1],target.shape[1]);m=m[:mh,:mw];target=target[:mh,:mw];gx0,gy0,gx1,gy1=map(int,r['bbox']);roi=np.zeros_like(m,dtype=bool);roi[max(0,gy0-y0):min(mh,gy1-y0),max(0,gx0-x0):min(mw,gx1-x0)]=True;outside=np.zeros_like(m,dtype=bool);outside[max(0,gy0-y0-1):min(mh,gy1-y0+1),max(0,gx0-x0-1):min(mw,gx1-x0+1)]=True;r['painted_pixels_outside_expanded_bbox']=int((m&~outside).sum());m &= roi;target &= roi;u=int(np.count_nonzero(m|target));r['shape_proxy_iou']=float(np.count_nonzero(m&target)/u) if u else None
 if r['local_ink_rgb'] is not None:r['global_vs_local_luma_abs']=abs(float((np.array(r['global_ink_rgb'])-np.array(r['local_ink_rgb']))@wt));r['page_vs_local_luma_abs']=abs(float((np.array(r['page_ink_rgb'])-np.array(r['local_ink_rgb']))@wt))
 r['outcome']='rejected by frozen region admission; no vector emitted';r['residual_check']='not applicable: isolated diagnostic; no source ink removed'
shape.close();(E/f'p{N}-shape-colour.json').write_text(json.dumps(records,indent=2)+'\n');print('page',N,'diagnostic outlines',len(records),flush=True)
