"""Source-relative image metrics and decoded-JPEG changes near unowned reference ink."""
import hashlib,json,os,pathlib,sys
import numpy as np
from PIL import Image
from scipy import ndimage as nd
from skimage.metrics import structural_similarity
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41h';L=R/'local/hvc41h';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41H_SOURCE_METRICS')!='1':sys.exit('research switch required')
source=R/'local/ink33r/renders/historical/01-source.png';prep=json.loads((E/'prepared.json').read_text());assert sha(source.read_bytes())==prep['source_png_sha256_before_after'];assert sha((R/'hvc41e/review-decisions.json').read_bytes())=='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';assert sha((R/'local/ink33r/historical.pdf').read_bytes())=='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b'
src=np.asarray(Image.open(source).convert('RGB'));h,w=src.shape[:2];owner=np.asarray(Image.open(L/'source-owner-labels.png'))>0;outside=~nd.binary_dilation(owner,iterations=4);ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;ms=np.load(L/'native-masks.npz');target=ms['any'].any(axis=0);H,W=target.shape;refnative=np.asarray(Image.fromarray(ref).resize((W,H),Image.Resampling.NEAREST))>0;control=np.asarray(Image.open(L/'control.jpg').convert('RGB'));wt=np.array([.2126,.7152,.0722]);lc=control@wt;results=[]
for name in ('control','b-pre','b-native'):
 native=Image.open(L/(name+'.jpg')).convert('RGB');up=np.asarray(native.resize((w,h),Image.Resampling.LANCZOS));score,smap=structural_similarity(src,up,channel_axis=2,data_range=255,full=True);err=np.abs(src.astype(np.int16)-up.astype(np.int16)).mean(axis=2);arr=np.asarray(native);delta=arr@wt-lc;unowned_ref=refnative&~target;bright=unowned_ref&(delta>10);results.append({'variant':name,'whole_page_ssim_to_source':float(score),'ssim_map_mean_outside_four_source_pixels_of_owned':float(smap.mean(axis=2)[outside].mean()),'rgb_mae_outside_four_source_pixels_of_owned':float(err[outside].mean()),'decoded_unowned_reference_proxy_pixels_lightened_over_10_luma':int(bright.sum()),'decoded_unowned_reference_proxy_max_lightening':float(delta[unowned_ref].max()) if unowned_ref.any() else 0.0})
if sha(source.read_bytes())!=prep['source_png_sha256_before_after'] or (L/'ocr-invoked').exists():sys.exit('source/OCR guard failed')
(E/'source-relative.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
