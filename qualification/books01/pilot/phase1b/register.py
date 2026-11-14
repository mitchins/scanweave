#!/usr/bin/env python3
"""Estimate and validate one global output-to-source similarity per pilot render."""
import collections,concurrent.futures,hashlib,json,math,os,pathlib,time
import numpy as np
from PIL import Image
from skimage.feature import SIFT,match_descriptors
from skimage.measure import ransac
from skimage.transform import SimilarityTransform
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[2]; Q=P/'pilot'; corpus=json.loads((P/'corpus.frozen.json').read_text()); ids=corpus['pilot_6'];locks=json.loads((P/'sources.lock.json').read_text())['pages'];render=json.loads((Q/'results/render-costs.json').read_text()); assert len(ids)==6
rows=['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']
def features(im,dpi):
 w,h=im.size;f=min(1.,900/max(w,h));small=im.convert('L').resize((max(1,round(w*f)),max(1,round(h*f))),Image.Resampling.LANCZOS);a=np.asarray(small,dtype=np.float32)/255.;s=SIFT();s.detect_and_extract(a);inds=np.argsort(s.scales)[-1600:];kp=s.keypoints[inds][:,::-1].astype(float);kp[:,0]*=w/small.width*150/dpi;kp[:,1]*=h/small.height*150/dpi;return kp,s.descriptors[inds]
def group(task):
 id,renderer,dpi=task;key=id.split('/')[-1]; root=B/'pilot/renders'/key; source=root/'src'/f'{renderer}-{dpi}.png'; sim=Image.open(source).convert('RGB'); w,h=sim.size
 try:spts,sdesc=features(sim,dpi);serr=None
 except Exception as e:spts=np.empty((0,2));sdesc=None;serr=repr(e)
 output={};cache={}
 for row in rows:
  image=root/row/f'{renderer}-{dpi}.png'; target=B/'pilot/aligned'/key/row/f'{renderer}-{dpi}.png';target.parent.mkdir(parents=True,exist_ok=True); im=Image.open(image).convert('RGB');arr=np.asarray(im);src=np.asarray(sim); equal=arr.shape==src.shape and np.array_equal(arr,src)
  record={'status':'unaccepted','method':'SIFT correspondences, RANSAC similarity','output_dimensions':list(im.size),'source_dimensions':[w,h],'source_type':locks[id]['source_type'],'dpi_confidence':locks[id]['dpi_evidence']['confidence'],'rotation_degrees':None,'scale_x':None,'scale_y':None,'translation_px':None,'inlier_count':0,'match_count':0,'inlier_fraction':None,'residual_median_px_150_equivalent':None,'residual_p95_px_150_equivalent':None,'quadrants_covered':0,'out_of_bounds_fraction':None,'reason':None}
  if equal:
   tr=SimilarityTransform(); record.update(status='accepted',method='exact pixel identity',rotation_degrees=0.,scale_x=1.,scale_y=1.,translation_px=[0.,0.],out_of_bounds_fraction=0.,reason='identical pixel grids')
  else:
   try:
    digest=hashlib.sha256(arr.tobytes()).hexdigest()
    if digest not in cache:cache[digest]=features(im,dpi)
    opt,odesc=cache[digest]; matches=match_descriptors(odesc,sdesc,cross_check=True,max_ratio=.8); record['match_count']=len(matches)
    if len(matches)<8:raise ValueError('fewer than eight descriptor matches')
    srcpts=opt[matches[:,0]];dstpts=spts[matches[:,1]]
    model,inliers=ransac((srcpts,dstpts),SimilarityTransform,min_samples=3,residual_threshold=3,max_trials=1200,rng=0)
    if model is None or inliers is None:raise ValueError('no global fit')
    residual=np.linalg.norm(model(srcpts)-dstpts,axis=1);sel=residual[inliers];n=int(inliers.sum());frac=n/len(matches);med=float(np.median(sel)) if n else None;p95=float(np.percentile(sel,95)) if n else None;angle=float(np.degrees(model.rotation));scale=float(model.scale); quadrants=len({(int(x>=w*150/dpi/2),int(y>=h*150/dpi/2)) for x,y in dstpts[inliers]}); trans=model.translation*dpi/150
    record.update(rotation_degrees=angle,scale_x=scale,scale_y=scale,translation_px=trans.tolist(),inlier_count=n,inlier_fraction=frac,residual_median_px_150_equivalent=med,residual_p95_px_150_equivalent=p95,quadrants_covered=quadrants)
    if n<8 or frac<.60 or quadrants<3 or med>3 or p95>6 or abs(angle)>2 or not (.97<=scale<=1.03):raise ValueError('fit did not meet predeclared acceptance criteria')
    tr=SimilarityTransform(scale=scale,rotation=model.rotation,translation=trans);inv=tr.inverse.params;corners=tr(np.array([[0,0],[im.width,0],[0,im.height],[im.width,im.height]],dtype=float));bounds=[float(corners[:,0].min()),float(corners[:,1].min()),float(corners[:,0].max()),float(corners[:,1].max())];record.update(status='accepted',reason='global fit met criteria',transformed_output_bounds=bounds,out_of_bounds_fraction=None)
   except Exception as e:record['reason']=str(e) if serr is None else 'source feature extraction failed: '+serr
  if record['status']=='accepted':
   if equal: sim.save(target)
   else:
    inv=tr.inverse.params;coeff=tuple(float(x) for x in (inv[0,0],inv[0,1],inv[0,2],inv[1,0],inv[1,1],inv[1,2]));aligned=im.transform((w,h),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC,fillcolor='white');aligned.save(target)
   record['aligned_render_path']=str(target.relative_to(B)); record['interpolation']='none' if equal else 'bicubic, white outside output'
  output[row]=record;im.close()
 sim.close();print(key,renderer,dpi,collections.Counter(x['status'] for x in output.values()),flush=True);return id,renderer,str(dpi),output
tasks=[(id,renderer,dpi) for id in ids for renderer in ['pdfium','poppler','mupdf'] for dpi in sorted({150,int(locks[id]['resolved_dpi'])})];results={}; start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for id,renderer,dpi,v in pool.map(group,tasks):
  for row,r in v.items():results.setdefault(id,{}).setdefault(row,{}).setdefault(renderer,{})[dpi]=r
(Q/'results/phase1b').mkdir(exist_ok=True);(Q/'results/phase1b/geometry.json').write_text(json.dumps({'criteria':'pilot/phase1b/REGISTRATION.md','elapsed_seconds':time.monotonic()-start,'pages':results},indent=2)+'\n')
