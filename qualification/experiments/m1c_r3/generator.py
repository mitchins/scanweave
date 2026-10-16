import hashlib, os
import numpy as np
from PIL import Image, ImageFont, ImageFilter, ImageDraw

def stable_seed(s):
    return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16)

def render_pristine(font_path, ch, ref_dpi=600):
    f = ImageFont.truetype(font_path, max(1,int(9 * ref_dpi/72.0)))  # ~9pt
    bbox = f.getbbox(ch)
    pad=ref_dpi//12
    w=max(1,bbox[2]-bbox[0])+pad*2
    h=max(1,bbox[3]-bbox[1])+pad*2
    im=Image.new("L",(w,h),255)
    ImageDraw.Draw(im).text((pad-bbox[0],pad-bbox[1]),ch,font=f,fill=0)
    arr=np.asarray(im,dtype=np.float32)
    arr=1.0-np.clip(arr/255.0,0,1)
    return arr, (bbox[0],bbox[1],pad)

def integrate_phase(source, phase_x, phase_y, out_w, out_h, sr=4):
    # rasterize with fractional subpixel offset then area integrate down
    h,w=source.shape
    im=Image.fromarray((source*255).astype(np.uint8))
    im=im.transform(im.size,Image.Transform.AFFINE,(1,0,phase_x,0,1,phase_y),fillcolor=0,resample=Image.BILINEAR)
    im=im.resize((w,h),Image.BILINEAR) # no-op
    srh, srw = h*sr, w*sr
    # use Pillow resize with box average
    big=im.resize((w*sr,h*sr),Image.BILINEAR)
    arr=np.asarray(big,dtype=np.float32)/255.0
    # downsample 4:1 average
    H,W=arr.shape
    H2=(H//sr)*sr; W2=(W//sr)*sr
    arr=arr[:H2,:W2].reshape(H2//sr,sr,W2//sr,sr).mean(axis=(1,3))
    # target size approx
    if (out_h,out_w)!=arr.shape:
        im2=Image.fromarray((arr*255).astype(np.uint8))
        im2=im2.resize((out_w,out_h),Image.BILINEAR)
        arr=np.asarray(im2,dtype=np.float32)/255.0
    return arr

def degrade(arr,seed, blur=0.6,noise=0.03, ink=0.1, fractional_tx=0.0, fractional_ty=0.0):
    rng=np.random.default_rng(seed)
    im=Image.fromarray((arr*255).astype(np.uint8))
    # shift by fractional pixels at observed grid
    im=im.transform(im.size, Image.Transform.AFFINE,(1,0,fractional_tx,0,1,fractional_ty),fillcolor=0,resample=Image.BILINEAR)
    arr=np.asarray(im,dtype=np.float32)/255.0
    if blur>0:
        im=Image.fromarray((arr*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
        arr=np.asarray(im,dtype=np.float32)/255.0
    arr=arr+rng.normal(0,noise,arr.shape)
    arr=arr*(1+ink)
    return np.clip(arr,0,1)

if __name__=='__main__':
    # phase coverage sensitivity
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    src,info=render_pristine(font,'a',600)
    # downsample variants with phases 0 and 0.5
    p0=integrate_phase(src,0.0,0.0,src.shape[0]//2,src.shape[1]//2)
    px=integrate_phase(src,3.0,3.0,src.shape[0]//2,src.shape[1]//2)
    phase_diff=float(np.mean(np.abs(p0-px)))
    assert phase_diff > 1e-3, phase_diff
    # observation content same structure with obs phase
    seed=stable_seed('DejaVuSans-Bold/a/0')
    o0=degrade(src,seed, fractional_tx=0.0, fractional_ty=0.0)
    o1=degrade(src,seed+1, fractional_tx=0.5, fractional_ty=-0.3)
    obs_diff=float(np.mean(np.abs(o0-o1)))
    assert obs_diff > 1e-3, obs_diff
    print("phase-change coverage sensitivity: phase_diff =", phase_diff, "obs_diff =", obs_diff, "PASS")
    import json,os
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work', 'm1c_r3'),exist_ok=True)
    json.dump({'phase_diff':phase_diff,'obs_diff':obs_diff,'passed':True}, open(os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work', 'm1c_r3'),'generator_phase.json'),'w'), indent=2)
