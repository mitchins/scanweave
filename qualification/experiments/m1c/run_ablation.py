#!/usr/bin/env python3
"""M1-C synthetic ablation: A/B/C across observation counts.

Inputs: local font files. Outputs: JSON summary + text table. No sealed corpus.
"""
import json, math, os, random, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "work", "m1c")
FONTS = [
    ("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("DejaVuSerif-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    ("URWGothic-Demi", "/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf"),
    ("P052-Roman", "/usr/share/fonts/opentype/urw-base35/P052-Roman.otf"),
    ("NimbusMonoPS-Regular", "/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Regular.otf"),
    ("IPAGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"),
]
GLYPHS = list("680Oaegi1l") + ["ガ", "パ"]
TARGET_DPI = 600
RN = None
SEED = 20261015
random.seed(SEED); np.random.seed(SEED)

def render_glyph(font, ch, dpi, antialias=True):
    size_pt = 8.0
    px = max(1, int(size_pt * dpi / 72.0))
    f = ImageFont.truetype(font, px)
    # render into temp large
    pad = px * 2
    bbox = f.getbbox(ch)  # left,top,right,bottom (uncertain)
    w = max(1, bbox[2]-bbox[0]) + pad*2
    h = max(1, bbox[3]-bbox[1]) + pad*2
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    x = pad - bbox[0]; y = pad - bbox[1]
    d.text((x, y), ch, font=f, fill=0)
    if not antialias:
        img = img.point(lambda p: 0 if p < 128 else 255)
    arr = 255.0 - np.asarray(img, dtype=np.float32)
    arr = np.clip(arr / 255.0, 0, 1)
    # crop bbox tightly to ink
    rows = arr.max(axis=1); cols = arr.max(axis=0)
    r0,r1 = np.where(rows>0)[0][[0,-1]] if rows.any() else (0,len(rows)-1)
    c0,c1 = np.where(cols>0)[0][[0,-1]] if cols.any() else (0,len(cols)-1)
    arr = arr[r0:r1+1, c0:c1+1]
    return arr, (c0,r0)  # returned relative origin not used


def make_observation(pristine_arr, dpi, scale, translate, blur_px, noise_sd, ink_bias):
    # down/up resize observation at lower DPI
    h, w = pristine_arr.shape
    # render at target observation resolution by scaling
    obs_scale = dpi / float(TARGET_DPI)
    oh = max(1, int(h * obs_scale)); ow = max(1, int(w * obs_scale))
    arr = np.asarray(Image.fromarray((pristine_arr*255).astype(np.uint8)).resize((ow,oh), Image.BILINEAR), dtype=np.float32)/255.0
    # transform registration (?) keep canvas center same after scale
    # blur
    if blur_px > 0:
        im = Image.fromarray((arr*255).astype(np.uint8))
        im = im.filter(ImageFilter.GaussianBlur(blur_px * obs_scale + 0.3))
        arr = np.asarray(im,dtype=np.float32)/255.0
    # noise
    arr = arr + np.random.normal(0, noise_sd, arr.shape).astype(np.float32)
    # ink intensity/bias
    arr = np.clip(arr * (1+ink_bias), 0, 1)
    # translate subpixel via shift upsample
    ty, tx = translate
    # convert translate (in pristine px) to obs px
    txo = tx*obs_scale; tyo=ty*obs_scale
    # resampling translation via roll-ish fractional using scipy not available? use PIL
    arr8 = (arr*255).astype(np.uint8)
    im = Image.fromarray(arr8)
    # apply affine translate
    im = im.transform(im.size, Image.Transform.AFFINE, (1,0,txo,0,1,tyo), fillcolor=0)
    arr = np.asarray(im,dtype=np.float32)/255.0
    # paper/texture
    # threshold-ish antialias not hard
    # upsample back to 600 grid for common fusion
    im = Image.fromarray((arr*255).astype(np.uint8))
    im = im.resize((w,h), Image.BILINEAR)
    obs = np.asarray(im,dtype=np.float32)/255.0
    return obs

def align_to_reference(obs, ref):
    # phase cross-correlation, integer shifts only
    from numpy.fft import fft2, ifft2, fftshift
    F1 = fft2(obs); F2=np.conj(fft2(ref))
    R = F1*F2/(np.abs(F1*F2)+1e-9)
    cc = np.abs(fftshift(ifft2(R))).real
    peak = np.unravel_index(np.argmax(cc), cc.shape)
    shift = (peak[0]-obs.shape[0]//2, peak[1]-obs.shape[1]//2)
    return shift

def fuse(obs_list, method="median"):
    # obs list: arrays shape (h,w) in 0..1 on same grid? In real, differing sizes; we assume same cropped bbox from padded references.
    aligned=[]
    for o in obs_list:
        # align each to first
        aligned.append(o)
    stack=np.stack(aligned,axis=0)
    if method=="median": out=np.median(stack,axis=0)
    elif method=="mean": out=stack.mean(axis=0)
    elif method=="trimmed": 
        q1=np.percentile(stack,25,axis=0); q3=np.percentile(stack,75,axis=0)
        keep=(stack>=q1)&(stack<=q3)
        # fallback keep at least 1
        out=np.where(keep, stack, np.nan).astype(np.float32)
        out=np.where(np.isnan(out), np.median(stack,axis=0), out)
        out=np.nanmedian(out,axis=0)
    return out



def threshold_mask(x, t=0.35):
    return (x>=t).astype(np.uint8)

def boundary_dist(a,b):
    # Manhattan/Euclidean distance from boundaries a to b
    # fallback: compute via morphological dilation not available; implement brute force for small masks
    # Convert mask boundary
    def boundary(m):
        m=m.astype(bool)
        b = np.zeros_like(m)
        # boundary = foreground with background neighbor
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                shifted=np.roll(m, (dy,dx), axis=(0,1))
                b |= (m & ~shifted)
        return b
    ba=boundary(a); bb=boundary(b)
    pts_a=np.argwhere(ba)
    pts_b=np.argwhere(bb)
    if len(pts_a)==0 or len(pts_b)==0:
        return 10.0
    # nearest neighbor distance via KDTree manually? small enough: brute
    # for speed sample
    maxn=400
    if len(pts_a)>maxn: pts_a=pts_a[np.random.choice(len(pts_a),maxn,replace=False)]
    if len(pts_b)>maxn: pts_b=pts_b[np.random.choice(len(pts_b),maxn,replace=False)]
    dmat=np.sqrt(((pts_a[:,None,:]-pts_b[None,:,:])**2).sum(2))
    # symmetric: mean nearest each direction
    da=dmat.min(axis=1).mean()
    db=dmat.min(axis=0).mean()
    return float((da+db)/2.0)

def bootstrap_ci(diffs, n=1000, seed=1):
    rng=np.random.default_rng(seed)
    arr=np.asarray(diffs,dtype=float)
    boot=[]
    for _ in range(n):
        s=rng.choice(arr,size=len(arr),replace=True)
        boot.append(s.mean())
    lo,hi=np.percentile(boot,[2.5,97.5])
    return float(lo),float(hi)

def iou(a,b):
    inter=np.logical_and(a,b).sum(); union=np.logical_or(a,b).sum()
    return float(inter/max(1,union))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(OUT,"m1c_ablation.json"))
    ap.add_argument("--maxsamples", type=int, default=40)
    args=ap.parse_args()
    os.makedirs(os.path.dirname(args.out),exist_ok=True)
    pooled = {nn: {"A":[],"B":[],"Cav":[],"Cmed":[],"Ctrim":[]} for nn in [1,2,4,8,16,32]}
    per_glyph = {}
    false_merges = 0
    test_count=0
    sample_id=0
    for family,font in FONTS:
        for ch in GLYPHS:
            if family=="IPAGothic" and ch not in ["ガ","パ","が","6","8"]:
                # kana-only focus for IPAGothic plus few
                pass
            for si in range(args.maxsamples):
                seed_base = hash((family, ch, si)) % 10**8
                rng = random.Random(seed_base)
                np.random.seed(seed_base % 2**32)
                arr,origin = render_glyph(font, ch, TARGET_DPI, True)
                if arr.size==0 or arr.max()<0.05: 
                    continue
                # pad to common shape not needed; but observations vary shape;
                # Use arr as reference pristine (high dpi)
                H,W = arr.shape
                # arm A uses one observation
                # degradation sets
                Ns=[1,2,4,8,16,32]
                # generate 32 observations
                obs_all=[]
                for j in range(32):
                    dpi = rng.choice([200,300,600])
                    obs_scale = dpi/TARGET_DPI
                    blur = rng.uniform(0.2,1.4)
                    noise = rng.uniform(0.02,0.10)
                    ink = rng.uniform(-0.15,0.15)
                    tx = rng.uniform(-2.0,2.0)
                    ty = rng.uniform(-2.0,2.0)
                    o = make_observation(arr, dpi, None, (tx,ty), blur, noise, ink)
                    obs_all.append(o)
                pristine_mask = (arr>0.2).astype(np.uint8)
                # ed for each N
                for N in Ns:
                    obsN=obs_all[:N]
                    # A: first observation threshold
                    mA=threshold_mask(obsN[0])
                    # align each to itself (same grid nominal); for B medoid choose best IoU after threshold
                    # medoid by minimum average pairwise IoU distance among obs
                    ms=[threshold_mask(o) for o in obsN]
                    best_idx=0; bestr=1e9
                    for i,m in enumerate(ms):
                        rr=0.0
                        for j,om in enumerate(ms):
                            if i==j: continue
                            rr += (1-iou(m,om))
                        if rr<bestr: bestr=rr; best_idx=i
                    bestB=ms[best_idx]
                    mA_id=0
                    # C average/median/trimmed on same grid; register with phase corr to first but same approx
                    avg=fuse(obsN,"mean"); med=fuse(obsN,"median"); trm=fuse(obsN,"trimmed")
                    mCav=threshold_mask(avg); mCmed=threshold_mask(med); mCtrim=threshold_mask(trm)
                    eA=boundary_dist(mA, pristine_mask)
                    eB=boundary_dist(bestB, pristine_mask)
                    eCav=boundary_dist(mCav, pristine_mask)
                    eCmed=boundary_dist(mCmed, pristine_mask)
                    eCtrim=boundary_dist(mCtrim, pristine_mask)
                    pooled[N]["A"].append(eA); pooled[N]["B"].append(eB)
                    pooled[N]["Cav"].append(eCav); pooled[N]["Cmed"].append(eCmed); pooled[N]["Ctrim"].append(eCtrim)
    # summary
    summary={"families":[f[0] for f in FONTS],"glyphs":GLYPHS,"ref_dpi":TARGET_DPI,"results":{}}
    for N in Ns:
        def stat(k): return float(np.median(pooled[N][k]))
        a=stat("A"); b=stat("B")
        summary["results"][str(N)]={k:stat(k) for k in pooled[N]}
        summary["results"][str(N)]["rel_improvement_vs_B_median_pct"]=float(100*(b-stat("Cmed"))/max(1e-9,b))
    # bootstrap improvement for N>=8: Cmed vs B pooled across all (all N together)
    allb=[]; allc=[]
    for N in [8,16,32]:
        allb+=pooled[N]["B"]; allc+=pooled[N]["Cmed"]
    diffs=np.array(allb)-np.array(allc)
    lo,hi=bootstrap_ci(diffs)
    summary["bootstrap_N_ge_8_Cmed_vs_B_median_error_reduction"]={
        "mean_pct":float(100*diffs.mean()/np.mean(allb)),
        "ci95_low_pct":float(100*lo/np.mean(allb)),
        "ci95_high_pct":float(100*hi/np.mean(allb)),
        "n":len(diffs),
    }
    os.makedirs(os.path.dirname(args.out),exist_ok=True)
    with open(args.out,"w") as f: json.dump(summary,f,indent=2)
    # table
    print("N   A        B        Cav      Cmed     Ctrim    relCmed_vs_B%")
    for N in Ns:
        r=summary["results"][str(N)]
        print(f"{N:<3} {r['A']:.4f}  {r['B']:.4f}  {r['Cav']:.4f}  {r['Cmed']:.4f}  {r['Ctrim']:.4f}  {r['rel_improvement_vs_B_median_pct']:+.1f}")
    print("bootstrap:", summary["bootstrap_N_ge_8_Cmed_vs_B_median_error_reduction"])


if __name__=="__main__":
    main()
