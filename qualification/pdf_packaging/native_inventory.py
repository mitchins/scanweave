"""Encoded object inventory; grayscale histograms are actual decoded samples.
Atlas comparison is an evaluator-only storage diagnostic, not promoted encoding.
"""
import json,hashlib,zlib,collections
from pathlib import Path
import pikepdf,numpy as np
B=Path(__file__).resolve().parent;R=B.parents[1]
def inventory(path,report):
 p=pikepdf.open(path);seen=set();items=[];hist=np.zeros(256,dtype=np.int64);total=0;native=0;atlases=[]
 for pageindex,page in enumerate(p.pages):
  patches=report['page_reports'][pageindex]['patches'];gray=[]
  for index,patch in enumerate(patches):
   o=page.Resources.XObject.get('/Im'+str(index))
   if o is None:continue
   key=o.objgen
   if key in seen:continue
   seen.add(key);n=len(o.read_raw_bytes());total+=n
   background=bool(patch.get('compact_background'));whole_native=(not background and len(patches)==1);im=pikepdf.PdfImage(o).as_pil_image().convert('RGB');a=np.asarray(im);isgray=bool(np.all(a[:,:,0]==a[:,:,1]) and np.all(a[:,:,1]==a[:,:,2]));values=np.unique(a[:,:,0]) if isgray else None
   item={'object':list(key),'page':pageindex,'width':im.width,'height':im.height,'encoded_bytes':n,'compact_background':background,'native_whole_page':whole_native,'gray':isgray,'unique_values':len(values) if values is not None else None,'genuinely_bitonal':bool(isgray and set(values.tolist())=={0,255}),'two_level_gray':bool(isgray and len(values)==2),'gray_levels_if_at_most_two':values.tolist() if isgray and len(values)<=2 else None}
   if not background:
    native+=n
    if isgray:
     h=np.bincount(a[:,:,0].reshape(-1),minlength=256);hist+=h;gray.append((a[:,:,0],n));item.update(black=int(h[0]),white=int(h[255]),near_white=int(h[245:255].sum()),intermediate=int(h[1:245].sum()))
   items.append(item)
  if gray:
   # Simple shelf packing preserves all original samples; white padding explicit.
   width=max(x.shape[1] for x,_ in gray);height=sum(x.shape[0] for x,_ in gray)
   atlas=np.full((height,width),255,dtype=np.uint8);y=0
   for a,n in gray:atlas[y:y+a.shape[0],:a.shape[1]]=a;y+=a.shape[0]
   atlases.append({'page':pageindex,'native_gray_objects':len(gray),'separate_stream_bytes':sum(n for _,n in gray),'atlas_flate_bytes':len(zlib.compress(atlas.tobytes(),6)),'atlas_width':width,'atlas_height':height,'note':'encoded-stream diagnostic only; excludes clipping/content overhead and independent sampling equivalence'})
 return {'pdf':str(path.relative_to(R)),'pdf_bytes':path.stat().st_size,'raster_bytes':total,'native_resource_objects':sum(not i['compact_background'] for i in items),'native_resource_bytes':native,'native_whole_page_objects':sum(i['native_whole_page'] for i in items),'native_whole_page_bytes':sum(i['encoded_bytes'] for i in items if i['native_whole_page']),'native_exception_objects':sum(not i['compact_background'] and not i['native_whole_page'] for i in items),'native_exception_bytes':sum(i['encoded_bytes'] for i in items if not i['compact_background'] and not i['native_whole_page']),'native_gray_sample_histogram':hist.tolist(),'bitonal_native_objects':sum(i['genuinely_bitonal'] and not i['compact_background'] for i in items),'two_level_native_objects':sum(i['two_level_gray'] and not i['compact_background'] for i in items),'objects':items,'atlas_controls':atlases}
rows=[]
for dpi in [300,600]:
 p=B/str(dpi);rows.append(inventory(p/'final.pdf',json.loads((p/'report.json').read_text())))
for p in sorted((B/'real/scanweave').glob('*.pdf.json')):
 q=json.loads(p.read_text());rows.append(inventory(Path(str(p)[:-5]),q['conversion']))
(B/'native-inventory.json').write_text(json.dumps(rows,indent=2));print([(r['pdf'],r['native_exception_objects'],r['native_exception_bytes'],r['bitonal_native_objects']) for r in rows])
