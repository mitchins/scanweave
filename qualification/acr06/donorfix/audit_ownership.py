#!/usr/bin/env python3
"""Audit PDF glyph outlines against source-owned masks at source pixel centers.

This is a geometric sampling audit, not an antialias-coverage proof. Source
ownership comes from a byte-checked diagnostic rerun of the candidate.
"""
import json,math,sys,os
from io import BytesIO
from pathlib import Path
import numpy as np,pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
q=Path('/data/coding/scanweave/qualification/acr06');loc=q/'local/donorfix';out=q/'donorfix';result={}
class Flatten(BasePen):
 def __init__(self,gs,trans):super().__init__(gs);self.trans=trans;self.paths=[];self.path=[];self.last=None
 def _moveTo(self,p):
  if self.path:self.paths.append(self.path)
  self.path=[self.trans(p)];self.last=p
 def _lineTo(self,p):self.path.append(self.trans(p));self.last=p
 def _qCurveToOne(self,c,p):
  a=self.last
  for t in np.linspace(1/12,1,12):self.path.append(self.trans(((1-t)**2*a[0]+2*(1-t)*t*c[0]+t*t*p[0],(1-t)**2*a[1]+2*(1-t)*t*c[1]+t*t*p[1])))
  self.last=p
 def _curveToOne(self,c1,c2,p):
  a=self.last
  for t in np.linspace(1/12,1,12):self.path.append(self.trans(((1-t)**3*a[0]+3*(1-t)**2*t*c1[0]+3*(1-t)*t*t*c2[0]+t**3*p[0],(1-t)**3*a[1]+3*(1-t)**2*t*c1[1]+3*(1-t)*t*t*c2[1]+t**3*p[1])))
  self.last=p
 def _closePath(self):
  if self.path:self.path.append(self.path[0]);self.paths.append(self.path);self.path=[]
 def _endPath(self):self._closePath()
def inside(paths,x,y):
 winding=np.zeros(x.shape,dtype=np.int16)
 for path in paths:
  for (x0,y0),(x1,y1) in zip(path,path[1:]):
   cross=(x1-x0)*(y-y0)-(x-x0)*(y1-y0)
   winding+=((y0<=y)&(y<y1)&(cross>0)).astype(np.int16)
   winding-=((y1<=y)&(y<y0)&(cross<0)).astype(np.int16)
 return winding!=0
def glyphs(page,rw,rh):
 media=list(map(float,page.MediaBox));ph=media[3]-media[1];sx=rw/(media[2]-media[0]);sy=rh/ph;fonts={}
 for name,f in page.Resources.Font.items():
  try:
   d=f.DescendantFonts[0];font=TTFont(BytesIO(d.FontDescriptor.FontFile2.read_bytes()));fonts[str(name)]=(font,font.getGlyphSet(),d.CIDToGIDMap.read_bytes(),font.getGlyphOrder())
  except (AttributeError,KeyError,IndexError):continue
 active=None;mat=None;mode=0
 for ins in pikepdf.parse_content_stream(page):
  op=str(ins.operator);args=ins.operands
  if op=='Tf':active=str(args[0])
  elif op=='Tr':mode=int(args[0])
  elif op=='Tm':mat=list(map(float,args))
  elif op=='Tj' and mode not in (3,7) and active in fonts and mat:
   raw=bytes(args[0]);font,gs,mapping,order=fonts[active]
   if len(raw)!=2:continue
   cid=int.from_bytes(raw,'big');ix=2*cid
   if ix+2>len(mapping):continue
   gid=int.from_bytes(mapping[ix:ix+2],'big')
   if gid>=len(order):continue
   pen=BoundsPen(gs);gs[order[gid]].draw(pen)
   if pen.bounds is None:continue
   a,b,c,d,e,f=mat;upem=font['head'].unitsPerEm
   trans=lambda p:((a*p[0]/upem+c*p[1]/upem+e)*sx,(ph-(b*p[0]/upem+d*p[1]/upem+f))*sy)
   x0,y0,x1,y1=pen.bounds;corners=[trans((x,y)) for x in (x0,x1) for y in (y0,y1)];bb=[min(t[0] for t in corners),min(t[1] for t in corners),max(t[0] for t in corners),max(t[1] for t in corners)]
   yield cid,gid,bb,gs,order[gid],trans
mode=os.environ.get('DONOR_AUDIT_MODE','candidate'); only=os.environ.get('DONOR_AUDIT_DOCUMENT')
for candidate in sorted((loc/'candidate').glob('*.pdf')):
 name=candidate.stem
 if only and name!=only: continue
 cp=candidate if mode=='candidate' else (loc/'main'/f'{name}.pdf' if (loc/'main'/f'{name}.pdf').exists() else loc/'baseline'/('single.pdf' if name=='single' else f'{name}-off.pdf'))
 capture=loc/'ownership'/name
 if not (capture/'capture.pdf').exists():continue
 # The capture must produce exactly the same PDF, not merely a similar plan.
 import hashlib
 reference=loc/'candidate-v1'/f'{name}.pdf'; reference=reference if reference.exists() else cp
 same=hashlib.sha256(reference.read_bytes()).digest()==hashlib.sha256((capture/'capture.pdf').read_bytes()).digest(); report=json.loads(Path(str(cp)+'.json').read_text()); capture_report=json.loads((capture/'capture.pdf.json').read_text()); provenance=(report['input_sha256']==capture_report['input_sha256'] and [p['pixel_sha256'] for p in report['pages']]==[p['pixel_sha256'] for p in capture_report['pages']] and [p['reconstruction']['observations'] for p in report['conversion']['page_reports']]==[p['reconstruction']['observations'] for p in capture_report['conversion']['page_reports']]);pdf=pikepdf.open(cp);pages=[]
 for pi,page in enumerate(pdf.pages):
  pr=report['conversion']['page_reports'][pi];f=capture/(pr['page_id']+'.json')
  if not f.exists():pages.append({'page_index':pi,'missing_snapshot':True});continue
  snap=json.loads(f.read_text());units=snap['owned'];art=snap['artwork'];owner={o['symbol_id']:o['owner'] for o in pr['occurrences']};occ={o['symbol_id']:o for o in pr['reconstruction']['occurrences']}; targets=[]
  for u in units:
   if not owner.get(u['id'],'').startswith('visible'):continue
   r=occ.get(u['id'],{}); placed=r.get('replacement_bbox_px') if r.get('repaired') or r.get('reused') else None;targets.append((u['id'],placed or u['bbox']))
  if not targets:pages.append({'page_index':pi,'glyphs':0,'unmatched':0,'overlaps':[]});continue
  tb=np.array([x[1] for x in targets]);overlaps=[];unmatched=0;count=0
  for cid,gid,bb,gs,gname,trans in glyphs(page,snap['width'],snap['height']):
   count+=1;dist=np.abs(tb-np.array(bb)).sum(axis=1);idx=int(np.argmin(dist)); target=targets[idx][0] if dist[idx]<=12 else None
   if target is None:unmatched+=1;continue
   neighbors=[u for u in units+art if u['id']!=target and u['bbox'][0]<bb[2] and bb[0]<u['bbox'][2] and u['bbox'][1]<bb[3] and bb[1]<u['bbox'][3]]
   if not neighbors:continue
   pen=Flatten(gs,trans);gs[gname].draw(pen);pen._endPath()
   for u in neighbors:
    w=int(u['width']);h=int(u['height']);bits=np.unpackbits(np.array(u['bits'],dtype=np.uint8),bitorder='little',count=w*h).reshape((h,w));ys,xs=np.nonzero(bits);xs=xs+u['bbox'][0]+.5;ys=ys+u['bbox'][1]+.5;keep=(xs>=bb[0])&(xs<bb[2])&(ys>=bb[1])&(ys<bb[3]); xs=xs[keep];ys=ys[keep]
    if not len(xs):continue
    n=int(inside(pen.paths,xs,ys).sum())
    if n:overlaps.append({'symbol_id':target,'neighbor_id':u['id'],'cid':cid,'gid':gid,'pixels':n,'bbox':bb,'match_error':float(dist[idx])})
  pages.append({'page_index':pi,'glyphs':count,'unmatched':unmatched,'overlaps':overlaps})
 result[name]={'capture_pdf_matches_reference':same,'source_ocr_observations_match':provenance,'pages':pages};(out/('ownership-audit.json' if mode=='candidate' else 'ownership-audit-main.json')).write_text(json.dumps(result,indent=2)+'\n');print(name,'identical',same,'glyphs',sum(p.get('glyphs',0) for p in pages),'overlaps',sum(len(p.get('overlaps',[])) for p in pages),flush=True)
