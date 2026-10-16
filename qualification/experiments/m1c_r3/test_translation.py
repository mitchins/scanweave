#!/usr/bin/env python3
"""Independent instrument translation tests; not a proof of weather-wane estimator."""
import json, os, random, hashlib
import numpy as np
from PIL import Image, ImageFilter
from alignment import phase_shift, shift_arr, mse

def asym(h=72,w=72):
    a=np.zeros((h,w),dtype=np.float32)
    a[6:48,7:19]=1; a[36:64,22:58]=1; a[18:34,28:40]=1
    a[10:22,42:52]=1
    return a

def indep_shift(arr,dy,dx):
    # independent interpolation operator (BICUBIC), no bilinear estimator code
    im=Image.fromarray((np.clip(arr,0,1)*255).astype(np.uint8))
    im=im.transform(im.size,Image.Transform.AFFINE,(1,0,dx,0,1,dy),fillcolor=0,resample=Image.BICUBIC)
    return np.asarray(im,dtype=np.float32)/255.0

def make_degraded(arr,tx,ty,seed):
    obs=indep_shift(arr,ty,tx)
    try:
        im=Image.fromarray((obs*255).astype(np.uint8))
        im=im.filter(ImageFilter.GaussianBlur(0.7))
        obs=np.asarray(im,dtype=np.float32)/255.0
    except Exception: pass
    rng=np.random.default_rng(seed)
    obs=obs+rng.normal(0,0.02,obs.shape)
    obs=obs*(1+0.1)
    return np.clip(obs,0,1)

def run_trials(n, noisy=True):
    a=asym()
    trials=[]
    rng=random.Random(hashlib.sha256(b"translation-trials").hexdigest()[:8])
    for i in range(n):
        tx=rng.uniform(-3,3); ty=rng.uniform(-3,3)
        if abs(tx)<1e-3 and abs(ty)<1e-3: tx=0.37; ty=-0.71
        seed=int(hashlib.sha256(f"trial{i}".encode()).hexdigest()[:8],16)
        obs=make_degraded(a,tx,ty,seed) if noisy else indep_shift(a,ty,tx)
        est_x,est_y,err=phase_shift(obs,a)
        correction_x,correction_y = est_x,est_y  # to be applied
        aligned=shift_arr(obs,correction_x,correction_y)
        disp=float(np.hypot(est_x-(-tx), est_y-(-ty)))
        trials.append({
            "truth_tx":tx,"truth_ty":ty,"est_correction_x":est_x,"est_correction_y":est_y,
            "residual_mse":float(mse(aligned,a)),"disp_err":disp,"noisy":noisy
        })
    return trials

# analytical off-grid (noise-free) trials
clean=run_trials(25,noisy=False)
noisy=run_trials(25,noisy=True)
disp_all=[r["disp_err"] for r in clean+noisy]
res_all=[r["residual_mse"] for r in clean+noisy]
max_disp=max(disp_all)
max_res=max(res_all)
bias_x=float(np.mean([r["est_correction_x"]+r["truth_tx"] for r in clean+noisy]))
bias_y=float(np.mean([r["est_correction_y"]+r["truth_ty"] for r in clean+noisy]))
sd=float(np.std([r["disp_err"] for r in clean+noisy]))
report={"clean_max_disp":max(r["disp_err"] for r in clean),"noisy_max_mse":max(r["residual_mse"] for r in noisy),
        "max_disp":max_disp,"max_res":max_res,"bias_x":bias_x,"bias_y":bias_y,"sd_disp":sd,
        "n_total":len(disp_all),"passed":(max_disp<0.6 and max_res<0.04 and abs(bias_x)<0.15 and abs(bias_y)<0.15)}
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work', 'm1c_r3'),exist_ok=True)
json.dump(report,open(os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work', 'm1c_r3'),'instrument_translation_v2.json'),'w'),indent=2)
json.dump({'clean':clean,'noisy':noisy},open(os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work', 'm1c_r3'),'trials_v2.json'),'w'),indent=2)
print("max_disp",max_disp,"max_res",max_res,"bias_x",bias_x,"bias_y",bias_y,"sd",sd)
print("PASS" if report["passed"] else "FAIL")
if not report["passed"]:
    raise SystemExit(1)
