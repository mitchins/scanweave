#!/usr/bin/env python3
"""Score actual pre-containment unit masks against the independent source proxy.

These are mask upper bounds, not verified glyph geometry or correctness.
No visible-vector PDF is constructed by this script.
"""
import collections,json,pathlib,sys
import numpy as np
from PIL import Image
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41';O=R/'local/hvc41';weights=np.array([.2126,.7152,.0722],np.float32);out=[]
for doc in ('historical','receipts'):
 base=json.loads((R/'local/ink33r'/f'{doc}.pdf.json').read_text());can=json.loads((O/'trial2'/f'{doc}.pdf.json').read_text())
 for i,(src,report) in enumerate(zip(base['pages'],can['conversion']['page_reports']),1):
  dump=json.loads((O/'trial2'/doc/f'p{i:06}.json').read_text());a=np.asarray(Image.open(R/'local/ink33r/renders'/doc/f'{i:02d}-source.png').convert('RGB'));h,w=a.shape[:2];y=a.astype(np.float32)@weights;ref=np.zeros((h,w),bool);paper=np.zeros((h,w),bool)
  for line in chars_from_hocr(src['hocr']):
   for word in line['words']:
    for char in word['chars']:
     x0,y0,x1,y1=map(int,char['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
     if x1-x0<2 or y1-y0<2:continue
     q=y[y0:y1,x0:x1];bg=float(np.percentile(q,85));ink=q<bg-30;pap=q>bg-10
     if ink.sum()<3 or pap.sum()<3:continue
     ref[y0:y1,x0:x1]|=ink;paper[y0:y1,x0:x1]|=pap
  paper &= ~ref
  layers={k:np.zeros((h,w),bool) for k in ('owned','region_vector','proposed','contact_nontext','fidelity_rejected','unsupported','screened')};items=[];reasonunits=collections.Counter();reasonpixels=collections.Counter();selected=0
  for unit in dump['units']:
   bw,bh=unit['crop_w'],unit['crop_h'];x0=int(unit['bbox'][0]);y0=int(unit['bbox'][1]);inds=np.array(unit['mask_indices'],dtype=np.int64);xx=x0+inds%bw;yy=y0+inds//bw;valid=(xx>=0)&(xx<w)&(yy>=0)&(yy<h);xx=xx[valid];yy=yy[valid];layers['owned'][yy,xx]=True
   reg=unit['region'];kind=reg if isinstance(reg,str) else (reg or {}).get('Raster',{}).get('reason','unknown');reasonunits[kind]+=1;reasonpixels[kind]+=len(xx)
   if kind=='Vector':layers['region_vector'][yy,xx]=True
   if kind=='ContactNonText':layers['contact_nontext'][yy,xx]=True
   if kind=='FidelityBelowPolicy':layers['fidelity_rejected'][yy,xx]=True
   if kind=='UnsupportedContent':layers['unsupported'][yy,xx]=True
   if not unit['emitted_before_containment']:continue
   selected+=1;layers['proposed'][yy,xx]=True;inside=ref[yy,xx];nn=len(xx);hits=int(inside.sum());false_paper=int(paper[yy,xx].sum());median=float(np.median(y[yy[inside],xx[inside]])) if hits else None;fill=float(np.array(dump['ink'])@weights);delta=abs(fill-median) if median is not None else None;precision=hits/nn if nn else 0;accepted_proxy=precision>=.9 and delta is not None and delta<=25
   if accepted_proxy:layers['screened'][yy,xx]=True
   items.append({'symbol':unit['symbol'],'text_ocr_unverified':unit['text'],'bbox':unit['bbox'],'mask_pixels':nn,'reference_ink_overlap':hits,'reference_paper_overlap':false_paper,'reference_precision':precision,'reference_ink_luminance_median':median,'page_fill_luminance':fill,'fill_delta':delta,'passes_exploratory_screen':accepted_proxy,'verified_glyph':False})
  n=int(ref.sum());layerstats={k:{'all_mask_pixels':int(v.sum()),'reference_ink_pixels':int((v&ref).sum()),'reference_paper_pixels':int((v&paper).sum()),'reference_ink_fraction':float((v&ref).sum()/n) if n else None} for k,v in layers.items()};rec=report['reconstruction'];dec=collections.Counter(x.get('decision','unknown') for x in rec['occurrences']);row={'document':doc,'page':i,'reference_ink_pixels':n,'paper_rgb':dump['paper'],'ink_rgb':dump['ink'],'owned_units':len(dump['units']),'region_unit_counts':dict(reasonunits),'region_mask_pixels_sum_may_overlap':dict(reasonpixels),'donor_decisions':dict(dec),'prototype_count':len(rec['prototypes']),'canonical_geometry_count':len(rec['canonical_geometry']),'reported_trace_shapes':len(report['glyph_stats']),'reported_budget_pass_shapes':sum(x['budget_ok'] for x in report['glyph_stats']),'precontainment_fidelity':dump['precontainment_fidelity'],'precontainment_coverage':dump['precontainment_coverage'],'precontainment_occurrences':dump['precontainment_occurrences'],'unique_emitted_units':selected,'exploratory_screen_pass_count':sum(x['passes_exploratory_screen'] for x in items),'verified_safe_vector_coverage':None,'layers':layerstats,'reported_final_visible_vector_count':0 if report['selected'].startswith('raster_baseline') else report['polarity_visible_occurrences']}
  (E/f'proposed-{doc}-{i:02d}.json').write_text(json.dumps(items,indent=2)+'\n');out.append(row)
  Image.fromarray((ref*255).astype('uint8')).save(O/'masks'/f'corpus-{doc}-{i:02d}-reference-ink.png')
  Image.fromarray((layers['proposed']*255).astype('uint8')).save(O/'masks'/f'corpus-{doc}-{i:02d}-proposed.png')
  print(doc,i,'pre',row['precontainment_occurrences'],'proxy coverage',layerstats['proposed']['reference_ink_fraction'],'screen',row['exploratory_screen_pass_count'],flush=True)
(E/'trial-funnel.json').write_text(json.dumps(out,indent=2)+'\n')
