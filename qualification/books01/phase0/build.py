#!/usr/bin/env python3
"""Build dev sources and normalized GT. Never opens holdout images or XML."""
import collections, hashlib, json, pathlib, time, xml.etree.ElementTree as ET, zlib
import pikepdf
from PIL import Image,ImageDraw,features
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
corpus=json.loads((P/'corpus.proposed.json').read_text()); pages=[p for p in corpus['pages'] if p['split']=='dev']; reg=json.loads((B/'registration.json').read_text()); inv=json.loads((B/'inventory.unfrozen.json').read_text())['pages']; dpi_ev=json.loads((B/'dpi-evidence.json').read_text())
def sha(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def tag(e):return e.tag.rsplit('}',1)[-1]
def polygon(el):
 c=next((e for e in el if tag(e)=='Coords'),None)
 if c is None:return []
 if c.get('points'):return [[int(a) for a in pt.split(',')] for pt in c.get('points').split()]
 return [[int(pt.get('x')),int(pt.get('y'))] for pt in c if tag(pt)=='Point']
def txt(el):
 t=next((x for x in el if tag(x)=='TextEquiv'),None)
 if t is None:return None
 x=next((x for x in t if tag(x)=='Unicode'),None); return (x.text or '') if x is not None else None
def makepdf(path,im,dpi):
 raw=im.tobytes(); w,h=im.size; pdf=pikepdf.Pdf.new(); page=pdf.add_blank_page(page_size=(w*72/dpi,h*72/dpi)); name=pikepdf.Name
 stream=pdf.make_stream(zlib.compress(raw,9)); stream['/Type']=name('/XObject'); stream['/Subtype']=name('/Image'); stream['/Width']=w; stream['/Height']=h; stream['/ColorSpace']=name('/DeviceGray' if im.mode=='L' else '/DeviceRGB'); stream['/BitsPerComponent']=8; stream['/Filter']=name('/FlateDecode'); page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=stream)); page.Contents=pdf.make_stream(f'q {w*72/dpi:.8f} 0 0 {h*72/dpi:.8f} 0 0 cm /Im0 Do Q\n'.encode()); pdf.save(path,static_id=True,object_stream_mode=pikepdf.ObjectStreamMode.disable)
 with pikepdf.open(path) as q:
  decoded=q.pages[0].Resources.XObject['/Im0'].read_bytes(); assert decoded==raw
 return hashlib.sha256(raw).hexdigest()
start=time.monotonic(); locks={}; summaries={}; works=collections.defaultdict(list)
for p in pages:
 id=p['id']; parts=id.split('/'); work=p['work']; key='_'.join(parts); data=inv[id]['files'];
 if p['source']=='ocr-d-quiver':
  d=dpi_ev[id]; dpi=d['tiff_x_resolution']; assert dpi==d['tiff_y_resolution'] and d['tiff_resolution_unit']==2
  image=B/data[0]['path']; gt=B/data[1]['path']; evidence={'source':'TIFF XResolution/YResolution, inch unit','tag_values':[dpi,dpi,2],'implied_size_mm':d['implied_size_mm'],'mets_extents':d['mets_extents'],'plausibility':'dimensions consistent with cited format' if any(x in d['mets_extents'] for x in ['4','8','2°']) else 'no physical dimensions or format in METS; tag not independently verified','confidence':'moderate' if any(x in d['mets_extents'] for x in ['4','8','2°']) else 'low'}; language='deu_latf+lat' if 'fontmix' in p['repo'] else ('deu_latf' if 'frak' in p['repo'] else ('lat' if work.startswith('alberti') else 'deu'))
 else:
  image=B/data[0]['path']; gt=B/data[1]['path']; r=reg[id]; assert r['decision']=='webp'; dpi=p['ppi']; evidence={'source':'IA metadata ppi and scandata bookData/dpi; WebP dimensions equal cropBox pixel dimensions','confidence':'moderate','note':'access derivative, no physical resolution tag established'}; language=p['lang']
 with Image.open(image) as origin:
  mode='L' if origin.mode in ('1','L') else 'RGB'; im=origin.convert(mode); im.load()
 root=ET.parse(gt).getroot(); regions=[]; lines=[]; region_counts=collections.Counter(); reading=[]
 for e in root.iter():
  name=tag(e)
  if name.endswith('Region'):
   region_counts[name]+=1; regions.append({'id':e.get('id'),'kind':name,'type':e.get('type'),'polygon':polygon(e),'text':txt(e)})
   for line in e:
    if tag(line)=='TextLine': lines.append({'id':line.get('id'),'region_id':e.get('id'),'region_type':e.get('type'),'polygon':polygon(line),'text':txt(line)})
  if name in ('RegionRefIndexed','RegionRef','TextLineRefIndexed','TextLineRef'): reading.append({'type':name,'attributes':dict(e.attrib)})
 normalized={'id':id,'coordinate_frame':'source PDF image pixels; origin top-left','source_dimensions':list(im.size),'regions':regions,'lines':lines,'reading_order':reading,'reading_order_present':any(tag(e)=='ReadingOrder' for e in root.iter()),'limitation':None if lines else 'PAGE source has no TextLine elements; region text and polygons retained without fabricating lines'}
 text=[x['text'] for x in (lines if lines else regions) if x['text'] is not None]; chars=''.join(text); out=B/'gt'/work/(str(p['page'])+'.json'); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(normalized,ensure_ascii=False,indent=2)+'\n')
 summaries[id]={'normalised_gt_sha256':sha(out),'line_count':len(lines),'known_char_count':len(chars)-chars.count('\ufffd'),'unknown_char_count':chars.count('\ufffd'),'region_counts':dict(region_counts),'reading_order_present':normalized['reading_order_present'],'text_level':'line' if lines else 'region'}
 overlay=im.convert('RGB'); draw=ImageDraw.Draw(overlay); shapes=lines if lines else regions
 for item in shapes:
  coords=item['polygon'];
  if len(coords)>2:draw.line([tuple(x) for x in coords]+[tuple(coords[0])],fill=(255,0,0),width=3)
 qa=B/'qa/align'/work/(str(p['page'])+'.png'); qa.parent.mkdir(parents=True,exist_ok=True); overlay.save(qa)
 pdf=B/'sources/single'/work/(str(p['page'])+'.pdf'); pdf.parent.mkdir(parents=True,exist_ok=True); again=B/'tmp/rebuild.pdf'; decoded=makepdf(pdf,im,dpi); assert makepdf(again,im,dpi)==decoded and sha(pdf)==sha(again); works[work].append(pdf)
 locks[id]={'origin':data[0],'gt_origin':data[1],'origin_codec': 'TIFF uncompressed RGB8 (Compression tag 1)' if p['source']=='ocr-d-quiver' else 'WebP lossy','lossy_origin':p['source']!='ocr-d-quiver','processed_derivative':p['source']!='ocr-d-quiver','source_type':'processed-derivative' if p['source']!='ocr-d-quiver' else 'quiver-original-tiff','decoded_pixel_sha256':decoded,'canonical_pixels':mode+'8 row-major','dimensions':list(im.size),'resolved_dpi':dpi,'dpi_evidence':evidence,'registration':reg.get(id),'source_pdf_sha256':sha(pdf),'source_pdf_path':str(pdf.relative_to(B)),'generator':'pikepdf '+pikepdf.__version__,'language':language}
 print(id,im.size,dpi,flush=True)
for work,paths in works.items():
 dest=B/'sources/work'/(work+'.pdf'); dest.parent.mkdir(parents=True,exist_ok=True)
 def multi(out):
  q=pikepdf.Pdf.new()
  for path in paths:
   with pikepdf.open(path) as src:q.pages.extend(src.pages)
  q.save(out,static_id=True,object_stream_mode=pikepdf.ObjectStreamMode.disable)
 multi(dest); multi(B/'tmp/rebuild-work.pdf'); assert sha(dest)==sha(B/'tmp/rebuild-work.pdf')
(P/'sources.lock.json').write_text(json.dumps({'schema':'books01-sources/1','generator':{'pikepdf':pikepdf.__version__,'Pillow':Image.__version__,'openjpeg':features.version_codec('jpg_2000'),'zlib':zlib.ZLIB_VERSION},'pages':locks,'work_pdfs':{w:{'sha256':sha(B/'sources/work'/(w+'.pdf')),'page_count':len(paths)} for w,paths in works.items()}},indent=2,ensure_ascii=False)+'\n')
(P/'provenance/gt-summary.json').write_text(json.dumps({'schema':'books01-gt-summary/1','pages':summaries},indent=2,ensure_ascii=False)+'\n'); (B/'build-seconds.txt').write_text(str(time.monotonic()-start))
