"""Recompute source-supported paper-ring statistics with composed neighbours."""
import pathlib,json,sys,hashlib
import numpy as np
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';side=json.loads((R/'local/ink33r/historical.pdf.json').read_text());source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));h,w=source.shape[:2];wt=np.array([.2126,.7152,.0722]);lum=source.astype(float)@wt;ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;rows=[r for r in json.loads((E/'review-decisions.json').read_text()) if r['decision']=='accept'];pre=json.loads((R/'hvc41d/p1-preflight-ledger.json').read_text());info=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text());dump=json.loads((R/'local/hvc41/trial2/historical/p000001.json').read_text());labels,_=nd.label(abs(lum-np.array(dump['paper'])@wt)>60,np.ones((3,3),bool));ids=[i for art in info['artwork'] for i in art['component_ids']];lookup=np.zeros(int(labels.max())+1,bool);lookup[ids]=True;artwork=lookup[labels];sys.path.insert(0,str(R/'ink33r'));from prepare import chars_from_hocr
words=[word for line in chars_from_hocr(side['pages'][0]['hocr']) for word in line['words']];chars=[(wi,ci,c['box']) for wi,word in enumerate(words) for ci,c in enumerate(word['chars'])];full=[];allpatch=np.zeros((h,w),bool);allvector=np.zeros((h,w),bool)
for r in rows:
 a,b,c,d=r['reference_box'];m={}
 for k in ('owner','patch','vector'):
  m[k]=np.zeros((h,w),bool);m[k][b:d,a:c]=np.asarray(Image.open(r['masks'][k]['path']).convert('L'))>0
 allpatch|=m['patch'];allvector|=m['vector'];full.append((r,m))
result=[]
for r,m in full:
 z=pre[r['proposal']];wi=r['word_index'];ci=int(r['symbol_id'].split('s')[-1]);other=np.zeros((h,w),bool)
 for j,k,(a,b,c,d) in chars:
  if (j,k)!=(wi,ci):other[max(0,b):min(h,d),max(0,a):min(w,c)]=True
 patch=m['patch'];owner=m['owner'];ring=nd.binary_dilation(patch,structure=np.ones((3,3),bool))&~patch&~owner&~other&~artwork&~ref&(lum>=z['admission']['paper_luma']-30);yy,xx=np.nonzero(patch);near=np.zeros((h,w),bool);near[max(0,yy.min()-2):min(h,yy.max()+3),max(0,xx.min()-2):min(w,xx.max()+3)]=True;ring &= near
 ring_single=ring&~m['vector'];ring_comp=ring&~allvector&~allpatch;paper=float(np.array(r['paper_fill_rgb'])@wt)
 def stats(mask):
  a=np.abs(lum[mask]-paper);return {'count':int(a.size),'mean':float(a.mean()) if a.size else None,'max':float(a.max()) if a.size else None}
 stats0=stats(ring);stats1=stats(ring_single);stats2=stats(ring_comp);changed=not np.array_equal(ring_single,ring_comp);result.append({'proposal':r['proposal'],'phase1_recomputed':stats0,'phase1_recorded_count':r['halo_ring_pixels'],'phase1_recorded_mean':r['halo_mean_abs_delta_luma'],'phase1_recorded_max':r['halo_max_abs_delta_luma'],'single_excluding_vector':stats1,'composed_excluding_all_patches_and_vectors':stats2,'ring_changed_by_neighbours':changed,'pixels_changed_by_neighbours':int((ring_single&~ring_comp).sum())})
(E/'halo-composition.json').write_text(json.dumps(result,indent=2)+'\n');print('neighbour ring changes',[(x['proposal'],x['pixels_changed_by_neighbours']) for x in result if x['ring_changed_by_neighbours']]);print('phase1 ring mismatches',[x['proposal'] for x in result if x['phase1_recomputed']['count']!=x['phase1_recorded_count']])
