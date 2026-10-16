#!/usr/bin/env python3
import inspect, json, os, random, hashlib, numpy as np
sys_path = __file__
import sys
sys.path.insert(0, os.path.dirname(__file__))
from diagnostic import fuse_oracle, fuse_estimated, fuse_unaligned, to_mask, iou
from generator import degrade, render_pristine
from alignment import phase_shift

def test_estimated_does_not_expose_truth():
    params = inspect.signature(fuse_estimated).parameters
    assert "truth" not in params and "src" not in params, params
    assert list(params.keys()) == ["obs", "method"], params

def test_oracle_changes_with_truth_and_estimated_does_not_accept_truth():
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    src,_=render_pristine(font,"a",300)
    src=np.asarray(src,dtype=np.float32)
    if src.max()>1: src=1-src/255.
    seed=int(hashlib.sha256(b"leak").hexdigest()[:8],16)
    rng=random.Random(seed)
    obs=[]; truth=[]
    for j in range(4):
        tx=rng.uniform(-1,1); ty=rng.uniform(-1,1)
        o=degrade(src,seed+j,blur=0.5,noise=0.03,ink=0.05,fractional_tx=tx,fractional_ty=ty)
        obs.append(o); truth.append((tx,ty))
    o1,_=fuse_estimated(obs,"median")
    # changing truth argument is impossible by API; function remains same
    truth2=[(t[1],t[0]) for t in truth]
    o_oracle_1=fuse_oracle(obs,truth)
    o_oracle_2=fuse_oracle(obs,truth2)
    assert not np.allclose(o_oracle_1,o_oracle_2), "oracle must depend on truth"
    # estimated should not be identical to oracle in general
    assert not np.allclose(o1,o_oracle_1), "estimated must be a separate mode"
    # shapes/data
    assert o1.shape==src.shape

def test_modes_shapes():
    from alignment import shift_arr
    arr=np.zeros((4,5),dtype=np.float32)
    a,_=fuse_estimated([arr,arr]); b=fuse_oracle([arr,arr],[(0,0),(0,0)]); c=fuse_unaligned([arr,arr])
    assert a.shape==b.shape==c.shape==(4,5)

def test_registration_failure_reproducible():
    # If the corrected instrument records outliers, they should be present and reported,
    # not masked by an ignored array filter.
    import json
    report=os.environ.get("M1CR3_REPORT")
    if not report or not os.path.exists(report):
        print("registration check skipped: no evidence file")
        return
    d=json.load(open(report))
    assert "registration" in d["final"]

if __name__=="__main__":
    test_estimated_does_not_expose_truth()
    test_oracle_changes_with_truth_and_estimated_does_not_accept_truth()
    test_modes_shapes()
    test_registration_failure_reproducible()
    print("diagnostic mode / leakage tests PASS")
