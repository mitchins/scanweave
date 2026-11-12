#!/usr/bin/env python3
"""Render isolated Phase A variants, quantify renderer differences, and make grids."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_RENDER_A')!='1':sys.exit('research switch required')
if sha((R/'hvc41e/review-decisions.json').read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha((R/'local/hvc41e/final/historical-composed.pdf').read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0':sys.exit('frozen hashes differ')
rows={x['proposal']:x for x in json.loads((R/'hvc41e/review-decisions.json').read_text()) if x['decision']=='accept'}; base=R/'local/ink33r/historical.pdf';runs=json.loads((E/'phase-a-variants.json').read_text());jobs=['splash-default','splash-aa','splash-noaa','cairo','pdfium','mupdf'];w,h=1738,2355
for i in [243,38,18]:
 p=pikepdf.open(L/f'A0-{i:03}.pdf');page=p.pages[0];page.Contents=pikepdf.Array([page.Contents[0],page.Contents[1]]);p.save(L/f'patch-only-{i:03}.pdf');p.close()
def render(path,engine,dpi,out):
 if engine=='pdfium':
  d=pdfium.PdfDocument(str(path));p=d[0];p.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(out);p.close();d.close()
 elif engine=='mupdf':
  code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[0].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(out),str(dpi)],check=True)
 else:
  exe='pdftocairo' if engine=='cairo' else 'pdftoppm'; flags=[] if engine in ('cairo','splash-default') else ['-aa','yes','-aaVector','yes'] if engine=='splash-aa' else ['-aa','no','-aaVector','no'];subprocess.run([exe,'-f','1','-l','1','-r',str(dpi),'-png','-singlefile',*flags,str(path),str(out.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
def crop_box(row,shape):
 a,b,c,d=row['reference_box'];H,W=shape[:2];return (max(0,int((a-8)*W/w)),max(0,int((b-8)*H/h)),min(W,int(np.ceil((c+8)*W/w))),min(H,int(np.ceil((d+8)*H/h))))
def crop(im,box):return im.crop(box)
def pdftext(path):
 d=pdfium.PdfDocument(str(path));v=[]
 for p in d:
  t=p.get_textpage();v.append(t.get_text_range());t.close();p.close()
 d.close();return v
def poptext(path):return subprocess.check_output(['pdftotext','-layout',str(path),'-'])
def searches(path):
 d=pdfium.PdfDocument(str(path));p=d[0];t=p.get_textpage();result={}
 for word in ['Bacharias','Boect!','Wud','Dat','fram','Ber)']:
  s=t.search(word);v=[]
  while True:
   hit=s.get_next()
   if hit is None:break
   v.append(list(hit))
  s.close();result[word]=v
 t.close();p.close();d.close();return result
with tempfile.TemporaryDirectory(prefix='hvc41f-render-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 if marker.exists():sys.exit('OCR marker exists')
 bt=pdftext(base);bp=poptext(base);bs=searches(base);sem=[]
 for run in runs:
  p=pathlib.Path(run['path']);sem.append({'proposal':run['proposal'],'variant':run['variant'],'pdfium_text_equal':pdftext(p)==bt,'poppler_text_equal':poptext(p)==bp,'pdfium_search_equal':searches(p)==bs})
 if not all(all(r[k] for k in ('pdfium_text_equal','poppler_text_equal','pdfium_search_equal')) for r in sem):sys.exit('semantics changed')
 (E/'phase-a-semantics.json').write_text(json.dumps(sem,indent=2)+'\n')
 for dpi in (96,300):
  for engine in jobs:
   file=L/'scratch.png';render(base,engine,dpi,file);baseim=Image.open(file).convert('RGB');W,H=baseim.size
   for i in [243,38,18]:
    box=crop_box(rows[i],np.asarray(baseim).shape);basecrop=np.asarray(crop(baseim,box));render(L/f'patch-only-{i:03}.pdf',engine,dpi,file);patchim=Image.open(file).convert('RGB');patchcrop=np.asarray(crop(patchim,box));
    a,b,c,d=rows[i]['reference_box']; owner=np.zeros((h,w),np.uint8);owner[b:d,a:c]=(np.asarray(Image.open(rows[i]['masks']['owner']['path']).convert('L'))>0);mapped=np.asarray(Image.fromarray(owner).resize((W,H),Image.Resampling.NEAREST))>0;own=np.asarray(Image.fromarray(mapped).crop(box));edge=ndi.binary_dilation(own,structure=np.ones((3,3),bool));
    for variant in ('A0','A1','A2'):
     render(L/f'{variant}-{i:03}.pdf',engine,dpi,file);im=Image.open(file).convert('RGB');cr=np.asarray(crop(im,box));dest=L/f'{variant}-{i:03}-{engine}-{dpi}.png';Image.fromarray(cr).save(dest)
     delta=np.max(np.abs(cr.astype(int)-patchcrop.astype(int)),axis=2);mask=delta>10;outside=(np.any(cr!=basecrop,axis=2))&~edge;yy,xx=np.nonzero(outside);lum=cr@np.array([.2126,.7152,.0722]);ink=np.mean(rows[i]['fill_rgb']);paper=np.mean(rows[i]['paper_fill_rgb']);intermediate=(lum>ink+(paper-ink)*.2)&(lum<ink+(paper-ink)*.8)&ndi.binary_dilation(mask,iterations=1)
     record={'proposal':i,'variant':variant,'engine':engine,'dpi':dpi,'crop_box_render_pixels':box,'intermediate_edge_pixels':int(intermediate.sum()),'vector_mask_pixels':int(mask.sum()),'centroid_xy':list(map(float,ndi.center_of_mass(mask)[::-1])) if mask.any() else None,'outside_owned_boundary_count':int(outside.sum()),'outside_coordinates_render_pixels':[[int(x+box[0]),int(y+box[1])] for y,x in zip(yy,xx)],'crop':str(dest),'crop_sha256':sha(dest.read_bytes())};(L/f'{variant}-{i:03}-{engine}-{dpi}.json').write_text(json.dumps(record));Image.fromarray(mask).save(L/f'{variant}-{i:03}-{engine}-{dpi}-mask.png')
    print(dpi,engine,i,flush=True)
 if marker.exists():sys.exit('OCR invoked')
file.unlink(missing_ok=True)
print('renderer crops completed; run phase_a_results.py for aligned metrics',flush=True)
