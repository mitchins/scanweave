#!/usr/bin/env python3
"""Diagnostic truth-assisted source-mask and physical-scale counterfactuals."""
from pathlib import Path
from collections import defaultdict
import json,random,hashlib,re,os
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,map_coordinates
from scipy.optimize import least_squares
R=Path('/data/coding/scanweave/qualification'); L=R/'acr06/local/c2b'; T=L/'trace'; D=L/'detail'; pairs=json.loads((L/'truth-pair-details.json').read_text()); sources={'p2':('P2','p2'),'p2prime':('P2prime','p2prime'),'p2pp':('P2pp','p2pp')}; rng=random.Random(270627)
limit=int(os.environ.get('SCANWEAVE_DECOMPOSE_LIMIT','60')); only=os.environ.get('SCANWEAVE_DECOMPOSE_DOCUMENTS'); pairs={k:v for k,v in pairs.items() if not only or k in only.split(',')}
# Stratify across documents, then sample within error quartiles using round-robin.
selected=[]
for dpi in (300,600):
 docs=sorted(n for n in pairs if int(n.rsplit('-',1)[1])//3==(1 if dpi==300 else 2)); bins=[]
 for doc in docs:
  options=[(doc,int(i),v['canonical']) for i,v in pairs[doc]['best']['same']['members'].items() if v['error']>.08]; rng.shuffle(options);bins.append(options)
 while len([x for x in selected if x[0]==dpi])<limit and any(bins):
  for b in bins:
   if b and len([x for x in selected if x[0]==dpi])<limit:selected.append((dpi,*b.pop()))
# Include all 12 originally selected pairs, whether or not truth matches them.
doc='p2-6'; tr=json.load((T/f'{doc}.pdf.funnel.json').open());rows=tr['rows']; above=[]
for row in rows:
 i=row['member']; fs=[f for f in tr['fits'] if f['member']==i and f['canonical']!=i and not f['reasons'] and rows[f['canonical']]['band']==row['band'] and not rows[f['canonical']]['hygiene'] and f['error']/max(row['floor'],1e-6)<=2]
 if fs:
  f=min(fs,key=lambda z:z['error'])
  if .08<f['error']<.3 and re.fullmatch(r'w\d+s\d+',row['id']) and re.fullmatch(r'w\d+s\d+',rows[f['canonical']]['id']):above.append((f['error'],i,f['canonical']))
for e,i,j in sorted(above,reverse=True)[:12]:
 if (600,doc,i,j) not in selected:selected.append((600,doc,i,j))
for document, data in sorted(pairs.items()):
 if int(document.rsplit('-',1)[1]) < 6:continue
 for member, item in data['best']['same']['members'].items():
  candidate=(600,document,int(member),item['canonical'])
  if len([x for x in selected if x[0]==600])>=limit+12:break
  if item['error']>.08 and candidate not in selected:selected.append(candidate)
def sample(a,x,y):
 # scanweave sample returns zero outside the pixel-centre range
 x=np.asarray(x);y=np.asarray(y);valid=(x>=0)&(y>=0)&(x<=a.shape[1]-1)&(y<=a.shape[0]-1);return np.where(valid,map_coordinates(a,[y,x],order=1,mode='nearest',prefilter=False),0.)
Y,X=np.mgrid[:64,:64]
def canvas(native,origin,frame,scale=None):
 sc=scale or frame['scale'];return sample(native,frame['cx']+(X-32)/sc-origin[0]-.5,frame['baseline']+(Y-48)/sc-origin[1]-.5)
def warp(c,p):return sample(c,32+(X-32-p[0])/p[2],48+(Y-48-p[1])/p[2])
def mse(a,b):return float(((a-b)**2).sum()/max(np.maximum(a,b).sum(),1.))
def optimize(a,c,initial):
 res=least_squares(lambda p:(warp(c,p)-a).ravel(),np.clip(initial,[-1.999999,-1.999999,.9800001],[1.999999,1.999999,1.0199999]),bounds=([-2,-2,.98],[2,2,1.02]),loss='huber',f_scale=.12,max_nfev=60)
 return mse(a,warp(c,res.x)),res.x.tolist()
records=[]; panels=[]
for doc in sorted({x[1] for x in selected}):
 path=D/f'{doc}.pdf.detail.json'
 if not path.exists():raise RuntimeError(f'missing {path}')
 detail=json.load(path.open());trace=json.load((T/f'{doc}.pdf.funnel.json').open());fits={(f['member'],f['canonical']):f for f in trace['fits']}; matches=pairs[doc]['matches'];name,si=doc.rsplit('-',1);sheet=int(si);folder,sub=sources[name];root=R/'font04/local'/folder/sub; page=np.asarray(Image.open(root/f'page-{sheet//3}-{sheet%3}.png').convert('L'))
 observations=[json.loads(x) for x in (root/'observations.jsonl').open()];truth_rows=[o for o in observations if o['page']==sheet//3 and o['sheet']==sheet%3]
 # Oracle masks also identify other truth glyphs, preventing their ink being restored.
 for dpi,_,i,j in [x for x in selected if x[1]==doc]:
  rr=detail[i];src=rr['source'];frame=rr['frame'];fit=fits.get((i,j));match=matches.get(str(i));other=matches.get(str(j));
  if not src or not frame or not fit or not match or not other or detail[j]['frame'] is None:
   records.append({'dpi':dpi,'document':doc,'member':i,'canonical':j,'status':'unmatched_or_missing'});continue
  h,w=src['height'],src['width'];mask=np.pad(np.array(src['mask'],bool).reshape(h,w),2);gray=np.array(src['gray_halo'],float).reshape(h+4,w+4);on=gray[mask];off=gray[~mask]
  if not len(on) or not len(off):continue
  paper=float(np.quantile(off,.8));ink=float(np.quantile(on,.15));color=np.dot(rr['paper'],[.2126,.7152,.0722]);foreign=(np.abs(gray-color)>60)&~mask;dist=distance_transform_edt(~mask);fd=distance_transform_edt(~foreign) if foreign.any() else np.full(gray.shape,100.);prepared=np.where((dist<=1.5)&(dist<fd),np.clip((paper-gray)/(paper-ink),0,1),0)
  x0,y0=map(int,src['bbox'][:2]);gx,gy,gx2,gy2=match['bbox']; px=np.asarray(Image.open(root/'oracle'/f"{match['truth_id']}-pristine.png").convert('L')); own=(255-px)/255.; H,W=page.shape; ax=max(0,min(x0-2,gx));ay=max(0,min(y0-2,gy));bx=min(W,max(x0+w+2,gx2));by=min(H,max(y0+h+2,gy2)); native=np.zeros((by-ay,bx-ax)); nx=x0-2-ax;ny=y0-2-ay;native[ny:ny+h+4,nx:nx+w+4]=prepared
  truth=np.zeros_like(native); tx=max(gx,ax);ty=max(gy,ay);te=min(gx2,bx);tf=min(gy2,by);truth[ty-ay:tf-ay,tx-ax:te-ax]=own[ty-gy:tf-gy,tx-gx:te-gx]; source=(255-page[ay:by,ax:bx])/255.;other_ink=np.zeros_like(native,dtype=bool)
  for ob in truth_rows:
   if ob['id']==match['truth_id']:continue
   ox,oy,ox2,oy2=ob['bbox'];lx=max(ox,ax);ly=max(oy,ay);rx=min(ox2,bx);ry=min(oy2,by)
   if lx>=rx or ly>=ry:continue
   z=np.asarray(Image.open(root/'oracle'/f"{ob['id']}-pristine.png").convert('L'));other_ink[ly-ay:ry-ay,lx-ax:rx-ax]|=z[ly-oy:ry-oy,lx-ox:rx-ox]<224
  support=truth>.12; safe=support & ~other_ink; repaired=native.copy(); repaired[safe]=np.maximum(repaired[safe],source[safe]);mass=truth.sum();missing=float((truth*(native<.05)).sum()/mass) if mass else None; source_missing=float((truth*(source<.05)).sum()/mass) if mass else None; extra_mask=float((truth*(source>=.05)*(native<.05)).sum()/mass) if mass else None
  orig=np.array(rr['field']).reshape(64,64); canon=np.array(detail[j]['canonical_field']).reshape(64,64);calc=canvas(prepared,(x0-2,y0-2),frame);fix=canvas(repaired,(ax,ay),frame); relative_true=match['point_size']/other['point_size']; estimated=frame['xheight']/detail[j]['frame']['xheight']; desired=detail[j]['frame']['xheight']*relative_true; scale_fix=32/desired;scaled=canvas(prepared,(x0-2,y0-2),frame,scale_fix); both=canvas(repaired,(ax,ay),frame,scale_fix);p=fit['parameters'];base=mse(orig,warp(canon,p));fixed,pfix=optimize(fix,canon,p);scored,pscale=optimize(scaled,canon,p);joint,pjoint=optimize(both,canon,p)
  rec={'dpi':dpi,'document':doc,'member':i,'canonical':j,'id':rr['id'],'canonical_id':detail[j]['id'],'same_design':all(match[k]==other[k] for k in ('character','font_sha256')),'truth_member':match,'truth_canonical':other,'original_fit':fit['error'],'baseline_recomputed':base,'reconstruction_max_abs':float(np.max(np.abs(calc-orig))),'pristine_missing_fraction':missing,'missing_in_source_fraction':source_missing,'additional_mask_loss_fraction':extra_mask,'excluded_overlap_fraction':float((truth*other_ink).sum()/mass) if mass else None,'estimated_xheight_ratio':estimated,'true_point_size_ratio':relative_true,'registration':p,'unregistered_fit':mse(orig,canon),'registration_error_reduction':mse(orig,canon)-base,'residual_after_joint':joint,'repaired_fit':fixed,'true_scale_fit':scored,'repaired_true_scale_fit':joint,'repaired_registration':pfix,'true_scale_registration':pscale,'joint_registration':pjoint,'status':'ok'};records.append(rec)
  if dpi==600:
   a=Image.fromarray(np.uint8(np.clip((1-native)*255,0,255)));b=Image.fromarray(page[ay:by,ax:bx]);c=Image.fromarray(np.uint8(np.clip((1-truth)*255,0,255)));panels.append((rec,a,b,c))
 print(doc, len(records),flush=True)
(L/'decomposition-records.json').write_text(json.dumps(records,indent=2)+'\n')
panels=sorted(panels,key=lambda item:item[0]['additional_mask_loss_fraction'],reverse=True)[:40]
width=900;rowheight=130;sheetim=Image.new('RGB',(width,rowheight*len(panels)),'white');draw=ImageDraw.Draw(sheetim)
for n,(rec,a,b,c) in enumerate(panels):
 for col,im in enumerate((a,b,c)):
  im=im.convert('RGB');im.thumbnail((220,95));sheetim.paste(im,(col*230,n*rowheight+22))
 draw.text((0,n*rowheight),f"{rec['document']} {rec['id']} > {rec['canonical_id']} same={rec['same_design']} masked={rec['additional_mask_loss_fraction']:.3f} : prepared | source | pristine",fill='black')
p=L/'masking-contact.png';sheetim.save(p)
summary={'seed':270627,'selection':'up to 60 per DPI, round-robin documents; plus 12 earlier source-pair examples','selected':len(selected),'results':len(records),'status_counts':{s:sum(r['status']==s for r in records) for s in set(r['status'] for r in records)},'contact_sha256':hashlib.sha256(p.read_bytes()).hexdigest()};(R/'acr06/c2b/decomposition-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
