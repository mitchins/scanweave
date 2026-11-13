#!/usr/bin/env python3
"""Dev-only patch correlation in the access frame; no holdout image opens."""
import json,pathlib,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from scipy.optimize import least_squares
from skimage.feature import match_template
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
pages=[p for p in json.loads((P/'corpus.proposed.json').read_text())['pages'] if p['source']=='finebooks-bhl-impact' and p['split']=='dev']
info=json.loads((B/'src/ia/dev-jp2.json').read_text())
def mask_polys(size,root,scale=(1,1),offset=(0,0)):
 mask=Image.new('1',size); draw=ImageDraw.Draw(mask); n=0
 for line in root.iter():
  if line.tag.rsplit('}',1)[-1]!='TextLine': continue
  c=next((e for e in line if e.tag.rsplit('}',1)[-1]=='Coords'),None)
  if c is None or not c.get('points'): continue
  pts=[tuple(map(float,p.split(','))) for p in c.get('points').split()]; draw.polygon([(round(x*scale[0]+offset[0]),round(y*scale[1]+offset[1])) for x,y in pts],fill=1); n+=1
 return np.asarray(mask,dtype=bool),n
def run(p):
 id=p['id']; d=info[id]; work=p['work']; page=str(p['page']); src=B/d['path']; access=B/'src/finebooks/pages'/work/page/'image.webp'; gt=B/'src/finebooks/pages'/work/page/'gt.xml'
 orig=Image.open(src).convert('L'); acc=Image.open(access).convert('L'); a=np.asarray(acc,dtype=np.uint8); xml=ET.parse(gt).getroot()
 node=ET.parse(B/'src/ia'/work/'scandata.xml').find(f'./pageData/page[@leafNum="{d["leaf"]}"]'); crop=node.find('cropBox'); cx=int(crop.findtext('x')); cy=int(crop.findtext('y'))
 # Test all exact orientations. Match a grid of distinct 128px access patches in a +/- 80px window around the metadata crop location.
 best=None
 for angle in (0,90,180,270):
  rot=orig.rotate(angle,expand=True); im=np.asarray(rot,dtype=np.uint8); pairs=[]
  for y in np.linspace(100,a.shape[0]-101,5,dtype=int):
   for x in np.linspace(100,a.shape[1]-101,5,dtype=int):
    half=64; search=80; patch=a[y-half:y+half,x-half:x+half]; x0=cx+x-half-search; y0=cy+y-half-search; x1=cx+x+half+search; y1=cy+y+half+search
    if x0<0 or y0<0 or x1>im.shape[1] or y1>im.shape[0] or patch.std()<12: continue
    score=match_template(im[y0:y1,x0:x1],patch); j,i=np.unravel_index(np.argmax(score),score.shape); peak=float(score[j,i]);
    if peak>=0.45: pairs.append((float(x),float(y),float(x0+i+half),float(y0+j+half),peak))
  if best is None or len(pairs)>len(best[1]): best=(angle,pairs,rot)
 angle,pairs,rot=best
 result={'id':id,'leaf':d['leaf'],'rotation_ccw':angle,'patches':len(pairs),'method':'128px NCC grid; +/-80px search from scandata crop, score >=0.45; robust anisotropic scale and translation','acceptance':'p95 inlier residual <=2px, >=8 inliers, >=0.8 fraction, ink containment delta >=-0.02','decision':'webp','lossy_origin':True,'reason':'insufficient spatially separated matches','scale':None,'translation':None,'inlier_fraction':0.0,'residual_p95_px':None,'ink_containment_delta':None}
 if len(pairs)<8: return result
 q=np.asarray(pairs); fit=least_squares(lambda t:np.r_[q[:,2]-(t[0]*q[:,0]+t[2]),q[:,3]-(t[1]*q[:,1]+t[3])],[1,1,cx,cy],loss='soft_l1',f_scale=2).x
 dist=np.hypot(q[:,2]-(fit[0]*q[:,0]+fit[2]),q[:,3]-(fit[1]*q[:,1]+fit[3])); inside=dist<=2; fraction=float(inside.mean()); n=int(inside.sum()); residual=float(np.percentile(dist[inside],95)) if n else None
 result.update(scale=fit[:2].tolist(),translation=fit[2:].tolist(),inliers=n,inlier_fraction=fraction,residual_p95_px=residual,reason='correlation residual or inlier requirement failed')
 if n<8 or fraction<.8 or min(fit[:2])<=0: return result
 amask,lines=mask_polys(acc.size,xml); jmask,_=mask_polys(rot.size,xml,fit[:2],fit[2:]); ai=np.asarray(acc)<128; ji=np.asarray(rot)<128
 if not lines or not ai.any() or not ji.any(): result['reason']='no measurable GT line ink'; return result
 av=float((ai & amask).sum()/ai.sum()); jv=float((ji & jmask).sum()/ji.sum()); delta=jv-av
 result.update(access_ink_containment=av,jp2_ink_containment=jv,ink_containment_delta=delta,line_count=lines)
 if delta<-.02: result['reason']='ink containment below accepted threshold'; return result
 result.update(decision='jp2',lossy_origin=False,reason='all predeclared checks passed'); return result
out={}
for p in pages:
 try: r=run(p)
 except Exception as e: r={'id':p['id'],'decision':'webp','lossy_origin':True,'reason':'registration error: '+repr(e),'residual_p95_px':None,'inlier_fraction':0.0,'ink_containment_delta':None}
 out[p['id']]=r; print(p['id'],r,flush=True)
(B/'registration.json').write_text(json.dumps(out,indent=2)+'\n')
