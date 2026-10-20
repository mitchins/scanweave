#!/usr/bin/env python3
"""Audit actual painted font/image resources and occurrence ownership."""
import argparse, io, json, hashlib, re
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from PIL import Image

B=Path(__file__).resolve().parent
ROOT=B.parents[1]
def audit(dpi, arm, path, report_path=None):
    p=pikepdf.open(path);counts=Counter();paths=Counter();rows=[];images={};classes=Counter();assign=[]
    report=json.loads(report_path.read_text()) if report_path else None
    ft_cache={};cff_cache={};shown_codes=0
    for pi,page in enumerate(p.pages):
        fonts=page.Resources.get('/Font',{}); mode=0; matrix=None; font=None; symbol=None; cursor=0
        pr=report['page_reports'][pi] if report else None
        recs={r['symbol_id']:r for r in pr['reconstruction']['occurrences']} if pr else {}
        ordered=json.loads((ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page{pi:02}.ocr.json').read_text())['reading_order'] if pr else []
        truth=json.loads((ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/oracle/page{pi:02}.truth.json').read_text()) if pr else None
        truthmap={r['id']:r for r in truth['records']} if truth else {}
        for ins in pikepdf.parse_content_stream(page):
            op=str(ins.operator);v=ins.operands
            if op=='Tr':mode=int(v[0])
            elif op=='Tf':font=fonts[str(v[0])]
            elif op=='Tm':matrix=list(map(float,v))
            elif op=='BDC' and len(v)>1 and isinstance(v[1],pikepdf.Dictionary) and '/ActualText' in v[1] and pr:
                symbol=ordered[cursor];cursor+=1
            elif op in ('Tj','TJ') and mode in (0,1,2) and font is not None:
                ss=[v[0]] if op=='Tj' else [x for x in v[0] if isinstance(x,pikepdf.String)]
                desc=font.get('/DescendantFonts',[font])[0];fd=desc.get('/FontDescriptor',{});stream=fd.get('/FontFile2');fk=tuple(font.objgen)
                ft=None;cff=None
                if stream is not None:
                    key=tuple(stream.objgen)
                    if key not in ft_cache:ft_cache[key]=TTFont(io.BytesIO(stream.read_bytes()))
                    ft=ft_cache[key]
                elif fd.get('/FontFile3') is not None:
                    from fontTools.cffLib import CFFFontSet
                    stream=fd.FontFile3;key=tuple(stream.objgen)
                    if key not in cff_cache:
                        c=CFFFontSet();c.decompile(io.BytesIO(stream.read_bytes()),None);cff_cache[key]=c[c.fontNames[0]]
                    cff=cff_cache[key]
                program_hash=hashlib.sha256(stream.read_bytes()).hexdigest() if stream is not None else str(fk)
                for s in ss:
                    data=bytes(s);step=2 if font.get('/Subtype')=='/Type0' else 1
                    for i in range(0,len(data),step):
                        cid=int.from_bytes(data[i:i+step],'big');gid=cid
                        mapping=desc.get('/CIDToGIDMap')
                        if isinstance(mapping,pikepdf.Stream):gid=int.from_bytes(mapping.read_bytes()[cid*2:cid*2+2],'big')
                        shown_codes+=1;k=f'{program_hash}:{gid}'
                        row={'page':pi,'symbol':symbol,'cid':cid,'gid':gid,'font':fk,'matrix':matrix}
                        if ft is not None:
                            name=ft.getGlyphOrder()[gid];pen=RecordingPen();ft.getGlyphSet()[name].draw(pen);h=hashlib.sha256(repr(pen.value).encode()).hexdigest();paths[h]+=1;row['outline_hash']=h
                            g=ft['glyf'][name]
                            if g.numberOfContours and matrix:
                                a,b,c,d,e,f=matrix;u=ft['head'].unitsPerEm
                                row['bbox_px']=[(e+a*g.xMin/u)*dpi/72, (float(page.MediaBox[3])-f-d*g.yMax/u)*dpi/72,(e+a*g.xMax/u)*dpi/72,(float(page.MediaBox[3])-f-d*g.yMin/u)*dpi/72]
                                if symbol in truthmap:
                                    t=truthmap[symbol];pad=(4 if ord(t['text'][0])>127 else 5)*dpi/300;bb=t['bbox'];target=[bb[0]+pad,bb[1]+pad,bb[2]-pad,bb[3]-pad];x=row['bbox_px'];row['design_vs_hinted_truth_delta_px']=[x[j]-target[j] for j in range(4)]
                        if cff is not None:
                            name=f'cid{cid:05d}';pen=RecordingPen();cff.CharStrings[name if name in cff.CharStrings.charStrings else '.notdef'].draw(pen);h=hashlib.sha256(repr(pen.value).encode()).hexdigest();paths[h]+=1;row['outline_hash']=h
                        has_ink=bool(pen.value) if ft is not None or cff is not None else True
                        if not has_ink:
                            if row.get('outline_hash'):paths[row['outline_hash']]-=1
                            continue
                        counts[k]+=1;rows.append(row)
                        if pr and symbol in recs:
                            r=recs[symbol];pid=r.get('prototype_id');g=next((g for g in pr['reconstruction'].get('canonical_geometry',[]) if g['prototype_id']==pid),None)
                            if g:
                                sid=g['witness_symbol_id'].split(':')[-1];wp=int(sid[1:3]);wt=json.loads((ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/oracle/page{wp:02}.truth.json').read_text());w=next(t for t in wt['records'] if t['id']==sid);assign.append({'page':pi,'symbol':symbol,'text':r['text'],'witness':sid,'witness_text':w['text'],'same_identity':r['text']==w['text'],'same_typeface':truth['font']==wt['font'],'prototype':pid})
        if pr:
            patches=pr['patches'];resources=[v for k,v in sorted(page.Resources.get('/XObject',{}).items(),key=lambda kv:int(str(kv[0]).removeprefix('/Im')))]
            # Writer numbers images in patch order. Classify actual object bytes,
            # not an inferred share of a compressed stream's source pixels.
            for patch,obj in zip(patches,resources):
                if obj.get('/Subtype')!='/Image':continue
                key=tuple(obj.objgen);bb=patch['bbox_px'];w=patch['w'];h=patch['h'];kind='native_fallback_artwork_unknown'
                if bb[0]==0 and bb[1]==0 and w<bb[2] and h<bb[3]:kind='residual_background'
                if key not in images:images[key]={'bytes':len(obj.read_raw_bytes()),'class':kind,'bbox':bb,'dimensions':[w,h],'filter':str(obj.get('/Filter'))}
    for im in images.values():classes[im['class']]+=im['bytes']
    paths=Counter({k:v for k,v in paths.items() if v>0})
    return {'shown_character_codes':shown_codes,'painted_occurrences':len(rows),'used_font_gids':len(counts),'distinct_painted_outline_hashes':len(paths) if paths else None,'outline_reuse':dict(paths),'gid_reuse':dict(counts),'placements':rows,'resource_bytes_by_class':dict(classes),'resource_classes':list(images.values()),'assignments':assign,'wrong_witness_identity':sum(not r['same_identity'] for r in assign),'wrong_witness_typeface':sum(not r['same_typeface'] for r in assign),'scope':'Assignment checks known source identity/style of selected witnesses, not a complete visual-identity classifier. Byte classes cannot split already encoded mixed-content streams.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('dpi',type=int);ap.add_argument('arm');ap.add_argument('pdf',type=Path);ap.add_argument('--report',type=Path);a=ap.parse_args();r=audit(a.dpi,a.arm,a.pdf,a.report);out=B/str(a.dpi)/a.arm/'audit.json';out.parent.mkdir(exist_ok=True,parents=True);out.write_text(json.dumps(r,indent=2));print(a.dpi,a.arm,{k:v for k,v in r.items() if k not in ['placements','assignments','gid_reuse','outline_reuse','resource_classes']})
