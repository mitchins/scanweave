#!/usr/bin/env python3
import os, random, json, hashlib, numpy as np
from alignment import shift_arr, phase_shift, mse
import generator as G
from PIL import Image, ImageFont

ROOT="/data/coding/scanweave"; OUT=os.path.join(ROOT,"work","m1c_r3","diag")
os.makedirs(OUT,exist_ok=True)
FONTS=[
 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
 "/usr/share/fonts/opentype/urw-base35/P052-Roman.otf",
 "/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf",
]
GLYPHS=["a","g","e"]
N=8; REF=300; SEED_BASE=hashlib.sha256(b"diag-v1").hexdigest()[:8]
random.seed(int(SEED_BASE,16)); np.random.seed(int(SEED_BASE,16)%2**32)

def render_pristine_f(font,ch,dpi):
    src,info=G.render_pristine(font,ch,dpi)
    # tight to bbox done already
    return src

def nearest_boundary_dist(a,b):
    # Euclidean distance between boundaries, sampling
    def bds(m):
        m=m.astype(bool)
        b=np.zeros_like(m)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                s=np.roll(m,(dy,dx),axis=(0,1))
                b |= (m & ~s)
        pts=np.argwhere(b)
        return pts
    pa=bds(a); pb=bds(b)
    if len(pa)==0 or len(pb)==0: return 10.0
    if len(pa)>500: pa=pa[np.random.choice(len(pa),500,replace=False)]
    if len(pb)>500: pb=pb[np.random.choice(len(pb),500,replace=False)]
    d=np.sqrt(((pa[:,None,:]-pb[None,:,:])**2).sum(2))
    return float((d.min(axis=1).mean()+d.min(axis=0).mean())/2)

def iou(a,b):
    return float(np.logical_and(a,b).sum()/max(1,np.logical_or(a,b).sum()))

allres=[]
for fi,f in enumerate(FONTS):
    for ch in GLYPHS:
        src,_=G.render_pristine(f,ch,REF)
        # crop
        # generate obs
        obs=[]; truth=[]; 
        for j in range(N):
            seed=G.stable_seed(f"{f}:{ch}:{j}:diag")
            # phase tx,ty in fractional obs pixels
            rng=random.Random(seed)
            tx=rng.uniform(-1.2,1.2); ty=rng.uniform(-1.2,1.2)
            blur=rng.uniform(0.3,0.9); noise=rng.uniform(0.02,0.08)
            ink=rng.uniform(-0.1,0.1)
            degraded=G.degrade(src,seed,blur=noise and blur, noise=noise, ink=ink, fractional_tx=tx, fractional_ty=ty)
            # Note: degrade uses blur placeholder variable; set properly:
            degraded=G.degrade(src,seed,blur=blur,noise=noise,ink=ink,fractional_tx=tx,fractional_ty=ty)
            obs.append(degraded); truth.append((tx,ty))
            # save obs
            im=Image.fromarray((degraded*255).astype(np.uint8))
            im.save(os.path.join(OUT,f"f{fi}_{ch}_obs_{j}.png"))
        # arms
        single=obs[0]
        # observed medoid (pairwise MSE)
        mats=[(o) for o in obs]
        medial_mse=sum([])
        # medoid selection
        best=None;bestscore=1e9
        for i,o in enumerate(obs):
            r=0.0
            for j,oo in enumerate(obs):
                if i==j: continue
                r+= (1-iou((o>=0.35).astype(np.uint8),(oo>=0.35).astype(np.uint8)))
            if r<bestscore: bestscore=r; best=i
        medoid=obs[best]
        def fuse(xs, method="median", use_shifts=None):
            aligned=xs
            if use_shifts=="true":
                aligned=[shift_arr(x,-tx,-ty) for x,txty in zip(xs,truth)]  # obs -> pristine correction? stored truth translation to deg to image; correction negative
                # truth above is applied translation (obs shifted +tx); correction -tx
            if use_shifts=="est":
                al=[]
                for x in xs:
                    sx,sy,err=phase_shift(x, src)
                    al.append(shift_arr(x,sx,sy))
                aligned=al
            if method=="mean": out=np.mean(aligned,axis=0)
            else: out=np.median(aligned,axis=0)
            return out
        # Note: threshold semantics stored separately
        def to_mask(x):
            return (x>=0.35).astype(np.uint8)
        # primitives
        single_m=to_mask(single)
        med_m=to_mask(medoid)
        noalign_m=to_mask(fuse(obs,"median",None))
        oracle_m=to_mask(fuse(obs,"median","true"))
        est_m=to_mask(fuse(obs,"median","est"))
        results={
         "font":os.path.basename(f),
         "glyph":ch,
         "single":{"iou":iou(single_m,src>=0.5),"boundary":nearest_boundary_dist(single_m, (src>=0.5).astype(np.uint8))},
         "medoid":{"iou":iou(med_m,src>=0.5),"boundary":nearest_boundary_dist(med_m,(src>=0.5).astype(np.uint8))},
         "noalign":{"iou":iou(noalign_m,src>=0.5),"boundary":nearest_boundary_dist(noalign_m,(src>=0.5).astype(np.uint8))},
         "oracle":{"iou":iou(oracle_m,src>=0.5),"boundary":nearest_boundary_dist(oracle_m,(src>=0.5).astype(np.uint8))},
         "estimated":{"iou":iou(est_m,src>=0.5),"boundary":nearest_boundary_dist(est_m,(src>=0.5).astype(np.uint8))},
        }
        allres.append(results)
        print(f"{os.path.basename(f)} / {ch}: oracle boundary {results['oracle']['boundary']:.3f} est {results['estimated']['boundary']:.3f} noalign {results['noalign']['boundary']:.3f} single {results['single']['boundary']:.3f}")
json.dump({"groups":allres}, open(os.path.join(OUT,"diagnostic.json"),'w'), indent=2)
# summary
print("\nMEDIAN BOUNDARY ERROR ACROSS ALL GROUPS:")
for k in ["single","medoid","noalign","oracle","estimated"]:
    b=np.median([r[k]["boundary"] for r in allres])
    print(f"  {k:10s} boundary={b:.4f}")
