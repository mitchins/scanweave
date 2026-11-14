#!/usr/bin/env python3
"""Compare stock PDF-import tracks and the diagnostic build path."""
import hashlib,json,pathlib,re
import fitz,numpy as np,pikepdf,pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot'; ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def first_difference(a,b):
 with pikepdf.open(a) as x,pikepdf.open(b) as y:
  for i in range(max(len(x.objects),len(y.objects))):
   if i>=len(x.objects) or i>=len(y.objects):return {'index':i+1,'reason':'object count differs'}
   def fingerprint(o):
    try:z=o.read_raw_bytes() if isinstance(o,pikepdf.Stream) else o.unparse()
    except Exception:z=str(o).encode()
    return hashlib.sha256(z).hexdigest()
   u=fingerprint(x.objects[i]);v=fingerprint(y.objects[i])
   if u!=v:return {'index':i+1,'left_sha256':u,'right_sha256':v}
 return None
def resources(p):
 with pikepdf.open(p) as pdf:
  page=pdf.pages[0];r=page.obj.get('/Resources',{});fonts=r.get('/Font',{});xo=r.get('/XObject',{})
  return {'object_count':len(pdf.objects),'page_font_count':len(fonts),'page_xobject_count':len(xo),'page_font_subtypes':sorted(str(f.get('/Subtype','')) for f in fonts.values()),'page_xobject_subtypes':sorted(str(x.get('/Subtype','')) for x in xo.values())}
def render(p):
 with fitz.open(p) as f:
  x=f[0].get_pixmap(matrix=fitz.Matrix(150/72,150/72),colorspace=fitz.csRGB,alpha=False);return np.frombuffer(x.samples,dtype=np.uint8).reshape(x.height,x.width,3).copy()
def extract(p):
 d=pdfium.PdfDocument(str(p));return d[0].get_textpage().get_text_range()
out={}
for id in ids:
 d=B/'pilot/runs'/id.split('/')[-1]; e=d/'sw-E.pdf';m=d/'sw-M.pdf';build=d/'sw-build.pdf'
 if not all(p.exists() for p in [e,m,build]):out[id]={'error':'missing output'};continue
 er=json.loads((d/'sw-E.pdf.json').read_text())['pages'][0];mr=json.loads((d/'sw-M.pdf.json').read_text())['pages'][0];h1=er['hocr'];h2=mr['hocr'];normalize=lambda s:re.sub(r'image [^;]*;', 'image PATH;',s);equal=sha(e)==sha(m);a=render(m);b=render(build); diff=np.abs(a.astype(np.int16)-b.astype(np.int16)) if a.shape==b.shape else None
 out[id]={'sw_E_vs_sw_M':{'hocr_byte_equal':h1==h2,'hocr_equal_after_image_path_redaction':normalize(h1)==normalize(h2),'hocr_sha256_E':er['hocr_sha256'],'hocr_sha256_M':mr['hocr_sha256'],'pdf_byte_equal':equal,'first_differing_object':None if equal else first_difference(e,m),'selected_psm_E':er['selected_psm'],'selected_psm_M':mr['selected_psm'],'raster_import_E':er['raster_import'],'raster_import_M':mr['raster_import']},'sw_M_vs_build':{'pdf_bytes_M':m.stat().st_size,'pdf_bytes_build':build.stat().st_size,'pdf_byte_equal':sha(m)==sha(build),'first_differing_object':first_difference(m,build),'extracted_text_equal':extract(m)==extract(build),'resources_M':resources(m),'resources_build':resources(build),'pixel_test':'MuPDF 150 dpi RGB','dimensions_M':list(a.shape),'dimensions_build':list(b.shape),'changed_pixel_fraction':float((diff.max(axis=2)>0).mean()) if diff is not None else None,'mean_abs_channel_difference':float(diff.mean()) if diff is not None else None}}
 print(id,flush=True)
(Q/'results/path-equivalence.json').write_text(json.dumps(out,indent=2)+'\n')
