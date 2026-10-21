import json,csv,hashlib,collections,subprocess
from pathlib import Path

PDF_GLOB = '*.pdf'

b=Path('qualification/real_convergence');p=Path('qualification/pdf_packaging')
m=json.loads((b/'measurements.json').read_text());old=json.loads((p/'group-measurements.json').read_text());inv=json.loads((b/'outline-inventory.json').read_text())
rows=[]
for r in old:rows.append({'document':r['group'],'arm':'previous_scanweave' if r['arm']=='scanweave' else r['arm'],**r['resources']})
for r in m:rows.append({'document':Path(r['pdf']).stem,'arm':'updated_scanweave',**r['resources']})
(b/'scorecard.json').write_text(json.dumps(rows,indent=2))
keys=sorted(set().union(*(r.keys() for r in rows)))
with (b/'scorecard.csv').open('w') as f:w=csv.DictWriter(f,keys,lineterminator="\n");w.writeheader();w.writerows(rows)
pages=[];classes=collections.Counter();counts=collections.Counter();bitonal=collections.Counter()
for r in m:
 name=Path(r['pdf']).stem;iv=next(x for x in inv if x['pdf'].endswith('/collections/'+name+'.pdf'))
 for i,a in enumerate(r['pages']):pages.append({'document':name,'document_pdf_bytes':r['resources']['pdf_bytes'],'page_index':i,**a,'actual_visible_glyph_draws':iv['pages'][i]['draws'],'unique_painted_gids':iv['pages'][i]['unique_gids']})
 for n in r['native']:
  if 'histogram' in n:n['strict_bitonal']={i for i,v in enumerate(n['histogram']) if v}=={0,255}
  classes[n['class']]+=n['bytes'];counts[n['class']]+=1
  if n.get('strict_bitonal'):bitonal[n['class']]+=1
(b/'measurements.json').write_text(json.dumps(m,indent=2));(b/'page-results.json').write_text(json.dumps(pages,indent=2))
flat=[{'document':r['document'],'page_index':r['page_index'],'id':r['id'],'document_pdf_bytes':r['document_pdf_bytes'],'actual_visible_glyph_draws':r['actual_visible_glyph_draws'],'unique_painted_gids':r['unique_painted_gids'],**{k:v for k,v in r['funnel'].items() if not isinstance(v,(dict,list))}} for r in pages]
keys=sorted(set().union(*(r.keys() for r in flat)))
with (b/'page-results.csv').open('w') as f:w=csv.DictWriter(f,keys,lineterminator="\n");w.writeheader();w.writerows(flat)
tot={k:sum(r['resources'][k] for r in m) for k in ['pdf_bytes','raster_bytes','font_bytes','content_bytes','overhead_bytes']};tot.update(raster_classes_bytes=dict(classes),raster_classes_objects=dict(counts),strict_bitonal_objects=dict(bitonal),actual_visible_draws=sum(r['actual_visible_glyph_draws'] for r in pages),unique_painted_gids_per_document_sum=sum(next(x for x in inv if x['pdf'].endswith('/collections/'+Path(r['pdf']).name))['unique_painted_gids'] for r in m))
(b/'totals.json').write_text(json.dumps(tot,indent=2))
manifest={'implementation_commits':['5998611','13288a8'],'starting_commit':(b/'starting-head.txt').read_text().strip(),'artifacts':[]}
paths=list((b/'outputs').glob(PDF_GLOB))+list((b/'collections').glob(PDF_GLOB))+list((b/'300').glob(PDF_GLOB))+list((b/'600').glob(PDF_GLOB))
paths+=list((p/'groups').glob(PDF_GLOB))
for x in paths:manifest['artifacts'].append({'path':str(x),'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'storage':'committed representative' if 'collections' not in str(x) and str(x).startswith(str(b)) else 'existing local artifact; reproduce with run.py'})
(b/'run-manifest.json').write_text(json.dumps(manifest,indent=2))
print(tot)
