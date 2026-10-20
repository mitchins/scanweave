#!/usr/bin/env python3
"""Stage audit using actual embedded fonts. Oracle read only by evaluator.
S1-S3 are measured at the witness's original physical geometry (no independent
oracle bbox fit); S4-S5 at the actual target position. Reported populations differ.
"""
import argparse,json,sys,subprocess,math
from pathlib import Path
import numpy as np
from PIL import Image
import pikepdf,pypdfium2 as pdfium
sys.path.insert(0,str(Path(__file__).parent));from compare import iou
ROOT=Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('dpi',type=int);ap.add_argument('arm');ap.add_argument('pdf',type=Path);ap.add_argument('report',type=Path);a=ap.parse_args();dpi=a.dpi;pt=72/dpi
 base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}';out=ROOT/f'qualification/clearscan_competitive/{dpi}/{a.arm}/stages';out.mkdir(parents=True,exist_ok=True)
 report=json.loads(a.report.read_text());p=pikepdf.open(a.pdf);s4=pikepdf.open(a.pdf);s3=pikepdf.Pdf.new();rows=[];witness_rows=[]
 sources=[np.asarray(Image.open(base/'input'/f'page{i:02}.png').convert('L')) for i in range(len(p.pages))];truths=[np.asarray(Image.open(base/'oracle'/f'page{i:02}.png').convert('L')) for i in range(len(p.pages))]
 for pi,page in enumerate(p.pages):
  pr=report['page_reports'][pi];recon=pr['reconstruction'];records={r['symbol_id']:r for r in recon['occurrences']};geometry={g['prototype_id']:g for g in recon['canonical_geometry']};ocr=json.loads((base/'input'/f'page{pi:02}.ocr.json').read_text());ordered=[s for sid in ocr['reading_order'] for s in ocr['spans'] if s['id']==sid];cursor=0;sid=None;mode=0;mat=None;cid=None;draws=[];used=set();commands=[];color=[0,0,0]
  for ins in pikepdf.parse_content_stream(page):
   op=str(ins.operator);oper=ins.operands
   if op=='BDC' and len(oper)>1 and isinstance(oper[1],pikepdf.Dictionary) and '/ActualText' in oper[1]:
    text=str(oper[1].ActualText)
    if cursor<len(ordered):
     span=ordered[cursor];cursor+=1;sid=span['id']
     if span['text']!=text:raise ValueError(('span mapping mismatch',pi,span['text'],text))
   elif op=='Tr':mode=int(oper[0])
   elif op=='Tm':mat=list(map(float,oper))
   elif op=='Tf':font=str(oper[0])
   elif op=='rg':color=list(map(float,oper))
   elif op=='Tj' and mode==0 and sid in records:
    rec=records[sid];gid=rec.get('prototype_id');code=bytes(oper[0]);draws.append((sid,mat,code,font,gid,rec.get('replacement_bbox_px'),geometry.get(gid)));
    if gid in geometry and gid not in used:
     used.add(gid);g=geometry[gid];wx0,wy0,wx1,wy1=g['witness_bbox_px'];sx=(wx1-wx0)*pt*2048/g['ink_span_fu'][0];sy=(wy1-wy0)*pt*2048/g['ink_span_fu'][1];tx=wx0*pt-g['anchor_bbox_fu'][0]*sx/2048;ty=(sources[pi].shape[0]-wy1)*pt-g['anchor_bbox_fu'][1]*sy/2048
     tile=s3.add_blank_page(page_size=(72,72))  # Integer-point canvas prevents tiny-tile ceil changing vertical phase.
     tile.Resources=s3.copy_foreign(p.make_indirect(page.Resources))
     tx=4*pt-g['anchor_bbox_fu'][0]*sx/2048;ty=float(tile.MediaBox[3])-(g['height']+4)*pt-g['anchor_bbox_fu'][1]*sy/2048
     tile.Contents=pikepdf.Stream(s3,(f"BT {font} 1 Tf {' '.join(map(str,color))} rg {sx} 0 0 {sy} {tx} {ty} Tm <{code.hex()}> Tj ET").encode())
     witness_rows.append({'tile':len(s3.pages)-1,'target_page':pi,'prototype':gid,'witness':g['witness_symbol_id'],'bbox':g['witness_bbox_px'],'geometry':g})
  # Removing only XObject Do leaves the original text placement/font assembly.
  ops=[ins for ins in pikepdf.parse_content_stream(page) if str(ins.operator)!='Do'];s4.pages[pi].Contents=pikepdf.Stream(s4,pikepdf.unparse_content_stream(ops))
  for sid,mat,code,font,gid,box,g in draws:rows.append({'page':pi,'id':sid,'prototype':gid,'matrix':mat,'construction_bbox':box,'_geometry':g})
 s4.save(out/'S4-vector-only.pdf');s3.save(out/'S3-nominal-witness.pdf');s4doc=pdfium.PdfDocument(str(out/'S4-vector-only.pdf'));s3doc=pdfium.PdfDocument(str(out/'S3-nominal-witness.pdf'));final=pdfium.PdfDocument(str(a.pdf));arr4=[np.asarray(pg.render(scale=math.nextafter(dpi/72,0.0)).to_pil().convert('L')) for pg in s4doc];arr3=[np.asarray(pg.render(scale=math.nextafter(dpi/72,0.0)).to_pil().convert('L')) for pg in s3doc];arr5=[np.asarray(pg.render(scale=math.nextafter(dpi/72,0.0)).to_pil().convert('L')) for pg in final]
 for row in rows:
  pi=row['page'];truth=json.loads((base/'oracle'/f'page{pi:02}.truth.json').read_text());rec=next((r for r in truth['records'] if r['id']==row['id']),None)
  if rec is None or not rec['text'].strip():continue
  x0,y0,x1,y1=map(int,rec['bbox']);pad=round((4 if ord(rec['text'][0])>127 else 5)*dpi/300);sl=(slice(y0+pad,y1-pad),slice(x0+pad,x1-pad));row['text']=rec['text'];row['S0']=iou(sources[pi][sl],truths[pi][sl]);row['S4']=iou(arr4[pi][sl],truths[pi][sl]);row['S5']=iou(arr5[pi][sl],truths[pi][sl]);row['composition_delta']=row['S5']-row['S4']
  g=row.pop('_geometry',None);box=row['construction_bbox']
  if g and box:
   sid=g['witness_symbol_id'].split(':')[-1];wp=int(sid[1:3]);wx0,wy0,wx1,wy1=map(int,g['witness_bbox_px']);donor=Image.fromarray(sources[wp][wy0:wy1,wx0:wx1]);mask=Image.fromarray(np.where(np.asarray(g['mask']).reshape(g['height'],g['width']),0,255).astype('uint8'))
   # Map through inferred construction geometry, never a pristine bbox fit.
   bx0,by0,bx1,by1=box;sx=g['width']/(bx1-bx0);sy=g['height']/(by1-by0)
   for key,img in [('S1_placed',donor),('S2_placed',mask)]:
    mapped=img.transform((sources[pi].shape[1],sources[pi].shape[0]),Image.Transform.AFFINE,(sx,0,-bx0*sx,0,sy,-by0*sy),resample=Image.Resampling.BILINEAR,fillcolor=255);row[key]=iou(np.asarray(mapped)[sl],truths[pi][sl])
 for row in witness_rows:
  g=row.pop('geometry');sid=row['witness'].split(':')[-1];pi=int(sid[1:3]);x0,y0,x1,y1=map(int,row['bbox']);target=truths[pi][y0:y1,x0:x1];row['S1']=iou(sources[pi][y0:y1,x0:x1],target);mask=np.asarray(g['mask']).reshape(g['height'],g['width']);row['S2']=iou(np.where(mask,0,255),target);row['S3']=iou(arr3[row['tile']][4:4+g['height'],4:4+g['width']],target)
 for row in rows:row.pop('_geometry',None)
 result={'populations':'S1-S3 unique prototype witnesses per page; S0,S4,S5 actual emitted occurrence set. S1_placed/S2_placed are grayscale/mask diagnostic rasters mapped to the same inferred replacement box, not PDF renders. No oracle normalization. S3 uses isolated nominal-geometry tiles with the actual font and actual ink color.','occurrences':rows,'witnesses':witness_rows,'means':{k:float(np.mean([r[k] for r in (witness_rows if k in ['S1','S2','S3'] else rows) if k in r])) for k in ['S0','S1','S2','S3','S1_placed','S2_placed','S4','S5','composition_delta']}}
 (out/'stage-errors.json').write_text(json.dumps(result,indent=2));print(result['means'])
if __name__=='__main__':main()
