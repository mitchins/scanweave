from pathlib import Path
import json, math
root=Path('/data/coding/scanweave/qualification/acr06');local=root/'local/ink37';out=root/'ink37';results=[]
def lum(c):return sum(x*y for x,y in zip(c,(.2126,.7152,.0722)))
def quantile(a,q):
 a=sorted(a);i=(len(a)-1)*q;lo=math.floor(i);hi=math.ceil(i);return a[lo]*(hi-i)+a[hi]*(i-lo) if lo!=hi else a[lo]
logs=[]
for doc in ('historical','financial','mixed','receipts','forms'):logs.append(('corpus',doc,local/f'{doc}-main.log'))
for arm in ('measured','supplemental-measured','positive-measured','table-measured'):
 for path in sorted((local/f'control-{arm}').glob('*.log')):logs.append((arm,path.stem,path))
logs.append(('table-source','receipt-photo-p4',local/'glyph-measure-table-source.log'))
logs.append(('table-context','receipt-context',local/'glyph-measure-table-context.log'))
for arm,name,path in logs:
 if not path.exists():continue
 for line in path.read_text().splitlines():
  if not line.startswith('INK37_EVIDENCE '):continue
  x=json.loads(line[len('INK37_EVIDENCE '):]); units=x.pop('units'); ls=[lum(u['median']) for u in units if u['samples']]; g=x['glyph_ink']; s=x['seg_ink']; row={'set':arm,'document':name,**x,'seg_ink_luminance':lum(s),'glyph_ink_luminance':lum(g) if g else None,'delta_luminance':lum(s)-lum(g) if g else None,'units':len(units),'unit_luminance_p10':quantile(ls,.1) if ls else None,'unit_luminance_p90':quantile(ls,.9) if ls else None}
  row['spread']=row['unit_luminance_p90']-row['unit_luminance_p10'] if ls else None
  name2=f"glyph-units-{arm}-{name}-{x['page_id'].replace('/','_')}.json"; p=out/name2;p.write_text(json.dumps(units,indent=2)+'\n'); row['units_file']=name2
  results.append(row)
(out/'glyph-measurements.json').write_text(json.dumps(results,indent=2)+'\n')
