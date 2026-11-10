#!/usr/bin/env python3
"""Classify planner causes and score actual masks against the source proxy.
All pixel-proximity distances are Euclidean <= 4 pixels. Categories may overlap.
"""
import json,pathlib,collections,numpy as np
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); E=R/'hvc41/contact'; L=R/'local/hvc41';weights=np.array([.2126,.7152,.0722]);rows=[];proposals=[]
for mode in ('interior','corner'):
 for doc in (('historical','receipts') if mode=='interior' else ('historical','receipts','financial','mixed','forms')):
  path=L/'contact'/mode/doc
  reportpath=L/'contact'/mode/f'{doc}.pdf.json'
  if not path.exists() or not reportpath.exists(): continue
  report=json.loads(reportpath.read_text())['conversion']['page_reports']
  for dp in sorted(path.glob('p*.json')):
   page=int(dp.stem[1:]);d=json.loads(dp.read_text());rr=report[page-1];geom={x['symbol_id']:x for x in rr['reconstruction']['occurrences']};trace={x['symbol_id']:x for x in rr['glyph_stats']};refpath=L/'masks'/f'corpus-{doc}-{page:02d}-reference-ink.png'
   # The baseline estimator pipeline writes all real-page proxy masks.
   if not refpath.exists(): print('missing reference',refpath); continue
   ref=np.asarray(Image.open(refpath).convert('L'))>0;h,w=ref.shape;units=d['units']; byreg={r['id']:r for r in d['region_contacts']};pixels={k:np.zeros((h,w),bool) for k in ('bbox_only','pixel_contact','suspect','new_vector','proposed','new_proposed','screened')};counts=collections.Counter();regioncounts=collections.Counter();new_regions=set();class_for={}
   oldpath=L/'trial2'/doc/f'p{page:06}.json' if mode=='interior' else None
   old=json.loads(oldpath.read_text()) if oldpath and oldpath.exists() else None; oldby={u['symbol']:u for u in old['units']} if old else {}
   for rg in d['region_contacts']:
    co=rg['contact'];hits=co['bbox_contacts'];sus=bool(co['suspects']);pixel=any(a['pixel_contact'] for a in hits);bbox=bool(hits);disp=rg['disposition'];protected=isinstance(disp,dict) and disp.get('Raster',{}).get('reason')=='Protected'
    if protected: continue
    flags=[]
    if bbox and not pixel:flags.append('bbox_only')
    if pixel:flags.append('pixel_contact')
    if sus:flags.append('suspect')
    if bbox and not pixel and not sus and disp=='Vector':flags.append('new_vector');new_regions.add(rg['id'])
    for key in flags:regioncounts[key]+=1
    for ui in rg['units']:class_for[ui]=flags
   srcpath=R/'local/ink33r/renders'/doc/f'{page:02d}-source.png';rgb=np.asarray(Image.open(srcpath).convert('RGB'));lum=rgb.astype(np.float32)@weights;fill=float(np.array(d['ink'])@weights)
   for ui,u in enumerate(units):
    flags=class_for.get(ui,[]);bw=u['crop_w'];ii=np.asarray(u['mask_indices'],dtype=np.int64);xx=int(u['bbox'][0])+ii%bw;yy=int(u['bbox'][1])+ii//bw;ok=(xx>=0)&(yy>=0)&(xx<w)&(yy<h);xx=xx[ok];yy=yy[ok]
    for flag in flags: counts[flag]+=1;pixels[flag][yy,xx]=True
    if u['emitted_before_containment']:
     counts['proposed']+=1;pixels['proposed'][yy,xx]=True
     if 'new_vector' in flags:
      counts['new_proposed']+=1;pixels['new_proposed'][yy,xx]=True
      n=len(xx);hit=ref[yy,xx];nh=int(hit.sum());prec=nh/n if n else 0;med=float(np.median(lum[yy[hit],xx[hit]])) if nh else None;delta=abs(fill-med) if med is not None else None
      g=geom.get(u['symbol'],{}); t=trace.get(u['symbol'],{}); giou=g.get('source_mask_iou'); tiou=g.get('prototype_trace_iou'); geometry_pass=giou is not None and giou>=.98 and (tiou is None or tiou>=.98); proposals.append({'mode':mode,'document':doc,'page':page,'symbol':u['symbol'],'ocr_label_unverified':u['text'],'bbox':u['bbox'],'mask_pixels':n,'reference_ink_pixels':nh,'reference_precision':prec,'fill_luminance_delta':delta,'source_mask_iou':giou,'prototype_trace_iou':tiou,'trace_budget_ok':t.get('budget_ok'),'donor_decision':g.get('decision'),'passes_exploratory_geometry_screen':geometry_pass,'passes_exploratory_screen':prec>=.9 and delta is not None and delta<=25 and geometry_pass,'verified_glyph':False})
      if prec>=.9 and delta is not None and delta<=25 and geometry_pass: counts['screened']+=1; pixels['screened'][yy,xx]=True
   stats={k:{'units':counts[k],'regions':regioncounts[k],'reference_ink_pixels_unioned':int((v&ref).sum()),'reference_ink_fraction':float((v&ref).sum()/ref.sum()) if ref.sum() else None} for k,v in pixels.items()}
   # New proposal counts describe units in newly vector-planned regions; geometry
   # and appearance still require rendered glyph verification.
   for art in d['largest_artwork']:
    x0,y0,x1,y1=art['bbox']; art['bbox_fill_ratio']=art['pixels']/max(1,(x1-x0)*(y1-y0))
   region_details=list(d['region_contacts'])
   for region in region_details:
    c=region['contact']; b=bool(c['bbox_contacts']); s0=bool(c['suspects']); pixel=any(x['pixel_contact'] for x in c['bbox_contacts']); region['bbox_rule_reason']='both' if b and s0 else 'artwork_contact' if b else 'suspect' if s0 else 'neither'; region['pixel_rule_reason']='both' if pixel and s0 else 'artwork_contact' if pixel else 'suspect' if s0 else 'neither'
   region_details.extend({'id':x['id'],'units':[],'disposition':x['disposition'],'kind':x['kind'],'bbox_px':x['bbox_px'],'contact':{'bbox_contacts':[],'suspects':[]},'reason':'standalone artwork; no text units'} for x in rr['regions'] if x['units']==0)
   top=d['largest_artwork'][0]['artwork_index'] if d['largest_artwork'] else None
   top_bbox=sum(len(r['units']) for r in d['region_contacts'] if any(x['artwork_index']==top for x in r['contact']['bbox_contacts'])) if top is not None else 0
   top_pixel=sum(len(r['units']) for r in d['region_contacts'] if any(x['artwork_index']==top and x['pixel_contact'] for x in r['contact']['bbox_contacts'])) if top is not None else 0
   rows.append({'mode':mode,'document':doc,'page':page,'reference_ink_pixels':int(ref.sum()),'owned_units':len(units),'new_vector_regions':len(new_regions),'precontainment_occurrences':d['precontainment_occurrences'],'top_art_bbox_units':top_bbox,'top_art_pixel_contact_units':top_pixel,'categories':stats,'regions':region_details,'largest_artwork':d['largest_artwork']})
   print(mode,doc,page,'new regions',len(new_regions),'new units',counts['new_vector'],'proposed',counts['proposed'],flush=True)
# Keep page JSON bounded; full per-region records are separate.
for row in rows:
 (E/f"regions-{row['mode']}-{row['document']}-{row['page']:02}.json").write_text(json.dumps(row.pop('regions'),indent=2)+'\n')
(E/'decomposition.json').write_text(json.dumps(rows,indent=2)+'\n');(E/'new-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
