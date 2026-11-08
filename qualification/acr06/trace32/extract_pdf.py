import fitz,json,sys,hashlib
from pathlib import Path
pdf=fitz.open(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
fonts={};pages=[]
for i,page in enumerate(pdf):
 content=[sha(pdf.xref_stream(x)) for x in page.get_contents()]
 images=[]
 for item in page.get_images(full=True):
  x=item[0]; images.append({'info':list(item[1:]),'raw':sha(pdf.xref_stream_raw(x)),'decoded':sha(pdf.xref_stream(x))})
 fids=[]
 for item in page.get_fonts(full=True):
  x=item[0]; name,ext,kind,data=pdf.extract_font(x); key=sha(data); fids.append(key)
  if key not in fonts:
   (out/(key+'.'+ext)).write_bytes(data)
   # Canonical object text with indirect object numbers normalized later if needed.
   fonts[key]={'file':key+'.'+ext,'type':kind,'base_name':name,'object':pdf.xref_object(x)}
 pages.append({'content':content,'images':images,'fonts':fids})
(out/'structure.json').write_text(json.dumps({'fonts':fonts,'pages':pages},indent=2))
