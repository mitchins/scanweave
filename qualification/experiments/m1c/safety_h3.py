#!/usr/bin/env python3
import os, random, json
import numpy as np
from PIL import Image, ImageFont, ImageFilter
import sys
sys.path.insert(0, os.path.dirname(__file__))
from run_ablation import render_glyph, make_observation, iou
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = [("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"), ("/usr/share/fonts/opentype/urw-base35/P052-Roman.otf")]
SEED=20261015; random.seed(SEED); np.random.seed(SEED)
def thresh(x): import numpy as np; return (x>=0.35).astype(np.uint8)
# generate one obs per (font,glyph)
items=[]
for fi,font in enumerate(FONTS):
    for ch in ["6","8","O","0","a"]:
        arr,_=render_glyph(font,ch,600,True)
        for k in range(5):
            o=make_observation(arr,300,None,(0.4,0.4),0.8,0.05,0.0)
            items.append(((fi,ch),thresh(o)))
# cross-similarity (obs threshold)
within=[]; cross=[]
for i,(li,ma) in enumerate(items):
    for j,(lj,mb) in enumerate(items):
        if i>=j: continue
        same = (li[1]==lj[1]) and (li[0]==lj[0])
        # pad masks to union shape
        ha,wa=ma.shape; hb,wb=mb.shape
        H=max(ha,hb); W=max(wa,wb)
        a=np.zeros((H,W),dtype=np.uint8); b=np.zeros((H,W),dtype=np.uint8)
        a[:ha,:wa]=ma; b[:hb,:wb]=mb
        d=float(np.logical_and(a,b).sum()/max(1,np.logical_or(a,b).sum()))
        (within if same else cross).append(d)
t = (np.median(within)+np.median(cross))/2 if within and cross else 0.5
# false merges: negative pair with sim >= t; false splits: positive pair with sim < t
fm = sum(1 for d in cross if d>=t)
fs = sum(1 for d in within if d<t)
print("within median IoU:", round(float(np.median(within)),3), "cross median IoU:", round(float(np.median(cross)),3))
print("threshold:", round(t,3), "false merges:", fm, "false splits:", fs, "total neg:", len(cross), "pos:", len(within))
json.dump({"within_median":float(np.median(within)),"cross_median":float(np.median(cross)),"threshold":float(t),"false_merges":fm,"false_splits":fs,"neg":len(cross),"pos":len(within)}, open(os.path.join(ROOT,"work/m1c","h3_safety.json"),"w"), indent=2)
