#!/usr/bin/env python3
"""Render frozen patch-only page and record per-glyph boundary-to-paper tone."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41g';L=R/'local/hvc41g';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41G_HALO')!='1':sys.exit('halo switch required')
freeze=json.loads((E/'freeze.json').read_text());candidate=L/'historical-frozen.pdf';base=R/'local/ink33r/historical.pdf';assert sha(candidate.read_bytes())==freeze['pdf_sha256'] and (L/'qualification.started').read_text().splitlines()==[freeze['pdf_sha256'],freeze['representation_sha256']];ledger=R/'hvc41e/review-decisions.json';assert sha(ledger.read_bytes())=='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];h,w=2355,1738;ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;allowner=np.zeros((h,w),np.uint8)
for r in rows:
 a,b,c,d=r['reference_box'];allowner[b:d,a:c]|=(np.asarray(Image.open(r['masks']['owner']['path']).convert('L'))>0)
def render(path,engine,dpi,out):
 if engine=='pdfium':
  d=pdfium.PdfDocument(str(path));p=d[0];p.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(out);p.close();d.close()
 elif engine=='mupdf':
  code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[0].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(out),str(dpi)],check=True)
 else:
  exe='pdftocairo' if engine=='cairo' else 'pdftoppm';flags=['-aa','yes','-aaVector','yes'] if engine=='splash-aa' else [];subprocess.run([exe,'-f','1','-l','1','-r',str(dpi),'-png','-singlefile',*flags,str(path),str(out.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
with tempfile.TemporaryDirectory(prefix='hvc41g-halo-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 p=pikepdf.open(candidate);page=p.pages[0];page.Contents=pikepdf.Array([page.Contents[0],page.Contents[1]]);patchonly=L/'patch-only-diagnostic.pdf';p.save(patchonly);p.close();out=[];wt=np.array([.2126,.7152,.0722]);imagefile=L/'halo-scratch.png'
 for dpi in (96,300):
  for eng in ('splash-default','splash-aa','cairo','pdfium','mupdf'):
   render(base,eng,dpi,imagefile);baseline=np.asarray(Image.open(imagefile).convert('RGB'));render(patchonly,eng,dpi,imagefile);patch=np.asarray(Image.open(imagefile).convert('RGB'));H,W=baseline.shape[:2];allm=np.asarray(Image.fromarray(allowner).resize((W,H),Image.Resampling.NEAREST))>0;refm=np.asarray(Image.fromarray(ref).resize((W,H),Image.Resampling.NEAREST))>0
   for r in rows:
    a,b,c,d=r['reference_box'];owner=np.zeros((h,w),np.uint8);owner[b:d,a:c]=(np.asarray(Image.open(r['masks']['owner']['path']).convert('L'))>0);m=np.asarray(Image.fromarray(owner).resize((W,H),Image.Resampling.NEAREST))>0;inner=m&~nd.binary_erosion(m,structure=np.ones((3,3),bool));ring=nd.binary_dilation(m,iterations=4)&~nd.binary_dilation(m,iterations=1)&~allm&~refm;bl=baseline@wt;values=bl[ring];ring &= bl>=np.percentile(values,50) if values.size else ring;paper=float(np.median(bl[ring])) if ring.any() else None;pl=patch@wt;delta=pl[inner]-paper if paper is not None else np.array([]);out.append({'proposal':r['proposal'],'symbol':r['symbol_id'],'engine':eng,'dpi':dpi,'patch_boundary_pixels':int(inner.sum()),'paper_ring_pixels':int(ring.sum()),'paper_luma':paper,'boundary_to_ring_mean_abs_delta_luma':float(np.abs(delta).mean()) if delta.size else None,'boundary_to_ring_max_abs_delta_luma':float(np.abs(delta).max()) if delta.size else None,'boundary_to_ring_mean_signed_delta_luma':float(delta.mean()) if delta.size else None})
   print('halo',dpi,eng,flush=True)
 if marker.exists():sys.exit('OCR invoked')
 imagefile.unlink(missing_ok=True)
(E/'qualification-halo.json').write_text(json.dumps(out,indent=2)+'\n');print('halo rows',len(out),flush=True)
