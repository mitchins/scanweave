import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
#!/usr/bin/env python3
"""A3/B1 38-glyph PDF for size measurement only, not Phase D qualification."""
import hashlib,io,json,math,os,pathlib,re,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage as nd
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41d'))
from pdf_font import pdf_path
from ownership_guard import require_owned
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_SIZE_ONLY')!='1':sys.exit('size-only switch required')
ledger=R/'hvc41e/review-decisions.json';baseline=R/'local/ink33r/historical.pdf';final=R/'local/hvc41e/final/historical-composed.pdf';side=R/'local/ink33r/historical.pdf.json'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(baseline.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(final.read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0':sys.exit('frozen hash mismatch')
s=json.loads(side.read_text());source=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=source.size
if sha((R.parent/'pdf_packaging/groups/historical-input.pdf').read_bytes())!=s['input_sha256'] or any(sha(p['hocr'].encode())!=p['hocr_sha256'] for p in s['pages']) or [w,h]!=[s['pages'][0]['raster_width'],s['pages'][0]['raster_height']] or sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+source.tobytes())!=s['pages'][0]['pixel_sha256']:sys.exit('OCR or source mismatch')
rows=[x for x in json.loads(ledger.read_text()) if x['decision']=='accept'];outlines=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines'];
if len(rows)!=38:sys.exit('accept count mismatch')
num=re.compile(r'(?<![A-Za-z0-9_.])[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')
def quant(path):
 coords=[]
 def sub(m):
  f=float(m.group());q=round(f,3);coords.append((f,q));return f'{q:.3f}'.rstrip('0').rstrip('.') if q else '0'
 return num.sub(sub,path),coords
# Exact degenerate segments only: no arbitrary curve simplification.
def simplify(path,matrix,pw,ph):
 tokens=path.split();out=[];args=[];cur=None;start=None;removed=0;max_bound=0.0
 a,b,c,d,_,_=matrix
 def transform(p):return np.array([(a*p[0]+c*p[1])/2048*w/pw,(b*p[0]+d*p[1])/2048*h/ph])
 for t in tokens:
  if t not in ('m','l','c','h'):args.append(t);continue
  if t=='m':cur=(float(args[0]),float(args[1]));start=cur
  elif t=='l':
   pt=(float(args[0]),float(args[1]));
   if pt==cur:removed+=1;args=[];continue
   cur=pt
  elif t=='c':
   pts=[(float(args[j]),float(args[j+1])) for j in (0,2,4)]
   if cur is not None and all(p==cur for p in pts):removed+=1;args=[];continue
   if cur is not None:
    origin=transform(cur); c1=transform(pts[0])-origin;c2=transform(pts[1])-origin;end=transform(pts[2])-origin;length=float(np.linalg.norm(end))
    if length>0:
     t1=float(c1@end/(length*length));t2=float(c2@end/(length*length));bound=max(abs(float(end[0]*c1[1]-end[1]*c1[0]))/length,abs(float(end[0]*c2[1]-end[1]*c2[0]))/length)
     # Convex-hull distance bound and monotone projection preserve the direction of travel.
     if 0<=t1<=t2<=1 and bound<=0.01:
      args=[args[4],args[5]];t='l';removed+=1;max_bound=max(max_bound,bound)
   cur=pts[-1]
  elif t=='h':cur=start
  out.extend(args);out.append(t);args=[]
 if args:raise ValueError('invalid path')
 return ' '.join(out),removed,max_bound
def sampled_deviation(original,modified,matrix,pw,ph):
 def commands(path):
  args=[];out=[]
  for token in path.split():
   if token in ('m','l','c','h'):out.append((token,[float(x) for x in args]));args=[]
   else:args.append(token)
  return out
 aa=commands(original);bb=commands(modified)
 if len(aa)!=len(bb):raise ValueError('unpaired outline operations')
 a,b,c,d,_,_=matrix
 def point(p):return np.array([(a*p[0]+c*p[1])/2048*w/pw,(b*p[0]+d*p[1])/2048*h/ph])
 errs=[];old=None;new=None;oldstart=None;newstart=None
 for (op,x),(qp,y) in zip(aa,bb):
  if op=='m':old=point(x);new=point(y);oldstart=old;newstart=new
  elif op=='c':
   p0=old;p1=point(x[0:2]);p2=point(x[2:4]);p3=point(x[4:6]);q0=new
   if qp=='c':q1=point(y[0:2]);q2=point(y[2:4]);q3=point(y[4:6])
   elif qp=='l':q3=point(y[0:2]);seg=q3-q0;norm=float(seg@seg)
   else:raise ValueError('unexpected simplified operator')
   for t in np.linspace(0,1,17):
    v=(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
    if qp=='c':u=(1-t)**3*q0+3*(1-t)**2*t*q1+3*(1-t)*t*t*q2+t**3*q3
    else:
     z=max(0,min(1,float((v-q0)@seg/norm))) if norm else 0;u=q0+z*seg
    errs.append(float(np.linalg.norm(v-u)))
   old=p3;new=q3
  elif op=='h':old=oldstart;new=newstart
  else:raise ValueError('unexpected frozen contour operation')
 return (float(np.mean(errs)),float(max(errs))) if errs else (0.0,0.0)
def mask_for(path,bb,sc):
 x0,y0,x1,y1=bb;cw=max(5,math.ceil((x1-x0)*sc)+10);ch=max(5,math.ceil((y1-y0)*sc)+10);pdf=pikepdf.Pdf.new();p=pdf.add_blank_page(page_size=(cw,ch));ops=f'q 0 0 0 rg {sc} 0 0 {sc} {5-x0*sc} {5-y0*sc} cm {path} f Q';p.Contents=pdf.make_stream(ops.encode());buf=io.BytesIO();pdf.save(buf);pdf.close();d=pdfium.PdfDocument(buf.getvalue());p=d[0];im=np.asarray(p.render(scale=1,rev_byteorder=True).to_pil().convert('L'));p.close();d.close();return im<128
def topology(m):
 comp=nd.label(m,structure=np.ones((3,3),bool))[1];lab,n=nd.label(~m,structure=np.ones((3,3),bool));edge=set(np.unique(np.concatenate((lab[0,:],lab[-1,:],lab[:,0],lab[:,-1]))));holes=sum(i not in edge for i in range(1,n+1));return [comp,holes]
from mask_path import mask_polygons
with tempfile.TemporaryDirectory(prefix='hvc41f-c-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(side)
 pdf=pikepdf.open(baseline);page=pdf.pages[0];pw=float(page.MediaBox[2]);ph=float(page.MediaBox[3]);old=page.Contents
 with pikepdf.open(final) as f:
  pat=f.pages[0].Resources.Pattern['/Research41E'];origlines=pat.read_bytes().decode().splitlines();font=pat.Resources.Font.FR;frozen=[font.CharProcs[f'/g{i}'].read_bytes() for i in range(1,39)]
 with pikepdf.open(baseline) as p:bg=np.asarray(pikepdf.PdfImage(p.pages[0].Resources.XObject['/Im0']).as_pil_image().convert('RGB').resize((w,h),Image.Resampling.BILINEAR)).copy()
 ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;lum=bg@np.array([.2126,.7152,.0722]);paths=[];patchops=['q'];metrics=[]
 for index,r in enumerate(rows,1):
  i=r['proposal'];g=outlines[i];original=pdf_path(g['path_svg']);expected=('2048 0 d0 '+original+' f').encode();m=' '.join(str(x) for x in g['matrix']);rgb=' '.join(f'{x/255:.8f}' for x in r['fill_rgb']);expectedline=f'BT /FR 1 Tf {rgb} rg {m} Tm <{index:02x}> Tj ET'
  if frozen[index-1]!=expected or origlines[index-1]!=expectedline or g['symbol']!=r['symbol_id']:sys.exit(f'frozen glyph mismatch {i}')
  q,coords=quant(original);q,removed,curve_bound=simplify(q,g['matrix'],pw,ph);sample_mean,sample_max=sampled_deviation(original,q,g['matrix'],pw,ph);pt=np.array(coords,dtype=float).reshape(-1,2,2);dif=pt[:,:,1]-pt[:,:,0];a0,b0,c0,d0,_,_=g['matrix'];err=np.hypot((a0*dif[:,0]+c0*dif[:,1])/2048*w/pw,(b0*dif[:,0]+d0*dif[:,1])/2048*h/ph)
  pen=BoundsPen(None);parse_path(g['path_svg'],pen);sc=max(abs(a0)/2048*w/pw,abs(d0)/2048*h/ph)*4;oldmask=mask_for(original,pen.bounds,sc);newmask=mask_for(q,pen.bounds,sc);top0=topology(oldmask);top1=topology(newmask);contour0=original.split().count('h');contour1=q.split().count('h')
  if top0!=top1 or contour0!=contour1:sys.exit(f'quantisation topology differs {i}: {top0} {top1}')
  mat=[a0/2048,b0/2048,c0/2048,d0/2048,g['matrix'][4],g['matrix'][5]];paths.append('q '+rgb+' rg '+' '.join(str(v) for v in mat)+' cm '+q+' f Q')
  a,b,c,d=r['reference_box'];maps={}
  for k in ('patch','owner'):
   spec=r['masks'][k];data=pathlib.Path(spec['path']).read_bytes()
   if sha(data)!=spec['sha256']:sys.exit('mask hash mismatch')
   maps[k]=np.asarray(Image.open(io.BytesIO(data)).convert('L'))>0
  require_owned(maps['patch'],maps['owner']);x0=max(0,a-16);y0=max(0,b-16);x1=min(w,c+16);y1=min(h,d+16);local=bg[y0:y1,x0:x1];ll=lum[y0:y1,x0:x1];mask=np.zeros(ll.shape,bool);mask[b-y0:d-y0,a-x0:c-x0]=maps['patch'];owner=np.zeros(ll.shape,bool);owner[b-y0:d-y0,a-x0:c-x0]=maps['owner'];ring=nd.binary_dilation(mask,iterations=12)&~nd.binary_dilation(mask,iterations=1)&~ref[y0:y1,x0:x1]&~owner;v=ll[ring]
  if len(v)<8:sys.exit('insufficient paper evidence')
  ring &= ll>=np.percentile(v,50);tone=np.median(local[ring],axis=0);loops=mask_polygons(maps['patch']);patchops.append(' '.join(f'{z/255:.9f}' for z in tone)+' rg')
  for loop in loops:
   # Collinear vertices are redundant on the exact pixel grid.
   points=loop[:-1];compressed=[]
   for k,pt0 in enumerate(points):
    before=points[k-1];after=points[(k+1)%len(points)]
    if (pt0[0]-before[0])*(after[1]-pt0[1])==(pt0[1]-before[1])*(after[0]-pt0[0]):continue
    compressed.append(pt0)
   if len(compressed)<3:raise ValueError('degenerate patch contour')
   for k,(xx,yy) in enumerate(compressed):patchops.append(f'{(a+xx)*pw/w:.9f} {ph-(b+yy)*ph/h:.9f} '+('m' if k==0 else 'l'))
   patchops.append('h')
  patchops.append('f*')
  metrics.append({'proposal':i,'symbol':r['symbol_id'],'contours_before':contour0,'contours_after':contour1,'raster_components_and_holes_before':top0,'raster_components_and_holes_after':top1,'raster_pixels_changed_at_4x':int((oldmask!=newmask).sum()),'max_control_point_error_source_px':float(err.max()) if err.size else 0,'mean_control_point_error_source_px':float(err.mean()) if err.size else 0,'simplified_or_removed_segments':removed,'max_curve_simplification_error_source_px':curve_bound,'sampled_mean_geometric_error_source_px':sample_mean,'sampled_max_geometric_error_source_px':sample_max,'patch_outside_owned':int((maps['patch']&~maps['owner']).sum())})
 patchops.append('Q');form=pdf.make_stream(('\n'.join(paths)).encode());form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;form.BBox=pikepdf.Array(page.MediaBox);form.Resources=pikepdf.Dictionary();page.Resources.XObject['/ResearchPaths']=form;patchstream=pdf.make_stream(('\n'.join(patchops)).encode());draw=pdf.make_stream(b'q /ResearchPaths Do Q');page.Contents=pikepdf.Array([old,patchstream,draw]);out=L/'SIZE-MEASUREMENT-NOT-FINAL.pdf';pdf.save(out);pdf.close()
 with pikepdf.open(out) as p:
  page=p.pages[0];x=page.Resources.XObject;path_raw=len(x['/ResearchPaths'].read_raw_bytes());images_raw=0;patch_raw=len(page.Contents[1].read_raw_bytes());draw_raw=len(page.Contents[2].read_raw_bytes());stream_raw=patch_raw+draw_raw
 delta=out.stat().st_size-baseline.stat().st_size;result={'description':'38-glyph size measurement only; not a final qualified PDF','rendering':'A3 path-only Form XObject; no embedded research font','patch':'B1 median decoded-background paper ring and exact combined pixel-union contours','baseline_bytes':baseline.stat().st_size,'bytes':out.stat().st_size,'sha256':sha(out.read_bytes()),'delta':delta,'compressed_form_path_bytes':path_raw,'compressed_patch_bytes':patch_raw,'compressed_image_and_smask_bytes':images_raw,'compressed_patch_and_draw_stream_bytes':stream_raw,'structural_overhead_bytes':delta-path_raw-images_raw-stream_raw,'glyphs':metrics,'ocr_stub_not_invoked':not marker.exists()}
 if marker.exists():sys.exit('OCR invoked')
(E/'phase-c-size.json').write_text(json.dumps(result,indent=2)+'\n');print('size-only',out.stat().st_size,'delta',delta,'raw streams',path_raw,images_raw,stream_raw,flush=True)
