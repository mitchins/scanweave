from pathlib import Path
import json,hashlib,numpy as np,pypdfium2 as p
base=Path('/data/coding/scanweave/qualification/acr06/local/ink37');out=base/'gate37';rows=[]
items=[]
for group in ('controls','controls-supplemental','positive-controls','table-candidates'):
 for src in sorted((base/group).glob('*.pdf')):items.append((group,src,out/group/src.name))
items.extend([('table-context',base/'table-context-control.pdf',out/'table-context.pdf'),('new-border',out/'black-border-new.pdf',out/'black-border-candidate.pdf')])
for group,src,dst in items:
 if not dst.exists():continue
 report=json.loads(Path(str(dst)+'.json').read_text()); docs=[p.PdfDocument(src),p.PdfDocument(dst)]
 for i,(x,y) in enumerate(zip(*docs)):
  result=report['conversion']['page_reports'][i]; gate=result['polarity_raster_baseline'];row={'group':group,'input':src.name,'page':i+1,'paper_luminance':result['polarity_paper_luminance'],'ink_luminance':result['polarity_ink_luminance'],'gate':gate}
  if gate:
   images=[np.asarray(z.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB')) for z in (x,y)]
   if images[0].shape==images[1].shape:row['source_render_changed_pixels']=int(np.any(images[0]!=images[1],axis=2).sum())
   else:row['source_render_changed_pixels']=None;row['shapes']=[im.shape for im in images]
  rows.append(row);x.close();y.close()
 for d in docs:d.close()
 print(group,src.name,flush=True)
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/gate-controls.json').write_text(json.dumps(rows,indent=2)+'\n')
