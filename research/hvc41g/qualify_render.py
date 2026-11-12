#!/usr/bin/env python3
"""Render final, baseline and E and enumerate outside-band differences."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
import numpy as np,pypdfium2 as pdfium,pikepdf
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41g';L=R/'local/hvc41g';O=L/'renders';O.mkdir(exist_ok=True);sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41G_QUALIFY')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';prior=R/'local/hvc41e/final/historical-composed.pdf';cand=L/'historical-frozen.pdf';freeze=json.loads((E/'freeze.json').read_text());failed=R/'local/hvc41f/final/historical-final.pdf'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(prior.read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(cand.read_bytes())!=freeze['pdf_sha256'] or sha(failed.read_bytes())!='a327845e4665935df26f9eb8b63b7000ab069235d9fd1db9bd2abbfb600525cc':sys.exit('frozen input mismatch')
rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];owner=np.zeros((2355,1738),bool)
for r in rows:
 a,b,c,d=r['reference_box'];spec=r['masks']['owner'];data=pathlib.Path(spec['path']).read_bytes();assert sha(data)==spec['sha256'];owner[b:d,a:c]|=np.asarray(Image.open(spec['path']).convert('L'))>0
def render(path,engine,dpi,page,out):
 if engine=='pdfium':
  d=pdfium.PdfDocument(str(path));p=d[page-1];p.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(out);p.close();d.close()
 elif engine=='mupdf':
  code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[int(sys.argv[4])-1].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(out),str(dpi),str(page)],check=True)
 else:
  exe='pdftocairo' if engine=='cairo' else 'pdftoppm';flags=['-aa','yes','-aaVector','yes'] if engine=='splash-aa' else [];subprocess.run([exe,'-f',str(page),'-l',str(page),'-r',str(dpi),'-png','-singlefile',*flags,str(path),str(out.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
with pikepdf.open(cand) as frozen:
 streams=[frozen.pages[0].Contents[1],frozen.pages[0].Contents[2],frozen.pages[0].Resources.XObject['/ResearchPaths']]
 if sha(b'\0'.join(z.read_bytes() for z in streams))!=freeze['representation_sha256']:sys.exit('frozen representation mismatch')
try:
 with (L/'qualification.started').open('x') as marker:marker.write(freeze['pdf_sha256']+'\n'+freeze['representation_sha256']+'\n')
except FileExistsError:sys.exit('qualification already started')
results=[];wt=np.array([.2126,.7152,.0722])
with tempfile.TemporaryDirectory(prefix='hvc41f-final-render-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 if marker.exists():sys.exit('OCR marker exists')
 for dpi in (96,300):
  for engine in ('splash-default','splash-aa','cairo','pdfium','mupdf'):
   for page in range(1,6):
    arrays={}
    for label,path in [('baseline',base),('candidate',cand)]+([('hvc41e',prior),('hvc41f',failed)] if page==1 else []):
     out=O/f'{engine}-{dpi}-{page:02}-{label}.png';render(path,engine,dpi,page,out);arrays[label]=np.asarray(Image.open(out).convert('RGB'))
    b=arrays['baseline'];H,W=b.shape[:2];mapped=np.asarray(Image.fromarray(owner).resize((W,H),Image.Resampling.NEAREST))>0;band=nd.binary_dilation(mapped,structure=np.ones((3,3),bool))&~mapped
    for label in ('candidate','hvc41e','hvc41f') if page==1 else ('candidate',):
     c=arrays[label];assert c.shape==b.shape;change=np.any(c!=b,axis=2);r={'engine':engine,'dpi':dpi,'page':page,'comparison':label,'changed':int(change.sum()),'render':str(O/f'{engine}-{dpi}-{page:02}-{label}.png'),'sha256':sha((O/f'{engine}-{dpi}-{page:02}-{label}.png').read_bytes())}
     if page==1:
      inside=change&mapped;boundary=change&band;other=change&~mapped&~band;delta=(c.astype(float)-b.astype(float))@wt;yy,xx=np.nonzero(other);owner_index=np.zeros(owner.shape,np.uint8)
      for ix,gr in enumerate(rows,1):
       ga,gb,gc,gd=gr['reference_box'];owner_index[gb:gd,ga:gc][np.asarray(Image.open(gr['masks']['owner']['path']).convert('L'))>0]=ix
      ids=np.asarray(Image.fromarray(owner_index).resize((W,H),Image.Resampling.NEAREST));_,near=nd.distance_transform_edt(~mapped,return_indices=True);nearest=ids[near[0],near[1]]
      r.update(inside_owned=int(inside.sum()),boundary=int(boundary.sum()),beyond=int(other.sum()),boundary_luma_min=float(delta[boundary].min()) if boundary.any() else None,boundary_luma_max=float(delta[boundary].max()) if boundary.any() else None,beyond_xy_delta_luma=[{'x':int(x),'y':int(y),'delta_luma':round(float(delta[y,x]),4),'nearest_glyph':rows[int(nearest[y,x])-1]['proposal'] if nearest[y,x] else None,'likely_cause':'renderer edge sampling near owned glyph; exact cause unproven'} for y,x in zip(yy,xx)]);mask=np.zeros_like(c);mask[boundary]=[255,200,0];mask[other]=[255,0,0];Image.fromarray(mask).save(O/f'{engine}-{dpi}-01-{label}-boundary.png')
     results.append(r)
    print(dpi,engine,page,'changed',results[-1]['changed'],flush=True)
 if marker.exists():sys.exit('OCR invoked')
(E/'qualification-render.json').write_text(json.dumps(results,indent=2)+'\n');print('final render complete',len(results),flush=True)
