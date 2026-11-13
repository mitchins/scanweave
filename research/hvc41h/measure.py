#!/usr/bin/env python3
"""Measure JPEG costs, per-glyph ghost proxy and spatial spill against the exact control."""
import hashlib,json,os,pathlib,sys
import numpy as np
from PIL import Image,features
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41h';L=R/'local/hvc41h';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41H_MEASURE')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';g=R/'local/hvc41g/historical-frozen.pdf';source=R/'local/ink33r/renders/historical/01-source.png';prep=json.loads((E/'prepared.json').read_text())
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(g.read_bytes())!='e408daab686fd47f05451627620a79dc8770e5c299654eba4f76bb5454ef7a4b' or sha(source.read_bytes())!=prep['source_png_sha256_before_after']:sys.exit('frozen hash mismatch')
rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];assert len(rows)==38;ms=np.load(L/'native-masks.npz');anys=ms['any'];full=ms['full'];assert anys.shape==(38,1569,1158) and not (full&~anys).any();ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;owners=np.asarray(Image.open(L/'source-owner-labels.png'));src=np.asarray(Image.open(source).convert('RGB'));edit=np.asarray(Image.open(L/'source-owned-edited.png').convert('RGB'));source_changed=np.any(src!=edit,axis=2)
if (source_changed&(owners==0)).any():sys.exit('source edit escaped ownership')
wt=np.array([.2126,.7152,.0722]);img={name:np.asarray(Image.open(L/(name+'.jpg')).convert('RGB')) for name in ('original-39','control','b-pre','b-native')};assert all(x.shape==(1569,1158,3) for x in img.values());blobs={k:(L/(k+'.jpg')).read_bytes() for k in img};lum={k:v@wt for k,v in img.items()};assert blobs['control']==blobs['original-39'];target=anys.any(axis=0);threshold=30.0
per=[];ghost_union={k:np.zeros(target.shape,bool) for k in ('control','b-pre','b-native')};source_ref_ink=0
for i,(r,z) in enumerate(zip(rows,prep['glyphs'])):
 assert r['proposal']==z['proposal'];paper=float(np.array(z['paper_rgb'])@wt);native=anys[i];original_ref=int((ref&(owners==i+1)).sum());source_ref_ink+=original_ref;counts={}
 for key in ('control','b-pre','b-native'):
  gmask=native&(lum[key]<paper-threshold);counts[key]=int(gmask.sum());ghost_union[key]|=gmask
 per.append({'proposal':r['proposal'],'symbol_id':r['symbol_id'],'identity':r['claude_identity'],'source_box':r['source_box'],'paper_rgb':z['paper_rgb'],'paper_luminance':paper,'dark_threshold_luminance':paper-threshold,'source_owned_pixels':z['source_owned_pixels'],'source_reference_ink_pixels':original_ref,'native_any_pixels':z['native_any_overlap_pixels'],'native_fully_contained_pixels':z['native_fully_contained_pixels'],'residual_ghost_proxy_pixels':counts})
# Classify all changed decoded pixels outside the any-overlap native footprint.
def blockcover(mask,side):
 H,W=mask.shape;ph=(-H)%side;pw=(-W)%side;m=np.pad(mask,((0,ph),(0,pw)));groups=m.reshape(m.shape[0]//side,side,m.shape[1]//side,side).any(axis=(1,3));return np.repeat(np.repeat(groups,side,axis=0),side,axis=1)[:H,:W]
b8=blockcover(target,8);b16=blockcover(target,16);contain={}
for name in ('b-pre','b-native'):
 delta=lum[name]-lum['control'];changed=np.any(img[name]!=img['control'],axis=2);outside=changed&~target
 def stat(mask):return {'pixels':int(mask.sum()),'max_abs_delta_luma':float(np.max(np.abs(delta[mask]))) if mask.any() else 0.0}
 contain[name]={'all_changed':stat(changed),'inside_any_overlap_footprints':stat(changed&target),'outside_total':stat(outside),'outside_within_touched_8x8':stat(outside&b8),'outside_beyond_touched_8x8':stat(outside&~b8),'outside_within_touched_16x16_mcu':stat(outside&b16),'outside_beyond_touched_16x16_mcu':stat(outside&~b16)}
 # Cyan=inside, yellow=outside but in touched MCU, red=outside that MCU.
 cmap=np.zeros((*target.shape,3),np.uint8);cmap[changed&target]=[0,220,255];cmap[outside&b16]=[255,200,0];cmap[outside&~b16]=[255,0,0];Image.fromarray(cmap).save(L/f'containment-{name}.png')
# Native full cells cover only source pixels fully owned by their corresponding glyph.
covered=np.zeros(ref.shape,bool);H,W=target.shape;hh,ww=ref.shape
for i in range(38):
 yy,xx=np.nonzero(full[i])
 for y,x in zip(yy,xx):
  y0=int(np.floor(y*hh/H));y1=int(np.ceil((y+1)*hh/H));x0=int(np.floor(x*ww/W));x1=int(np.ceil((x+1)*ww/W));assert np.all(owners[y0:y1,x0:x1]==i+1);covered[y0:y1,x0:x1]=True
native_ref=int((covered&ref).sum());control_bytes=len(blobs['control']);pre_bytes=len(blobs['b-pre']);native_bytes=len(blobs['b-native']);v=json.loads((R/'hvc41g/preflight-build.json').read_text());vector=v['compressed_form_path_bytes']+(v['compressed_patch_and_draw_stream_bytes']-v['compressed_patch_bytes'])+v['structural_overhead_bytes'];baseline=base.stat().st_size
provenance={'source_png_sha256_before_after':sha(source.read_bytes()),'control_matches_embedded_stream':blobs['control']==blobs['original-39'],'decoder':'Pillow '+Image.__version__+' JPEG '+str(features.version_codec('jpg')),'files':{k:{'bytes':len(z),'sha256':sha(z)} for k,z in blobs.items()},'source_dimensions':[1738,2355],'jpeg_dimensions':[1158,1569],'encoder':'#39 jpeg-encoder 0.7.1 Q85 progressive 4:2:0 optimized Huffman, image crate Lanczos3','native_variant_input':'unencoded source-derived Lanczos3 samples, never decoded #39 JPEG'}
economics={'baseline_pdf_bytes':baseline,'original_jpeg_bytes':len(blobs['original-39']),'control_jpeg_bytes':control_bytes,'b_pre_jpeg_bytes':pre_bytes,'b_native_jpeg_bytes':native_bytes,'b_pre_image_savings_bytes':control_bytes-pre_bytes,'b_native_image_savings_bytes':control_bytes-native_bytes,'a3_form_bytes':v['compressed_form_path_bytes'],'a3_draw_bytes':v['compressed_patch_and_draw_stream_bytes']-v['compressed_patch_bytes'],'estimated_structure_bytes':v['structural_overhead_bytes'],'estimated_vector_cost_excluding_patches':vector,'b_pre_predicted_document_bytes':baseline+vector+pre_bytes-control_bytes,'b_native_predicted_document_bytes':baseline+vector+native_bytes-control_bytes,'source_owned_reference_ink_pixels':source_ref_ink,'native_fully_owned_source_reference_ink_pixels':native_ref,'b_pre_savings_per_source_reference_ink_pixel':(control_bytes-pre_bytes)/source_ref_ink,'b_native_savings_per_source_reference_ink_pixel':(control_bytes-native_bytes)/native_ref if native_ref else None,'form_and_overhead_bytes_per_glyph':vector/38,'reference_proxy_total_pixels':int(ref.sum()),'projection_assumption':'constant marginal source-reference ink per glyph, JPEG savings per source-reference ink pixel, and vector bytes per added glyph; does not model differing glyphs, area overhead or JPEG context'}
ghost={'threshold':'Rec.709 decoded pixel luminance < source-supported local paper luminance minus 30','region':'native cells with any overlap of the frozen source ownership masks; counts can include mixed edge cells and neighbouring unowned ink','control':int(ghost_union['control'].sum()),'b_pre':int(ghost_union['b-pre'].sum()),'b_native':int(ghost_union['b-native'].sum()),'glyphs':per}
assert sha(source.read_bytes())==prep['source_png_sha256_before_after'] and not (L/'ocr-invoked').exists();(E/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');(E/'economics.json').write_text(json.dumps(economics,indent=2)+'\n');(E/'ghost-ink.json').write_text(json.dumps(ghost,indent=2)+'\n');(E/'containment.json').write_text(json.dumps(contain,indent=2)+'\n');print(json.dumps({'economics':economics,'ghost_unique':{k:int(v.sum()) for k,v in ghost_union.items()},'containment':contain},indent=2),flush=True)
