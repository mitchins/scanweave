#!/usr/bin/env python3
"""Compare A4 artifact font with the A3/B1 Form in four renderers."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
import numpy as np,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';D=L/'final';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_A4_RENDER')!='1':sys.exit('A4 render switch required')
if sha((R/'hvc41e/review-decisions.json').read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha((R/'local/hvc41e/final/historical-composed.pdf').read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0' or sha((R/'local/ink33r/historical.pdf').read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b':sys.exit('hash mismatch')
attempt=json.loads((E/'a4-attempts.json').read_text())[-1];strategy=attempt['strategy'];assert all(x['pdfium_text_equal'] and x['poppler_text_equal'] and x['pdfium_search_equal'] for x in attempt['results']);rows={r['proposal']:r for r in json.loads((R/'hvc41e/review-decisions.json').read_text()) if r['decision']=='accept'};engines=['splash-aa','cairo','pdfium','mupdf'];w,h=1738,2355;records=[]
def render(path,engine,dpi,out):
 if engine=='pdfium':
  d=pdfium.PdfDocument(str(path));p=d[0];p.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB').save(out);p.close();d.close()
 elif engine=='mupdf':
  code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[0].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(out),str(dpi)],check=True)
 else:
  exe='pdftocairo' if engine=='cairo' else 'pdftoppm';opts=[] if engine=='cairo' else ['-aa','yes','-aaVector','yes'];subprocess.run([exe,'-f','1','-l','1','-r',str(dpi),'-png','-singlefile',*opts,str(path),str(out.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
with tempfile.TemporaryDirectory(prefix='hvc41f-a4-render-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=D/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json');tmp=D/'scratch-a4.png'
 for dpi in (96,300):
  for engine in engines:
   render(R/'local/ink33r/historical.pdf',engine,dpi,tmp);baseline=np.asarray(Image.open(tmp).convert('RGB'));H,W=baseline.shape[:2]
   for i in (243,38,18):
    r=rows[i];a,b,c,d=r['reference_box'];owner=np.zeros((h,w),np.uint8);owner[b:d,a:c]=(np.asarray(Image.open(r['masks']['owner']['path']).convert('L'))>0);own=np.asarray(Image.fromarray(owner).resize((W,H),Image.Resampling.NEAREST))>0;bound=nd.binary_dilation(own,structure=np.ones((3,3),bool));box=(max(0,int((a-8)*W/w)),max(0,int((b-8)*H/h)),min(W,int(np.ceil((c+8)*W/w))),min(H,int(np.ceil((d+8)*H/h))))
    render(L/f'B1-patch-only-{i:03}.pdf',engine,dpi,tmp);patch=np.asarray(Image.open(tmp).convert('RGB'))
    for variant in ('A3','A4'):
     path=L/f'B1-{i:03}.pdf' if variant=='A3' else D/f'A4-{strategy}-{i:03}.pdf';render(path,engine,dpi,tmp);im=np.asarray(Image.open(tmp).convert('RGB'));delta=np.max(abs(im.astype(int)-patch.astype(int)),axis=2);mask=delta>10;outside=np.any(im!=baseline,axis=2)&~bound;yy,xx=np.nonzero(outside);dl=(im.astype(float)-baseline.astype(float))@np.array([.2126,.7152,.0722]);crop=Image.fromarray(im).crop(box);dest=D/f'{variant}-{i:03}-{engine}-{dpi}.png';crop.save(dest);Image.fromarray(mask.astype(np.uint8)*255).crop(box).save(D/f'{variant}-{i:03}-{engine}-{dpi}-mask.png');records.append({'proposal':i,'dpi':dpi,'engine':engine,'variant':variant,'outside_count':int(outside.sum()),'outside_xy_delta_luma':[[int(x),int(y),float(dl[y,x])] for y,x in zip(yy,xx)],'mask_bbox':box,'crop':str(dest),'crop_sha256':sha(dest.read_bytes())})
    print(dpi,engine,i,flush=True)
 if marker.exists():sys.exit('OCR invoked')
 tmp.unlink(missing_ok=True)
for r in records:
 ref=next(x for x in records if x['dpi']==r['dpi'] and x['proposal']==r['proposal'] and x['variant']==r['variant'] and x['engine']=='pdfium');a=np.asarray(Image.open(D/f"{r['variant']}-{r['proposal']:03}-{r['engine']}-{r['dpi']}-mask.png"))>0;b=np.asarray(Image.open(D/f"{r['variant']}-{r['proposal']:03}-pdfium-{r['dpi']}-mask.png"))>0;ba=r['mask_bbox'];bb=ref['mask_bbox'];shape=(max(ba[3],bb[3]),max(ba[2],bb[2]));m=np.zeros(shape,bool);n=np.zeros(shape,bool);m[ba[1]:ba[3],ba[0]:ba[2]]=a;n[bb[1]:bb[3],bb[0]:bb[2]]=b;den=(m|n).sum();r['iou_to_pdfium']=float((m&n).sum()/den) if den else None
checks=[]
for i in (243,38,18):
 for dpi in (96,300):
  for e in engines:
   a=next(x for x in records if (x['proposal'],x['dpi'],x['engine'],x['variant'])==(i,dpi,e,'A3'));b=next(x for x in records if (x['proposal'],x['dpi'],x['engine'],x['variant'])==(i,dpi,e,'A4'));checks.append({'proposal':i,'dpi':dpi,'engine':e,'a3_iou':a['iou_to_pdfium'],'a4_iou':b['iou_to_pdfium'],'a3_outside':a['outside_count'],'a4_outside':b['outside_count'],'a4_not_worse_iou':b['iou_to_pdfium']>=a['iou_to_pdfium'],'a4_not_worse_outside':b['outside_count']<=a['outside_count']})
accepted=all(x['a4_not_worse_iou'] and x['a4_not_worse_outside'] and (x['engine']!='splash-aa' or x['a4_outside']==0) for x in checks);data={'strategy':strategy,'checks':checks,'a4_pass':accepted,'chosen':'A4' if accepted else 'A3','records':records};(E/'a4-render.json').write_text(json.dumps(data,indent=2)+'\n');print('A4 pass',accepted,flush=True)
