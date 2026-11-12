"""Measure source-reference ghost and under-replacement for A0 and A3 vectors."""
import hashlib,json,os,pathlib,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from scipy import ndimage as nd
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda x:hashlib.sha256(x).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_GHOST')!='1':sys.exit('research switch required')
f=R/'hvc41e/review-decisions.json'
if sha(f.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef':sys.exit('ledger mismatch')
rows={r['proposal']:r for r in json.loads(f.read_text()) if r['decision']=='accept'};src=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;lum=src@np.array([.2126,.7152,.0722]);out=[]
with tempfile.TemporaryDirectory(prefix='hvc41f-ghost-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 for i in (243,38,18):
  r=rows[i];a,b,c,d=r['reference_box'];patch=np.asarray(Image.open(r['masks']['patch']['path']).convert('L'))>0;owner=np.asarray(Image.open(r['masks']['owner']['path']).convert('L'))>0
  for variant in ('A0','A3'):
   p=pikepdf.open(L/f'{variant}-{i:03}.pdf');p.pages[0].Contents=p.pages[0].Contents[-1];fpath=pathlib.Path(td)/'only.pdf';p.save(fpath);p.close();doc=pdfium.PdfDocument(str(fpath));page=doc[0];im=np.asarray(page.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB'));page.close();doc.close();l=im[b:d,a:c]@np.array([.2126,.7152,.0722]);v=l<(255+np.array(r['fill_rgb'])@np.array([.2126,.7152,.0722]))/2;local=ref[b:d,a:c];ghost=local&~v&~patch&nd.binary_dilation(v,structure=np.ones((3,3),bool));under=local&patch&~v;contrast=np.array(r['paper_fill_rgb'])@np.array([.2126,.7152,.0722])-lum[b:d,a:c];out.append({'proposal':i,'variant':variant,'vector_pixels':int(v.sum()),'ghost_ink_pixels':int(ghost.sum()),'ghost_max_luminance_contrast':float(contrast[ghost].max()) if ghost.any() else None,'under_replaced_ink_pixels':int(under.sum()),'patch_outside_owner':int((patch&~owner).sum()),'definition':'E frozen global reference proxy; neighbourhood ghost can include legitimate nearby marks'})
 if marker.exists():sys.exit('OCR invoked')
(E/'phase-b-ghost.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
