#!/usr/bin/env python3
"""Create exhaustive source/main/candidate word crops for changed occurrence decisions or placements."""
import json, math, importlib.util
spec=importlib.util.spec_from_file_location("outline", "/data/coding/scanweave/qualification/acr06/donorfix/pdf_outline_bounds.py")
outline=importlib.util.module_from_spec(spec); spec.loader.exec_module(outline)
from collections import defaultdict
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
root=Path('/data/coding/scanweave/qualification'); local=root/'acr06/local/donorfix'; output=local/'panels'; output.mkdir(parents=True,exist_ok=True)
def source(name):
    if name in ('financial','forms','historical','mixed','receipts'): return root/f'pdf_packaging/groups/{name}-input.pdf'
    if name=='single': return root/'pdf_packaging/real/input/scan-c03-29.pdf'
    if name=='fresh2': return local/'fresh2/source.pdf'
    if name.startswith('fresh2-'): return local/f"fresh2/page-{dict(zip(('200','300','600','fractional'),range(4)))[name[7:]]}.pdf"
    if name=='fresh': return local/'fresh/source.pdf'
    if name.startswith('fresh-'): return local/f"fresh/page-{dict(zip(('200','300','600','fractional'),range(4)))[name[6:]]}.pdf"
    if name.startswith('competitive'): return root/f'clearscan_competitive/{name[11:]}/source.pdf'
    if name.startswith('font01-'):
        _,split,i=name.split('-'); return root/f'font04/local/S1/font01/{split}-{i}.pdf'
    kind,i=name.split('-'); return root/f"font04/local/{dict(p2='P2',p2prime='P2prime',p2pp='P2pp')[kind]}/sheet-{i}.pdf"
def main_path(name):
    p=local/'main'/f'{name}.pdf'
    if p.exists(): return p
    return local/'baseline'/('single.pdf' if name=='single' else f'{name}-off.pdf')
rows=[]; grouped=defaultdict(list)
for cp in sorted((local/'candidate').glob('*.pdf')):
    name=cp.stem; mp=main_path(name)
    if not mp.exists(): continue
    a=json.loads(Path(str(mp)+'.json').read_text()); b=json.loads(Path(str(cp)+'.json').read_text())
    for page,(pa,pb) in enumerate(zip(a['conversion']['page_reports'],b['conversion']['page_reports'])):
        old={x['symbol_id']:x for x in pa['reconstruction']['occurrences']}; new={x['symbol_id']:x for x in pb['reconstruction']['occurrences']}; old_owner={x['symbol_id']:x['owner'] for x in pa['occurrences']}; new_owner={x['symbol_id']:x['owner'] for x in pb['occurrences']}; obs={x['symbol_id']:x for x in pa['reconstruction']['observations']}
        for sid in sorted(old.keys() & new.keys()):
            x,y=old[sid],new[sid]
            if (x['decision'],x.get('replacement_bbox_px'),x.get('prototype_id'),old_owner.get(sid))==(y['decision'],y.get('replacement_bbox_px'),y.get('prototype_id'),new_owner.get(sid)): continue
            if sid not in obs: continue
            prefix=sid.split('s')[0]; word=[v for k,v in obs.items() if k.startswith(prefix+'s')]; boxes=[v['bbox_px'] for v in word]
            for o in (x,y):
                if o.get('replacement_bbox_px'): boxes.append(o['replacement_bbox_px'])
            bb=[min(t[0] for t in boxes),min(t[1] for t in boxes),max(t[2] for t in boxes),max(t[3] for t in boxes)]
            row={'number':len(rows)+1,'document':name,'page_index':page,'symbol_id':sid,'text':x['text'],'word':''.join(z['text_hypothesis'] for z in sorted(word,key=lambda v:v['symbol_id'])),'old_decision':x['decision'],'new_decision':y['decision'],'old_owner':old_owner.get(sid),'new_owner':new_owner.get(sid),'observed_bbox':obs[sid]['bbox_px'],'old_bbox':x.get('replacement_bbox_px'),'new_bbox':y.get('replacement_bbox_px'),'old_expected_emission_box':(x.get('replacement_bbox_px') if x.get('repaired') or x.get('reused') else obs[sid]['bbox_px']) if str(old_owner.get(sid,'')).startswith('visible') else None,'new_expected_emission_box':(y.get('replacement_bbox_px') if y.get('repaired') or y.get('reused') else obs[sid]['bbox_px']) if str(new_owner.get(sid,'')).startswith('visible') else None,'old_similarity':x.get('similarity'),'new_similarity':y.get('similarity'),'old_source_mask_iou':x.get('source_mask_iou'),'new_source_mask_iou':y.get('source_mask_iou'),'crop_bbox':bb,'raster_width':a['pages'][page]['raster_width'],'raster_height':a['pages'][page]['raster_height']}
            rows.append(row);grouped[(name,page)].append(row)
for (name,pi),rs in grouped.items():
    docs=[pdfium.PdfDocument(str(p)) for p in (source(name),main_path(name),local/'candidate'/f'{name}.pdf')]; images=[]
    for doc in docs:
        pg=doc[pi]; images.append(pg.render(scale=150/72).to_pil().convert('RGB'))
    old_outlines=outline.bounds(str(main_path(name)),pi,rs[0]['raster_width'],rs[0]['raster_height'])
    new_outlines=outline.bounds(str(local/'candidate'/f'{name}.pdf'),pi,rs[0]['raster_width'],rs[0]['raster_height'])
    for row in rs:
        for label,items in [('old',old_outlines),('new',new_outlines)]:
            expected=row[label+'_expected_emission_box']
            if expected:
                choices=sorted(items,key=lambda z:sum(abs(z['outline_bbox_px'][k]-expected[k]) for k in range(4)))
                error=sum(abs(choices[0]['outline_bbox_px'][k]-expected[k]) for k in range(4)) if choices else float('inf')
                row[label+'_emitted_outline_bbox']=choices[0]['outline_bbox_px'] if error<=12 else None
                row[label+'_outline_match_error']=error if error<=12 else None
            else:
                row[label+'_emitted_outline_bbox']=None; row[label+'_outline_match_error']=None
        img=images[0]; sx=img.width/row['raster_width']; sy=img.height/row['raster_height']; bb=row['crop_bbox']; crop=(max(0,math.floor(bb[0]*sx)-8),max(0,math.floor(bb[1]*sy)-8),min(img.width,math.ceil(bb[2]*sx)+8),min(img.height,math.ceil(bb[3]*sy)+8)); row['_images']=[im.crop(crop) for im in images]
for offset in range(0,len(rows),12):
    chunk=rows[offset:offset+12]; width=max(sum(im.width*4+12 for im in r['_images']) for r in chunk); heights=[38+max(im.height*5+8 for im in r['_images']) for r in chunk]; sheet=Image.new('RGB',(width,sum(heights)),'white'); draw=ImageDraw.Draw(sheet); y=0
    for row,h in zip(chunk,heights):
        draw.text((4,y+3),f"{row['number']} {row['document']} p{row['page_index']} {row['symbol_id']} {row['word']} : {row['old_decision']} -> {row['new_decision']}   [source | main | candidate]",fill='black'); x=0
        for im in row['_images']:
            sheet.paste(im,(x,y+23)); sheet.paste(im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST),(x,y+27+im.height)); x+=im.width*4+12
        row['sheet']=f'sheet-{offset//12+1:04}.png'; row['sheet_y']=y; del row['_images']; y+=h
    sheet.save(output/f'sheet-{offset//12+1:04}.png',optimize=True)
(output/'index.json').write_text(json.dumps(rows,indent=2)+'\n'); print('changed rows',len(rows),'sheets',(len(rows)+11)//12)
