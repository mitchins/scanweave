#!/usr/bin/env python3
"""Check changed PDFs, embedded fonts, and pixels outside changed glyph neighborhoods."""
import collections, hashlib, json, math, os, subprocess, tempfile
from pathlib import Path
import numpy as np, pikepdf, pypdfium2 as pdfium
from PIL import Image
root=Path('/data/coding/scanweave/qualification'); local=root/'acr06/local/donorfix'; rows=json.loads((local/'panels/index.json').read_text()); grouped=collections.defaultdict(list)
for row in rows: grouped[(row['document'],row['page_index'])].append(row)
qpdf='/tmp/scanweave-qpdf-deb/root/usr/bin/qpdf'; ots='/tmp/scanweave-donorfix-ots/build/ots-sanitize'; env=dict(os.environ,LD_LIBRARY_PATH='/tmp/scanweave-qpdf-deb/root/usr/lib/x86_64-linux-gnu'); cache={}; results={}
def main_path(name):
 p=local/'main'/f'{name}.pdf'
 return p if p.exists() else local/'baseline'/('single.pdf' if name=='single' else f'{name}-off.pdf')
def poppler(path,page):
 with tempfile.TemporaryDirectory(dir='/tmp') as td:
  prefix=Path(td)/'page'; cmd=['pdftoppm','-f',str(page+1),'-l',str(page+1),'-singlefile','-r','150','-png',str(path),str(prefix)]; p=subprocess.run(cmd,capture_output=True,text=True)
  if p.returncode: raise RuntimeError(p.stderr)
  return np.array(Image.open(str(prefix)+'.png').convert('RGB'))
def pdfium_render(path,page):
 doc=pdfium.PdfDocument(str(path)); return np.array(doc[page].render(scale=150/72).to_pil().convert('RGB'))
for name in sorted({x[0] for x in grouped}):
 cp=local/'candidate'/f'{name}.pdf'; mp=main_path(name); q=subprocess.run([qpdf,'--check',str(cp)],env=env,capture_output=True,text=True); result={'qpdf_exit':q.returncode,'qpdf_output':q.stdout+q.stderr,'fonts':[], 'pages':[]}
 with pikepdf.open(cp) as pdf:
  for pi,page in enumerate(pdf.pages):
   resources=page.get('/Resources',{}); fonts=resources.get('/Font',{})
   for _,font in fonts.items():
    try:
     face=font.DescendantFonts[0] if '/DescendantFonts' in font else font; desc=face.FontDescriptor
     stream=next((desc[k] for k in ('/FontFile','/FontFile2','/FontFile3') if k in desc),None)
     if stream is None: continue
     raw=stream.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
     if digest not in cache:
      with tempfile.TemporaryDirectory(dir='/tmp') as td:
       ip=Path(td)/'input.font'; op=Path(td)/'output.font'; ip.write_bytes(raw); p=subprocess.run([ots,str(ip),str(op)],capture_output=True,text=True)
       cache[digest]={'sha256':digest,'exit':p.returncode,'output':p.stdout+p.stderr}
     result['fonts'].append({'page_index':pi,**cache[digest]})
    except (AttributeError,KeyError,ValueError,pikepdf.PdfError) as e: result['fonts'].append({'page_index':pi,'error':str(e)})
 for _,pi in sorted(k for k in grouped if k[0]==name):
  rs=grouped[(name,pi)]; entry={'page_index':pi,'renderers':{}}
  for renderer,fn in [('pdfium',pdfium_render),('poppler',poppler)]:
   a=fn(mp,pi); b=fn(cp,pi)
   if a.shape!=b.shape: entry['renderers'][renderer]={'shape_mismatch':[list(a.shape),list(b.shape)]}; continue
   h,w=a.shape[:2]; sx=w/rs[0]['raster_width']; sy=h/rs[0]['raster_height']; allowed=np.zeros((h,w),dtype=bool); wide=np.zeros((h,w),dtype=bool)
   for row in rs:
    for box in (row['observed_bbox'],row['old_bbox'],row['new_bbox']):
     if box:
      x0=max(0,math.floor((box[0]-4)*sx)); x1=min(w,math.ceil((box[2]+4)*sx)); y0=max(0,math.floor((box[1]-4)*sy)); y1=min(h,math.ceil((box[3]+4)*sy)); allowed[y0:y1,x0:x1]=True
      x0=max(0,math.floor(box[0]*sx)-16); x1=min(w,math.ceil(box[2]*sx)+16); y0=max(0,math.floor(box[1]*sy)-16); y1=min(h,math.ceil(box[3]*sy)+16); wide[y0:y1,x0:x1]=True
   delta=np.max(np.abs(a.astype('int16')-b.astype('int16')),axis=2); diff=delta>0; outside=diff & ~allowed; far=diff & ~wide
   entry['renderers'][renderer]={'different_pixels':int(diff.sum()),'outside_neighborhood_pixels':int(outside.sum()),'neighborhood_padding_source_px':4,'outside_16_render_px':int(far.sum()),'outside_16_render_px_delta_gt_2':int(((delta>2)&~wide).sum()),'outside_16_render_px_delta_gt_8':int(((delta>8)&~wide).sum()),'shape':list(a.shape)}
  result['pages'].append(entry)
 results[name]=result
 (root/'acr06/donorfix/functional.json').write_text(json.dumps(results,indent=2)+'\n'); print(name,'qpdf',q.returncode,'fonts',len(result['fonts']),'pages',len(result['pages']),flush=True)
