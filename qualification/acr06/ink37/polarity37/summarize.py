from pathlib import Path
import json,math,hashlib
root=Path('/data/coding/scanweave/qualification/acr06'); evidence=root/'ink37/polarity37'; local=root/'local/ink37/polarity37'
def lum(c):return sum(a*b for a,b in zip(c,(.2126,.7152,.0722)))
def q(a,k):
 a=sorted(a); p=(len(a)-1)*k; lo=math.floor(p); hi=math.ceil(p)
 return a[lo] if lo==hi else a[lo]*(hi-p)+a[hi]*(p-lo)
logs=[('corpus',name,local/f'{name}.log') for name in ('historical','financial','mixed','receipts','forms')]
for group in ('controls','controls-supplemental','positive-controls','table-candidates'):
 logs.extend((group,p.stem,p) for p in sorted((local/group).glob('*.log')))
logs.append(('table-context','receipt-context',local/'table-context.log'))
rows=[]
for group,name,path in logs:
 for line in path.open():
  if not line.startswith('POLARITY37_EVIDENCE '): continue
  record=json.loads(line.split(' ',1)[1]); boxes=record.pop('boxes'); values=[b['foreground']/b['pixels'] for b in boxes]
  file=f"boxes-{group}-{name}-{record['page_id']}.json"; (evidence/file).write_text(json.dumps(boxes,indent=2)+'\n')
  rows.append({'set':group,'document':name,**record,'paper_luminance':lum(record['paper']),'ink_luminance':lum(record['ink']),'box_count':len(values),'median':q(values,.5) if values else None,'p10':q(values,.1) if values else None,'p90':q(values,.9) if values else None,'majority_boxes':sum(v>.5 for v in values),'boxes_file':file,'decision':'not_applied','decision_reason':'no corpus-separating foreground-fraction threshold was found','zero_box_requested_route':('raster_baseline' if lum(record['ink']) > lum(record['paper']) else 'existing') if not values else None})
(evidence/'measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
