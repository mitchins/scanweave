#!/usr/bin/env python3
"""Measure selected and finally retained donor masks at the proposed page placement."""
import json,math
from pathlib import Path
q=Path('/data/coding/scanweave/qualification/acr06'); traces=json.loads((q/'donorfix/instrumented-traces.json').read_text()); out=[]
def sample(mask,w,h,box,x,y):
 if not (box[0]<=x<box[2] and box[1]<=y<box[3]): return False
 i=int((x-box[0])*w/(box[2]-box[0]));j=int((y-box[1])*h/(box[3]-box[1]));return bool(mask[j*w+i])
for doc in ('single','financial','forms','historical'):
 log=q/f'local/donorfix/mask-debug/{doc}.log'
 if not log.exists():continue
 reports={}
 for line in log.open():
  if not line.startswith('DONOR_MASK_DEBUG '):continue
  try: m=json.loads(line[len('DONOR_MASK_DEBUG '):])
  except json.JSONDecodeError: continue
  t=next((t for t in traces if t['document']==doc and t['id']==m['id'] and t['ink']==m['bbox']),None)
  if not t:continue
  if t['page_index'] not in reports:
   f=q/'local/donorfix/baseline'/('single.pdf.json' if doc=='single' else doc+'-off.pdf.json');reports[t['page_index']]=json.loads(f.read_text())['conversion']['page_reports'][t['page_index']]['reconstruction']
  rec=reports[t['page_index']];o=next(o for o in rec['occurrences'] if o['symbol_id']==m['id']);g=next((g for g in rec['canonical_geometry'] if g['prototype_id']==o['prototype_id']),None)
  masks=[('selected',m['donor'],m['donor_width'],m['donor_height'],m['donor_mask'])]
  if g:masks.append(('retained',g['witness_symbol_id'],g['width'],g['height'],g['mask']))
  bbox=m['bbox'];p=m['replacement'];x0=math.floor(min(bbox[0],p[0]));x1=math.ceil(max(bbox[2],p[2]));y0=math.floor(min(bbox[1],p[1]));y1=math.ceil(max(bbox[3],p[3]));
  for kind,witness,dw,dh,dm in masks:
   source=[];donor=[];overlaps={n['id']:0 for n in m['neighbors']}
   for y in range(y0,y1):
    for x in range(x0,x1):
     xx=x+.5;yy=y+.5;a=sample(m['mask'],m['width'],m['height'],bbox,xx,yy);c=sample(dm,dw,dh,p,xx,yy)
     if a:source.append((xx,yy))
     if c:
      donor.append((xx,yy))
      for n in m['neighbors']:
       if sample(n['mask'],n['width'],n['height'],n['bbox'],xx,yy):overlaps[n['id']]+=1
   aa=set(source);cc=set(donor);inter=len(aa&cc);union=len(aa|cc)
   centroid=lambda a:[sum(v[j] for v in a)/len(a) for j in (0,1)] if a else None
   a,b=centroid(source),centroid(donor)
   out.append({'document':doc,'page_index':t['page_index'],'id':m['id'],'kind':kind,'witness':witness,'donor_size':[dw,dh],'source_pixels':len(source),'donor_pixels':len(donor),'intersection_pixels':inter,'union_pixels':union,'physical_mask_iou':inter/union if union else None,'source_ink_centroid':a,'placed_donor_centroid':b,'centroid_displacement':[b[j]-a[j] for j in (0,1)] if a and b else None,'separately_owned_neighbor_overlap_pixels':overlaps})
(q/'donorfix/physical-measures.json').write_text(json.dumps(out,indent=2)+'\n');print('measured',len(out))
