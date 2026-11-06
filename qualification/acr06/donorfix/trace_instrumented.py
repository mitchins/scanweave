#!/usr/bin/env python3
"""Join temporary reconstruction instrumentation to PDFium tight emitted character bounds."""
import json, math, importlib.util
spec=importlib.util.spec_from_file_location("outline", "/data/coding/scanweave/qualification/acr06/donorfix/pdf_outline_bounds.py")
outline=importlib.util.module_from_spec(spec); spec.loader.exec_module(outline)
from pathlib import Path
import pypdfium2 as pdfium
root=Path('/data/coding/scanweave/qualification/acr06/local/donorfix')
targets={'single':(0,['w000053s0000','w000053s0001','w000102s0000','w000102s0001','w000130s0001','w000175s0001','w000180s0001']), 'financial':(8,['w000005s0011']), 'forms':(1,['w000471s0000','w000471s0001']), 'historical':(1,['w000070s0000','w000106s0006'])}
out=[]
for doc,(page,ids) in targets.items():
    log=root/f'{doc}-debug.log'; pdfpath=root/f'{doc}-instrumented.pdf'
    if not pdfpath.exists(): pdfpath=root/'baseline'/('single.pdf' if doc=='single' else f'{doc}-off.pdf')
    if not log.exists() or not pdfpath.exists(): continue
    rep=json.loads(Path(str(pdfpath)+'.json').read_text()); pr=rep['conversion']['page_reports'][page]; obs={o['symbol_id']:o for o in pr['reconstruction']['observations']}
    entries=[]
    for line in log.open():
        if line.startswith('DONOR_DEBUG '):
            item=json.loads(line[len('DONOR_DEBUG '):]);
            if item['id'] in ids and item['id'] in obs and item['ink']==obs[item['id']]['bbox_px']: entries.append(item)
    pdf=pdfium.PdfDocument(str(pdfpath)); pg=pdf[page]; tp=pg.get_textpage(); pw,ph=pg.get_size(); raster=rep['pages'][page]; sx=raster['raster_width']/pw; sy=raster['raster_height']/ph
    chars=[]
    for i in range(tp.count_chars()):
        try:
            c=tp.get_text_range(i,1); l,b,r,t=tp.get_charbox(i); box=[l*sx,(ph-t)*sy,r*sx,(ph-b)*sy]
            if r>l and t>b: chars.append((i,c,box))
        except Exception: pass
    outlines=outline.bounds(str(pdfpath),page,raster['raster_width'],raster['raster_height'])
    for e in entries:
        vals=[[] for _ in range(4)]; negatives=[0]*4
        for m in e['members']:
            o,b=m['ocr'],m['ink']; p=[b[0]-o[0],b[1]-o[1],o[2]-b[2],o[3]-b[3]]
            for j,v in enumerate(p):
                if math.isfinite(v) and v>=0: vals[j].append(v)
                else: negatives[j]+=1
        med=[sorted(v)[len(v)//2] if v else 0 for v in vals]
        box=e['replacement']; cx=(box[0]+box[2])/2; cy=(box[1]+box[3])/2
        matches=[(i,c,b) for i,c,b in chars if c==e['text'] and abs((b[0]+b[2])/2-cx)<max(20,box[2]-box[0]) and abs((b[1]+b[3])/2-cy)<max(20,box[3]-box[1])]
        matches.sort(key=lambda x: abs((x[2][0]+x[2][2])/2-cx)+abs((x[2][1]+x[2][3])/2-cy))
        near=sorted(outlines,key=lambda z:sum(abs(z['outline_bbox_px'][k]-box[k]) for k in range(4)))
        emitted=near[0] if near and sum(abs(near[0]['outline_bbox_px'][k]-box[k]) for k in range(4))<12 else None
        neighbors=[]
        for other in obs.values():
            b=other['bbox_px']; ix=max(0,min(box[2],b[2])-max(box[0],b[0])); iy=max(0,min(box[3],b[3])-max(box[1],b[1]));
            if other['symbol_id']!=e['id'] and ix*iy: neighbors.append({'id':other['symbol_id'],'text':other['text_hypothesis'],'ink_bbox':b,'bbox_intersection_area':ix*iy})
        occ=next((o for o in pr['reconstruction']['occurrences'] if o['symbol_id']==e['id']),{})
        donor_w=e['donor_ink'][2]-e['donor_ink'][0]; donor_h=e['donor_ink'][3]-e['donor_ink'][1]
        emitted_box=emitted['outline_bbox_px'] if emitted else None
        e.update(similarity=occ.get('similarity'),source_mask_iou=occ.get('source_mask_iou'),donor_size=[donor_w,donor_h],donor_aspect_ratio=donor_w/donor_h if donor_h else None,baseline_displacement_px=(emitted_box[3]-e['ink'][3] if emitted_box else None),height_displacement_px=((emitted_box[3]-emitted_box[1])-(e['ink'][3]-e['ink'][1]) if emitted_box else None),bbox_centroid_displacement_px=([(emitted_box[j]+emitted_box[j+2]-e['ink'][j]-e['ink'][j+2])/2 for j in (0,1)] if emitted_box else None),document=doc,page_index=page,median_pads=med,negative_pads_discarded=negatives,emitted_outline=emitted,pdfium_text_charbox_unreliable_for_multi_char_mappings=True,neighbour_bbox_intersections=neighbors)
        out.append(e)
Path('/data/coding/scanweave/qualification/acr06/donorfix/instrumented-traces.json').write_text(json.dumps(out,indent=2)+'\n')
print('traces',len(out),[(x['document'],x['id'],x['ocr'],x['ink'],x['median_pads'],x['replacement'],x['emitted_outline']['outline_bbox_px'] if x['emitted_outline'] else None) for x in out])
