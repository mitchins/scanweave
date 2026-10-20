"""Fixed-source pixel accounting; rectangles are crops, never erasure masks."""
from pathlib import Path
import json,hashlib,collections,sys
import numpy as np,pikepdf
B=Path(__file__).resolve().parent;R=B.parents[1]
sourcepdf=R/'qualification/pdf_packaging/real/input/history-02.pdf'
def samples(path):
 q=pikepdf.open(path);ims=[o for o in q.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name.Image];assert len(ims)==1
 im=ims[0];return np.asarray(pikepdf.PdfImage(im).as_pil_image().convert('RGB')),{'image_resources':len(ims),'raster_bytes':len(im.read_raw_bytes()),'font_bytes':sum(len(o.FontFile2.read_raw_bytes()) for o in q.objects if isinstance(o,pikepdf.Dictionary) and '/FontFile2' in o),'pdf_bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
source,_=samples(sourcepdf);h,w=source.shape[:2];gray=np.round(source@np.array([.2126,.7152,.0722])).astype(np.uint8)
T=128;nx=(w+T-1)//T;ny=(h+T-1)//T;grid=np.zeros((ny,nx))
for y in range(ny):
 for x in range(nx):
  v=np.sort(gray[y*T:min(h,(y+1)*T),x*T:min(w,(x+1)*T)].ravel());grid[y,x]=v[(len(v)*90+99)//100-1]
gx=np.clip((np.arange(w)+.5)/T-.5,0,nx-1);gy=np.clip((np.arange(h)+.5)/T-.5,0,ny-1);xx=gx.astype(int);yy=gy.astype(int);fx=gx-xx;fy=gy-yy
paper=(grid[yy[:,None],xx]*(1-fx)+grid[yy[:,None],np.minimum(xx+1,nx-1)]*fx)*(1-fy[:,None])+(grid[np.minimum(yy+1,ny-1)[:,None],xx]*(1-fx)+grid[np.minimum(yy+1,ny-1)[:,None],np.minimum(xx+1,nx-1)]*fx)*fy[:,None]
foreground=paper-gray>60

def dilate(m):
 p=np.pad(m,1);return np.logical_or.reduce([p[y:y+h,x:x+w] for y in range(3) for x in range(3)])
def core_mask(o):
 m=np.zeros((h,w),bool);idx=np.array(o['ink']);ys=idx//o['width']+int(o['bbox'][1]);xs=idx%o['width']+int(o['bbox'][0]);m[ys,xs]=True;return m
regions=json.loads((B/'regions.json').read_text());rows=[];per=[];
for arm,base in [('control',B/'control.pdf'),('a',B/'a.pdf'),('b',B/'b-active.pdf')]:
 if not base.exists():continue
 log=base.with_suffix('.log');records=[json.loads(s.split(' ',1)[1]) for s in log.read_text().splitlines() if s.startswith('FRINGE_SOURCE_AUDIT ')];assert len(records)==1;audit=records[0];(B/(arm+'-ownership.json')).write_text(json.dumps(audit,indent=2))
 assert int(foreground.sum())==audit['foreground_pixels']==495223
 owners={o['id']:o for o in audit['owners']};union=np.zeros((h,w),bool)
 for o in owners.values():union|=core_mask(o)
 assert not (union&~foreground).any();protected=foreground&~union;allowed=dilate(union)
 raster,res=samples(base);assert raster.shape==source.shape
 changed=np.any(raster!=source,axis=2);res.update(arm=arm,actual_changed_core_pixels=int((changed&union).sum()),actual_changed_fringe_pixels=int((changed&~union).sum()),outside_owned_1px_footprint_changed=int((changed&~allowed).sum()),protected_foreground_changed=int((changed&protected).sum()),mask_core_pixels=int(union.sum()))
 rastergray=raster@np.array([.2126,.7152,.0722])
 for entry in regions:
  id=entry['owner']['symbol_id'];o=owners.get(id)
  if o is None:per.append({'arm':arm,'id':id,'accepted':False});continue
  core=core_mask(o);ring=dilate(core)&~core&~protected&~union
  deficit=np.maximum(0,paper-rastergray)[ring];before=np.maximum(0,paper-(source@np.array([.2126,.7152,.0722])))[ring]
  per.append({'arm':arm,'id':id,'text':entry['observation']['text_hypothesis'],'bbox':o['bbox'],'accepted':True,'independent_halo':o['independent_halo'],'local_paper':o['local_paper'],'core_pixels':int(core.sum()),'actual_changed_core_pixels':int((changed&core).sum()),'eligible_fringe_pixels':int(ring.sum()),'actual_changed_fringe_pixels':int((changed&ring).sum()),'residual_ring_contrast_mean':float(deficit.mean()),'source_ring_contrast_mean':float(before.mean()),'residual_ring_contrast_p90':float(np.quantile(deficit,.9))})
 report=json.loads(Path(str(base)+'.json').read_text())['conversion'];pr=report['page_reports'][0];res.update(reported_core=pr['raster_ink_pixels_suppressed'],reported_fringe=pr['antialias_fringe_pixels_suppressed'],visible_records=sum(o['owner'].startswith('visible') for o in pr['occurrences']),timings=report['stage_timings']);rows.append(res)
(B/'measurements.json').write_text(json.dumps({'documents':rows,'fixed_regions':per,'note':'Ring contrast includes genuine paper variation. Outside-footprint zero is necessary, not proof that every changed fringe sample is harmless.'},indent=2));print(rows)
