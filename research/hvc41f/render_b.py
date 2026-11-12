#!/usr/bin/env python3
"""Render B0/B1/B2; enumerate every outside-boundary exception."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_RENDER_B')!='1':sys.exit('research switch required')
if sha((R/'hvc41e/review-decisions.json').read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha((R/'local/hvc41e/final/historical-composed.pdf').read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0' or sha((R/'local/ink33r/historical.pdf').read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b':sys.exit('frozen hash mismatch')
rows={r['proposal']:r for r in json.loads((R/'hvc41e/review-decisions.json').read_text()) if r['decision']=='accept'};base=R/'local/ink33r/historical.pdf';w,h=1738,2355
for i in (243,38,18):
 shutil.copyfile(L/f'A0-{i:03}.pdf',L/f'B0-{i:03}.pdf')
 for v in ('B0','B1','B2'):
  p=pikepdf.open(L/f'{v}-{i:03}.pdf');page=p.pages[0];page.Contents=pikepdf.Array([page.Contents[0],page.Contents[1]]);p.save(L/f'{v}-patch-only-{i:03}.pdf');p.close()
def render(path,engine,dpi,out):
 if engine=='pdfium':
  d=pdfium.PdfDocument(str(path));p=d[0];p.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(out);p.close();d.close()
 elif engine=='mupdf':
  code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[0].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(out),str(dpi)],check=True)
 else:
  exe='pdftocairo' if engine=='cairo' else 'pdftoppm';flags=[] if engine=='cairo' else ['-aa','yes','-aaVector','yes'];subprocess.run([exe,'-f','1','-l','1','-r',str(dpi),'-png','-singlefile',*flags,str(path),str(out.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
def text(path):
 d=pdfium.PdfDocument(str(path));v=[]
 for p in d:
  t=p.get_textpage();v.append(t.get_text_range());t.close();p.close()
 d.close();return v
def search(path):
 d=pdfium.PdfDocument(str(path));p=d[0];t=p.get_textpage();v={}
 for q in ['Bacharias','Boect!','Wud','Dat','fram','Ber)']:
  s=t.search(q);hits=[]
  while (z:=s.get_next()) is not None:hits.append(list(z))
  s.close();v[q]=hits
 t.close();p.close();d.close();return v
with tempfile.TemporaryDirectory(prefix='hvc41f-b-render-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 bt=text(base); bp=subprocess.check_output(['pdftotext','-layout',str(base),'-']);bs=search(base);sem=[]
 for i in (243,38,18):
  for v in ('B0','B1','B2'):
   p=L/f'{v}-{i:03}.pdf';sem.append({'proposal':i,'variant':v,'pdfium_text_equal':text(p)==bt,'poppler_text_equal':subprocess.check_output(['pdftotext','-layout',str(p),'-'])==bp,'pdfium_search_equal':search(p)==bs})
 if not all(x['pdfium_text_equal'] and x['poppler_text_equal'] and x['pdfium_search_equal'] for x in sem):sys.exit('semantic mismatch')
 (E/'phase-b-semantics.json').write_text(json.dumps(sem,indent=2)+'\n');records=[];wt=np.array([.2126,.7152,.0722]);tmp=L/'scratch-b.png'
 for dpi in (96,300):
  for engine in ('splash-aa','cairo','pdfium','mupdf'):
   render(base,engine,dpi,tmp);baseline=np.asarray(Image.open(tmp).convert('RGB'));H,W=baseline.shape[:2]
   for i in (243,38,18):
    r=rows[i];a,b,c,d=r['reference_box'];source=np.zeros((h,w),np.uint8);source[b:d,a:c]=(np.asarray(Image.open(r['masks']['owner']['path']).convert('L'))>0);owned=np.asarray(Image.fromarray(source).resize((W,H),Image.Resampling.NEAREST))>0;boundary=nd.binary_dilation(owned,structure=np.ones((3,3),bool));ring=nd.binary_dilation(owned,iterations=4)&~boundary;bl=baseline@wt;sample=bl[ring];ring &= bl>=np.percentile(sample,50) if sample.size else ring;paper=float(np.median(bl[ring])) if ring.any() else None
    box=(max(0,int((a-8)*W/w)),max(0,int((b-8)*H/h)),min(W,int(np.ceil((c+8)*W/w))),min(H,int(np.ceil((d+8)*H/h))))
    for v in ('B0','B1','B2'):
     render(L/f'{v}-{i:03}.pdf',engine,dpi,tmp);candidate=np.asarray(Image.open(tmp).convert('RGB'));diff=np.any(candidate!=baseline,axis=2);other=diff&~boundary;yy,xx=np.nonzero(other);delta=(candidate.astype(float)-baseline.astype(float))@wt;points=[[int(x),int(y),round(float(delta[y,x]),4)] for y,x in zip(yy,xx)]
     out=L/f'{v}-{i:03}-{engine}-{dpi}.png';Image.fromarray(candidate).crop(box).save(out); overlay=Image.fromarray(candidate).crop(box).convert('RGB');mark=np.zeros_like(candidate);mark[diff&~owned&boundary]=[255,200,0];mark[other]=[255,0,0];Image.fromarray(mark).crop(box).save(L/f'{v}-{i:03}-{engine}-{dpi}-outside.png')
     render(L/f'{v}-patch-only-{i:03}.pdf',engine,dpi,tmp);patch=np.asarray(Image.open(tmp).convert('RGB'));inner=owned&~nd.binary_erosion(owned,structure=np.ones((3,3),bool));pl=patch@wt;res=abs(pl[inner]-paper) if paper is not None else np.array([])
     records.append({'proposal':i,'variant':v,'engine':engine,'dpi':dpi,'beyond_one_pixel_count':len(points),'beyond_one_pixel_coordinates_xy_and_signed_luma_delta':points,'patch_edge_vs_ring_mean_abs_luma':float(res.mean()) if res.size else None,'patch_edge_vs_ring_max_abs_luma':float(res.max()) if res.size else None,'ring_luma':paper,'ring_samples':int(ring.sum()),'crop':str(out),'crop_sha256':sha(out.read_bytes())})
    print(dpi,engine,i,flush=True)
 if marker.exists():sys.exit('OCR invoked')
 tmp.unlink(missing_ok=True)
(E/'phase-b-render.json').write_text(json.dumps(records,indent=2)+'\n');idx=[]
for i in (243,38,18):
 cells=[]
 for v in ('B0','B1','B2'):
  rr=[]
  for engine in ('splash-aa','cairo','pdfium','mupdf'):
   im=Image.open(L/f'{v}-{i:03}-{engine}-300.png').convert('RGB');mk=Image.open(L/f'{v}-{i:03}-{engine}-300-outside.png').convert('RGB');im=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);mk=mk.resize(im.size,Image.Resampling.NEAREST);rr.append((v,engine,im,mk))
  cells.append(rr)
 cw=max(z[2].width for rr in cells for z in rr)+10;ch=max(z[2].height for rr in cells for z in rr)*2+44;sheet=Image.new('RGB',(cw*4,ch*3),'white');d=ImageDraw.Draw(sheet)
 for y,rr in enumerate(cells):
  for x,(v,e,im,mk) in enumerate(rr):d.text((x*cw+2,y*ch+2),v+' '+e,fill='black');sheet.paste(im,(x*cw+2,y*ch+20));sheet.paste(mk,(x*cw+2,y*ch+24+im.height))
 p=L/f'phase-b-grid-{i:03}.png';sheet.save(p);idx.append({'proposal':i,'path':str(p),'sha256':sha(p.read_bytes())})
(E/'phase-b-panel-index.json').write_text(json.dumps(idx,indent=2)+'\n');print('B renders complete',len(records),flush=True)
