#!/usr/bin/env python3
"""Prepare only the frozen owned source pixels and conservative native masks."""
import hashlib,json,os,pathlib,sys
import numpy as np
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41h';L=R/'local/hvc41h';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41H_PREPARE')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';g=R/'local/hvc41g/historical-frozen.pdf';side=R/'local/ink33r/historical.pdf.json';source=R/'local/ink33r/renders/historical/01-source.png'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(g.read_bytes())!='e408daab686fd47f05451627620a79dc8770e5c299654eba4f76bb5454ef7a4b':sys.exit('frozen hash mismatch')
s=json.loads(side.read_text());im=Image.open(source).convert('RGB');w,h=im.size;src=np.asarray(im);meta=s['pages'][0];source_hash=sha(source.read_bytes())
if sha((R.parent/'pdf_packaging/groups/historical-input.pdf').read_bytes())!=s['input_sha256'] or any(sha(x['hocr'].encode())!=x['hocr_sha256'] for x in s['pages']) or [w,h]!=[meta['raster_width'],meta['raster_height']] or sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+src.tobytes())!=meta['pixel_sha256'] or sha(src.tobytes())!=meta['native_source']['decoded_rgb_sha256']:sys.exit('source or OCR mismatch')
rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];assert len(rows)==38;pre={x['proposal']:x for x in json.loads((R/'hvc41g/qualification-patches.json').read_text())['glyphs']};reference=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;lum=src@np.array([.2126,.7152,.0722]);dump=json.loads((R/'local/hvc41/trial2/historical/p000001.json').read_text());info=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text());labels,_=nd.label(abs(lum-np.array(dump['paper'])@np.array([.2126,.7152,.0722]))>60,np.ones((3,3),bool));ids=[i for art in info['artwork'] for i in art['component_ids']];lut=np.zeros(int(labels.max())+1,bool);lut[ids]=True;art=lut[labels];del labels
sys.path.insert(0,str(R/'ink33r'));from prepare import chars_from_hocr
ocrboxes=np.zeros((h,w),bool)
for line in chars_from_hocr(s['pages'][0]['hocr']):
 for word in line['words']:
  for c in word['chars']:
   a,b,cx,d=map(int,c['box']);ocrboxes[max(0,b):min(h,d),max(0,a):min(w,cx)]=True
owners=np.zeros((h,w),np.uint8);masks=[]
for i,r in enumerate(rows,1):
 a,b,c,d=r['reference_box'];spec=r['masks']['owner'];p=pathlib.Path(spec['path']);assert sha(p.read_bytes())==spec['sha256'];m=np.asarray(Image.open(p).convert('L'))>0;ps=r['masks']['patch'];pp=pathlib.Path(ps['path']);assert sha(pp.read_bytes())==ps['sha256'];patch=np.asarray(Image.open(pp).convert('L'))>0;assert np.array_equal(m,patch) and not (owners[b:d,a:c][m]>0).any() and pre[r['proposal']]['patch_outside_owned']==0 and pre[r['proposal']]['foreign_other_ocr_pixels']==0 and pre[r['proposal']]['foreign_artwork_pixels']==0;owners[b:d,a:c][m]=i;masks.append(m)
modified=src.copy();measure=[];nw,nh=1158,1569;native_any=np.zeros((len(rows),nh,nw),bool);native_full=np.zeros((len(rows),nh,nw),bool)
for i,(r,own) in enumerate(zip(rows,masks),1):
 a,b,c,d=r['reference_box'];x0=max(0,a-16);x1=min(w,c+16);y0=max(0,b-16);y1=min(h,d+16);local_owner=owners[y0:y1,x0:x1]==i;local_lum=lum[y0:y1,x0:x1];ring=nd.binary_dilation(local_owner,iterations=12)&~nd.binary_dilation(local_owner,iterations=1)&~reference[y0:y1,x0:x1]&~art[y0:y1,x0:x1]&~ocrboxes[y0:y1,x0:x1]&(owners[y0:y1,x0:x1]==0);vals=local_lum[ring]
 if len(vals)<8:sys.exit('insufficient independently supported source paper for '+str(r['proposal']))
 ring &= local_lum>=np.percentile(vals,50);paper=np.median(src[y0:y1,x0:x1][ring],axis=0).astype(np.uint8);modified[b:d,a:c][own]=paper
 # A native cell maps to every source pixel its geometric cell intersects.
 # Any-overlap is used for containment/ghost accounting. Full-containment is
 # the strictly conservative B-native edit mask; no outside source owner is used.
 nx0=max(0,int(np.floor(a*nw/w)));nx1=min(nw,int(np.ceil(c*nw/w)));ny0=max(0,int(np.floor(b*nh/h)));ny1=min(nh,int(np.ceil(d*nh/h)))
 for ny in range(ny0,ny1):
  sy0=int(np.floor(ny*h/nh));sy1=int(np.ceil((ny+1)*h/nh))
  for nx in range(nx0,nx1):
   sx0=int(np.floor(nx*w/nw));sx1=int(np.ceil((nx+1)*w/nw));v=owners[sy0:sy1,sx0:sx1];native_any[i-1,ny,nx]=np.any(v==i);native_full[i-1,ny,nx]=np.all(v==i)
 measure.append({'proposal':r['proposal'],'symbol':r['symbol_id'],'source_owned_pixels':int(own.sum()),'paper_rgb':paper.tolist(),'paper_ring_pixels':int(ring.sum()),'native_any_overlap_pixels':int(native_any[i-1].sum()),'native_fully_contained_pixels':int(native_full[i-1].sum()),'frozen_foreign_ocr_pixels':r['foreign_other_ocr_pixels'],'frozen_foreign_artwork_pixels':r['foreign_artwork_pixels']})
changed=np.any(modified!=src,axis=2)
if np.any(changed&(owners==0)) or sha(source.read_bytes())!=source_hash:sys.exit('ownership or source identity violation')
Image.fromarray(modified).save(L/'source-owned-edited.png');Image.fromarray(owners).save(L/'source-owner-labels.png');np.savez_compressed(L/'native-masks.npz',any=native_any,full=native_full);(E/'prepared.json').write_text(json.dumps({'source_png_sha256_before_after':source_hash,'source_rgb_sha256':sha(src.tobytes()),'edited_source_sha256':sha(modified.tobytes()),'source_owned_pixels':int((owners>0).sum()),'source_changed_pixels':int(changed.sum()),'source_changed_outside_ownership':int((changed&(owners==0)).sum()),'native_any_union_pixels':int(native_any.any(axis=0).sum()),'native_full_union_pixels':int(native_full.any(axis=0).sum()),'native_mapping':'any = any source pixel intersecting the native geometric cell; full = all intersecting source pixels are owned by this same glyph','source_paper_method':'median of upper-luminance half of 12px source annulus, excluding source text-ink proxy, all OCR char boxes, artwork and every owned footprint','glyphs':measure},indent=2)+'\n');print('prepared',len(rows),'source owned',int((owners>0).sum()),'native full',int(native_full.any(axis=0).sum()),flush=True)
