from pathlib import Path
import json,hashlib,pikepdf
B=Path(__file__).resolve().parent;R=B.parents[1];out=[]
for name in ['cord-00','cord-05','history-02','history-03']:
 inp=R/'qualification/pdf_packaging/real/input'/f'{name}.pdf';q=pikepdf.open(inp);pg=q.pages[0];rows=[]
 for obj in q.objects:
  if isinstance(obj,pikepdf.Stream) and obj.get('/Subtype')==pikepdf.Name.Image:
   im=pikepdf.PdfImage(obj).as_pil_image().convert('RGB');preview=im.copy();preview.thumbnail((1000,1200));preview.save(B/f'{name}-source-preview.png');rows.append({'width':int(obj.Width),'height':int(obj.Height),'colorspace':str(obj.ColorSpace),'filter':str(obj.get('/Filter')),'encoded_bytes':len(obj.read_raw_bytes()),'encoded_sha256':hashlib.sha256(obj.read_raw_bytes()).hexdigest(),'decoded_rgb_sha256':hashlib.sha256(im.tobytes()).hexdigest(),'effective_dpi':[int(obj.Width)*72/float(pg.MediaBox[2]),int(obj.Height)*72/float(pg.MediaBox[3])]})
 row={'id':name,'input_bytes':inp.stat().st_size,'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'media_box':[float(x) for x in pg.MediaBox],'images':rows}
 baseline=B/'baseline'/f'{name}.pdf'
 if baseline.exists():
  a=pikepdf.open(baseline);r=json.load(open(str(baseline)+'.json'));row.update(baseline_pdf_bytes=baseline.stat().st_size,native_import=r['pages'][0]['raster_import'],ocr_words=r['pages'][0]['ocr_words'],ocr_native_source=r['pages'][0]['native_source'],vector_occurrences=sum(o['owner'].startswith('visible') for o in r['conversion']['page_reports'][0]['occurrences']),baseline_images=[{'bytes':len(o.read_raw_bytes()),'filter':str(o.get('/Filter')),'width':int(o.Width),'height':int(o.Height),'colorspace':str(o.ColorSpace)} for o in a.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name.Image])
 out.append(row)
(B/'inventory.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
