"""Render all historical pages; classify every changed p1 pixel outside ownership."""
import pathlib,subprocess,json,hashlib,os
import numpy as np,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';(L/'renders').mkdir(exist_ok=True);(L/'diffs').mkdir(exist_ok=True);rows=[r for r in json.loads((E/'review-decisions.json').read_text()) if r['decision']=='accept'];owner=np.zeros((2355,1738),bool)
for r in rows:
 a,b,c,d=r['reference_box'];m=np.asarray(Image.open(r['masks']['owner']['path']).convert('L'))>0;owner[b:d,a:c]|=m
candidate=L/'historical-composed.pdf';out=[];wt=np.array([.2126,.7152,.0722])
for dpi in (96,300):
 for engine in ('pdfium','poppler','mupdf'):
  for page in range(1,6):
   baseline=R/f'local/hvc41d/renders/{engine}-{dpi}-{page:02}-baseline.png';dest=L/'renders'/f'{engine}-{dpi}-{page:02}-candidate.png'
   if engine=='pdfium':
    doc=pdfium.PdfDocument(str(candidate));p=doc[page-1];im=p.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB');p.close();doc.close();im.save(dest)
   elif engine=='poppler':subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-r',str(dpi),'-png','-singlefile',str(candidate),str(dest.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
   else:
    code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[int(sys.argv[4])-1].get_pixmap(matrix=pymupdf.Matrix(float(sys.argv[3])/72,float(sys.argv[3])/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(candidate),str(dest),str(dpi),str(page)],check=True)
   b=np.asarray(Image.open(baseline).convert('RGB'));c=np.asarray(Image.open(dest).convert('RGB'))
   if b.shape!=c.shape:raise RuntimeError(f'geometry mismatch {engine} {dpi} {page}')
   changed=np.any(b!=c,axis=2);entry={'engine':engine,'dpi':dpi,'page':page,'dimensions':[b.shape[1],b.shape[0]],'changed_pixels':int(changed.sum()),'candidate_render':str(dest),'candidate_render_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
   if page==1:
    mapped=np.asarray(Image.fromarray(owner).resize((b.shape[1],b.shape[0]),Image.Resampling.NEAREST));outside=changed&~mapped;edge=nd.binary_dilation(mapped,structure=np.ones((3,3),bool))&~mapped;boundary=outside&edge;other=outside&~edge;dl=(c.astype(float)-b.astype(float))@wt
    def points(mask):
     yy,xx=np.nonzero(mask);return [[int(x),int(y),round(float(dl[y,x]),4)] for y,x in zip(yy,xx)]
    pixels={'classification':'boundary = outside mapped source-owner mask, within one render pixel in 8-connectivity; other = all remaining outside pixels','coordinates':'zero-based x,y from top-left; delta_luma=candidate minus baseline Rec.709','boundary':points(boundary),'other':points(other)};f=E/f'outside-pixels-{engine}-{dpi}.json';f.write_text(json.dumps(pixels,separators=(',',':'))+'\n');mask=np.zeros((*changed.shape,3),np.uint8);mask[boundary]=[255,200,0];mask[other]=[255,0,0];mf=L/'diffs'/f'{engine}-{dpi}-outside.png';Image.fromarray(mask).save(mf);entry.update({'outside_owned_pixels':int(outside.sum()),'boundary_pixels':int(boundary.sum()),'other_pixels':int(other.sum()),'boundary_luma_delta_min':float(dl[boundary].min()) if boundary.any() else None,'boundary_luma_delta_max':float(dl[boundary].max()) if boundary.any() else None,'other_luma_delta_min':float(dl[other].min()) if other.any() else None,'other_luma_delta_max':float(dl[other].max()) if other.any() else None,'pixel_list':str(f),'pixel_list_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'diff_mask':str(mf),'diff_mask_sha256':hashlib.sha256(mf.read_bytes()).hexdigest()})
   out.append(entry);print(engine,dpi,page,'changed',entry['changed_pixels'],'outside',entry.get('outside_owned_pixels'), 'other',entry.get('other_pixels'),flush=True)
(E/'render-phase2.json').write_text(json.dumps(out,indent=2)+'\n')
