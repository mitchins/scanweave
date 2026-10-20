#!/usr/bin/env python3
"""Evaluator-only known-outline control within the existing emitted PDF/font contract.
Replaces the existing embedded glyf program and text matrices; never called by
the converter. Uses known generator positions and original font design metrics,
not an independent fit of each glyph to the pristine bitmap bounds.
"""
import copy,io,json,argparse
from pathlib import Path
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import ImageFont
ROOT=Path(__file__).resolve().parents[2]
TEXT='e8a0g6e,a; 8e0ag6! e8a0g6e,a; 8e0ag6?'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('dpi',type=int);ap.add_argument('pdf',type=Path);a=ap.parse_args();scale=a.dpi/300;pt=72/a.dpi;base=ROOT/f'qualification/experiments/m1g/fixture/dpi{a.dpi}';pdf=pikepdf.open(a.pdf);audit=[]
 for pi,page in enumerate(pdf.pages):
  truth=json.loads((base/'oracle'/f'page{pi:02}.truth.json').read_text());ocr=json.loads((base/'input'/f'page{pi:02}.ocr.json').read_text());sid_order=ocr['reading_order'];records={r['id']:r for r in truth['records']};sources={};positions={}
  for row in range(2):
   x=70*scale;y=(75+178*row)*scale;font=ImageFont.truetype(truth['font'],round(44*scale));ascent=font.getmetrics()[0]
   for j,ch in enumerate(TEXT):
    sid=f'p{pi:02}s{row*len(TEXT)+j:04}';positions[sid]=(truth['font'],ch,x,y+ascent,44*scale);x+=int(font.getlength(ch))+7*scale
  if pi==0:
   fp='/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf';font=ImageFont.truetype(fp,round(30*scale));x=75*scale
   for j,ch in enumerate('かなカナかなカナ'):
    sid=f'p00kana{2*len(TEXT)+j:03}';positions[sid]=(fp,ch,x,710*scale+font.getmetrics()[0],30*scale);x+=int(font.getlength(ch))+5*scale
  old=page.Resources.Font.F1;desc=old.DescendantFonts[0];raw=desc.FontDescriptor.FontFile2.read_bytes();ft=TTFont(io.BytesIO(raw));order=ft.getGlyphOrder();mapping=desc.CIDToGIDMap.read_bytes();insns=pikepdf.parse_content_stream(page);cursor=0;sid=None;mode=0;last_matrix=None;assigned={};modified=[];widths={};in_text=False
  for ix,ins in enumerate(insns):
   op=str(ins.operator);v=ins.operands
   if op=='BT':in_text=True
   elif op=='ET':in_text=False
   elif op=='rg' and in_text:insns[ix]=pikepdf.ContentStreamInstruction([15/255]*3,pikepdf.Operator('rg'))
   if op=='BDC' and len(v)>1 and isinstance(v[1],pikepdf.Dictionary) and '/ActualText' in v[1]:sid=sid_order[cursor];cursor+=1
   elif op=='Tr':mode=int(v[0])
   elif op=='Tm':last_matrix=ix
   elif op=='Tj' and mode==0 and sid in positions:
    code=bytes(v[0]);cid=int.from_bytes(code,'big');gid=int.from_bytes(mapping[cid*2:cid*2+2],'big');fp,ch,x,baseline,size=positions[sid];key=(fp,ch)
    if gid in assigned and assigned[gid]!=key:raise ValueError(('oracle GID conflict',pi,gid,assigned[gid],key))
    assigned[gid]=key
    if fp not in sources:sources[fp]=TTFont(fp)
    src=sources[fp];name=src.getBestCmap()[ord(ch)];gs=src.getGlyphSet();rec=DecomposingRecordingPen(gs);gs[name].draw(rec);pen=TTGlyphPen(None);rec.replay(TransformPen(pen,(2048/src['head'].unitsPerEm,0,0,2048/src['head'].unitsPerEm,0,0)));ft['glyf'][order[gid]]=pen.glyph();ft['hmtx'].metrics[order[gid]]=(round(src['hmtx'][name][0]*2048/src['head'].unitsPerEm),round(src['hmtx'][name][1]*2048/src['head'].unitsPerEm))
    widths[cid]=src['hmtx'][name][0]*1000/src['head'].unitsPerEm
    mat=[size*pt,0,0,size*pt,x*pt,(900*scale-baseline)*pt];insns[last_matrix]=pikepdf.ContentStreamInstruction(mat,pikepdf.Operator('Tm'));modified.append(sid)
  data=io.BytesIO();ft.save(data);fd=pikepdf.Dictionary(desc.FontDescriptor);stream=pikepdf.Stream(pdf,data.getvalue());stream.Length1=len(data.getvalue());fd.FontFile2=stream;fd.FontBBox=pikepdf.Array([-2048,-2048,4096,4096]);d=pikepdf.Dictionary(desc);d.FontDescriptor=pdf.make_indirect(fd);d.W=pikepdf.Array([v for cid,width in sorted(widths.items()) for v in (cid,pikepdf.Array([width]))]);f=pikepdf.Dictionary(old);f.DescendantFonts=pikepdf.Array([pdf.make_indirect(d)]);fonts=pikepdf.Dictionary(page.Resources.Font);fonts.F1=pdf.make_indirect(f);resources=pikepdf.Dictionary(page.Resources);resources.Font=fonts;page.Resources=resources
  # Same compositor/preserved layers and semantics as the completed converter.
  page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(insns));audit.append({'page':pi,'oracle_replaced_instances':modified,'source_fonts':list(sources),'unique_design_glyphs':len(assigned)})
 out=ROOT/f'qualification/clearscan_competitive/{a.dpi}/oracle-assembly.pdf';pdf.save(out);out.with_suffix('.json').write_text(json.dumps(audit,indent=2));print(out)
 for page in pdf.pages:
  page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream([i for i in pikepdf.parse_content_stream(page) if str(i.operator)!='Do']))
 pdf.save(out.with_name('oracle-vector-only.pdf'))
if __name__=='__main__':main()
