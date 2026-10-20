"""Strict page-content-only compression, independent of fonts/CMaps/images."""
import pikepdf,zlib,json
from pathlib import Path
B=Path(__file__).resolve().parent;rows=[]
for dpi in [300,600]:
 source=B.parent/'clearscan_background'/str(dpi)/'final.pdf'
 for content,objects in [(False,False),(True,False),(False,True),(True,True)]:
  q=pikepdf.open(source)
  if content:
   seen=set()
   for page in q.pages:
    streams=page.Contents if isinstance(page.Contents,pikepdf.Array) else [page.Contents]
    for s in streams:
     if s.objgen in seen:continue
     seen.add(s.objgen);s.write(zlib.compress(s.read_bytes(),6),filter=pikepdf.Name.FlateDecode)
  out=B/str(dpi)/f'content-{int(content)}-objects-{int(objects)}.pdf'
  q.save(out,compress_streams=False,object_stream_mode=pikepdf.ObjectStreamMode.generate if objects else pikepdf.ObjectStreamMode.disable,deterministic_id=True)
  counts={'content':0,'fonts':0,'unicode_cid':0,'images':0,'other_stream':0};seen=set()
  for page in q.pages:
   for s in page.Contents if isinstance(page.Contents,pikepdf.Array) else [page.Contents]:seen.add(s.objgen)
  # Reopen to measure actual encoded streams, not an in-memory pre-save model.
  p=pikepdf.open(out);content_ids=set();font_ids=set();map_ids=set()
  for page in p.pages:
   for s in page.Contents if isinstance(page.Contents,pikepdf.Array) else [page.Contents]:content_ids.add(s.objgen)
  for o in p.objects:
   if isinstance(o,pikepdf.Dictionary):
    for key in ['/FontFile','/FontFile2','/FontFile3']:
     if key in o:font_ids.add(o[key].objgen)
    for key in ['/ToUnicode','/CIDToGIDMap']:
     if key in o and isinstance(o[key],pikepdf.Stream):map_ids.add(o[key].objgen)
  for o in p.objects:
   if not isinstance(o,pikepdf.Stream):continue
   kind='content' if o.objgen in content_ids else 'fonts' if o.objgen in font_ids else 'unicode_cid' if o.objgen in map_ids else 'images' if o.get('/Subtype')==pikepdf.Name.Image else 'other_stream'
   counts[kind]+=len(o.read_raw_bytes())
  rows.append({'dpi':dpi,'content_compressed':content,'objects_compressed':objects,'pdf_bytes':out.stat().st_size,'streams':counts,'dicts_xref_and_overhead':out.stat().st_size-sum(counts.values())})
(B/'content-ablation.json').write_text(json.dumps(rows,indent=2));print(rows)
