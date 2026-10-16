#!/usr/bin/env python3
"""M1-C-R3 discriminating diagnostic — A-E arms, no ground-truth leakage in estimated arm."""
import argparse, hashlib, json, os, random, sys
import numpy as np
from PIL import Image
from alignment import phase_shift, shift_arr, mse
import generator as G

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/opentype/urw-base35/P052-Roman.otf",
    "/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf",
]
GLYPHS = ["a", "g", "8", "0", "6", "が", "パ", "4"]


def font_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_obs(font, ch, seed):
    src, _ = G.render_pristine(font, ch, 300)
    src = np.asarray(src, dtype=np.float32)
    if src.ndim == 3:
        src = src[:, :, 0]
    src = np.clip(1.0 - src / 255.0, 0, 1) if src.max() > 1 else src
    rng = random.Random(seed)
    tx, ty = (rng.uniform(-1.25, 1.25), rng.uniform(-1.25, 1.25))
    blur = rng.uniform(0.35, 0.85)
    noise = rng.uniform(0.02, 0.085)
    ink = rng.uniform(-0.09, 0.09)
    degraded = G.degrade(src, seed, blur=blur, noise=noise, ink=ink, fractional_tx=tx, fractional_ty=ty)
    return src, np.asarray(degraded, dtype=np.float32), (float(tx), float(ty)), {"tx": tx, "ty": ty, "blur": blur, "noise": noise, "ink": ink, "seed": seed}


def to_mask(x, thr=0.35):
    return (np.asarray(x) >= thr).astype(np.uint8)


def boundary_dist(a, b):
    a = np.asarray(a).astype(bool); b = np.asarray(b).astype(bool)
    def bd(m):
        out = np.zeros_like(m)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                s = np.roll(m, (dy, dx), axis=(0, 1))
                out |= (m & ~s)
        return out
    pa, pb = np.argwhere(bd(a)), np.argwhere(bd(b))
    if len(pa) == 0 or len(pb) == 0:
        return 10.0
    if len(pa) > 250:
        pa = pa[np.random.choice(len(pa), 250, replace=False)]
    if len(pb) > 250:
        pb = pb[np.random.choice(len(pb), 250, replace=False)]
    d = np.sqrt(((pa[:, None, :] - pb[None, :, :]) ** 2).sum(2))
    return float((d.min(axis=1).mean() + d.min(axis=0).mean()) / 2.0)


def iou(a, b):
    a = np.asarray(a).astype(bool); b = np.asarray(b).astype(bool)
    return float(np.logical_and(a, b).sum() / max(1, np.logical_or(a, b).sum()))


def fuse_unaligned(obs, method="median"):
    return np.median(obs, axis=0) if method == "median" else np.mean(obs, axis=0)


def fuse_oracle(obs, truth, method="median"):
    # Ground truth only arm.
    aligned = [shift_arr(o, -tx, -ty) for o, (tx, ty) in zip(obs, truth)]
    return np.median(aligned, axis=0) if method == "median" else np.mean(aligned, axis=0)


def fuse_estimated(obs, method="median"):
    # Production-realistic: no source, no truth; register to the first observation.
    aligned = []
    reference = obs[0]
    relative = [(0.0, 0.0)]
    for i, o in enumerate(obs):
        if i == 0:
            aligned.append(o.copy())
        else:
            sx, sy, _ = phase_shift(o, reference)
            aligned.append(shift_arr(o, sx, sy))
            relative.append((sx, sy))
    fused = np.median(aligned, axis=0) if method == "median" else np.mean(aligned, axis=0)
    return fused, relative


def medoid_selection(obs):
    best, score = 0, float("inf")
    for i in range(len(obs)):
        dist = 0.0
        for j in range(len(obs)):
            if i == j:
                continue
            dist += 1.0 - iou(to_mask(obs[i]), to_mask(obs[j]))
        if dist < score:
            score = dist
            best = i
    return best


def write_image(path, arr, mask=False):
    arr = arr if arr.ndim == 2 else np.asarray(arr)[:, :, 0]
    u8 = (np.clip(arr, 0, 1) * 255).astype(np.uint8) if not mask else (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(u8).save(path)


def build_observation_set(font, ch, n, seed):
    rngseed = hashlib.sha256(f"{font}:{ch}:{seed}".encode()).hexdigest()[:16]
    base_seed = int(rngseed, 16)
    random.seed(base_seed)
    np.random.seed(base_seed % (2 ** 32))
    src, obsset, truths, metas = [], [], [], []
    while len(obsset) < n:
        seed_i = hashlib.sha256(f"{font}:{ch}:{len(obsset)}:{seed}".encode()).hexdigest()[:12]
        seed_i = int(seed_i, 16)
        src_i, obs_i, truth_i, meta_i = make_obs(font, ch, seed_i)
        if len(obsset) == 0:
            src = src_i
        obsset.append(obs_i)
        truths.append(truth_i)
        metas.append(meta_i)
    return src, obsset, truths, metas


def evaluate(src_mask, pred_mask, pred_img):
    return {
        "iou": iou(pred_mask, src_mask),
        "boundary": nearest_boundary_dist(pred_mask, src_mask),
        "mae_independent": float(np.mean(np.abs(pred_img - src_mask.astype(np.float32)))),
    }


def run(font, ch, n, outdir, tag):
    src, obs, truths, metas = build_observation_set(font, ch, n, tag)
    src_mask = (src >= 0.5).astype(np.uint8)
    # non-leaking estimated arm
    est_fused, est_relative = fuse_estimated(obs, "median")
    # arms expressed in common source frame:
    single = obs[0].copy(); t0 = truths[0]
    single_src = shift_arr(single, -t0[0], -t0[1])
    mid = medoid_selection(obs)
    med_m = obs[mid].copy(); tm = truths[mid]
    med_src = shift_arr(med_m, -tm[0], -tm[1])
    # unaligned, place at centroid of true shifts for common coordinates
    mean_tx = float(np.mean([t[0] for t in truths])); mean_ty = float(np.mean([t[1] for t in truths]))
    unaligned_src = shift_arr(fuse_unaligned(obs), -mean_tx, -mean_ty)
    # oracle and estimated
    oracle_fused = fuse_oracle(obs, truths)
    oracle_src = oracle_fused.copy()
    # oracle ALREADY placed by true shifts per observation
    est_fused_src = shift_arr(est_fused, -truths[0][0], -truths[0][1])
    # metrics
    masks = {
        "A_single": (to_mask(single_src), single_src),
        "B_medoid": (to_mask(med_src), med_src),
        "C_unaligned": (to_mask(unaligned_src), unaligned_src),
        "D_oracle": (to_mask(oracle_src), oracle_src),
        "E_estimated": (to_mask(est_fused_src), est_fused_src),
    }
    out = {"n": n, "truths": truths, "metas": metas}
    for k, (m, img) in masks.items():
        out[k] = {"mask": m, "img": img}
        out[k]["metrics"] = evaluate(src_mask, m, img)
    # registration errors
    errs = []
    for o, (tx, ty) in zip(obs, truths):
        # independent estimated shifts relative to first
        # already calculated partially; store shifted
        errs.append({"truth": [tx, ty], "truth_norm": float(np.hypot(tx, ty))})
    # estimate to first observed:
    for i in range(1, len(obs)):
        sx, sy, err = phase_shift(obs[i], obs[0])
        tdiff_x = sx - (truths[i][0] - truths[0][0])
        tdiff_y = sy - (truths[i][1] - truths[0][1])
        errs[i]["est_rel"] = [float(sx), float(sy)]
        errs[i]["disp_err"] = float(np.hypot(tdiff_x, tdiff_y))
    if len(errs[0]) == 2:
        errs[0]["est_rel"] = [0.0, 0.0]
        errs[0]["disp_err"] = 0.0
    out["registration"] = errs
    # save images
    tagdir = os.path.join(outdir, f"{os.path.basename(font)}_{ch}_N{n}_{tag}")
    os.makedirs(tagdir, exist_ok=True)
    write_image(os.path.join(tagdir, "source.png"), src_mask, mask=True)
    for k, (m, img) in masks.items():
        write_image(os.path.join(tagdir, f"{k}_mask.png"), m, mask=True)
        write_image(os.path.join(tagdir, f"{k}_gray.png"), img)
    for j, o in enumerate(obs):
        write_image(os.path.join(tagdir, f"obs_{j}.png"), o)
    np.save(os.path.join(tagdir, "source.npy"), src)
    np.save(os.path.join(tagdir, "truths.npy"), np.asarray(truths))
    # serializable
    serial = {key: {"metrics": masks[key][0] and out[key]["metrics"]} for key in masks}
    return serial, os.path.basename(tagdir)


def run(font, ch, n, outdir, tag):
    src, obs, truths, metas = build_observation_set(font, ch, n, tag)
    src_mask = (src>=0.5).astype(np.uint8)
    single = obs[0].copy(); t0 = truths[0]
    single_src = shift_arr(single, -t0[0], -t0[1])
    med_idx = medoid_selection(obs)
    tm = truths[med_idx]
    med_src = shift_arr(obs[med_idx].copy(), -tm[0], -tm[1])
    mean_tx = float(np.mean([t[0] for t in truths]))
    mean_ty = float(np.mean([t[1] for t in truths]))
    unaligned_src = shift_arr(fuse_unaligned(obs), -mean_tx, -mean_ty)
    oracle_src = fuse_oracle(obs, truths)
    est_fused, est_relative = fuse_estimated(obs)
    est_src = shift_arr(est_fused, -truths[0][0], -truths[0][1])
    masks = {
        "A_single": (to_mask(single_src), single_src),
        "B_medoid": (to_mask(med_src), med_src),
        "C_unaligned": (to_mask(unaligned_src), unaligned_src),
        "D_oracle": (to_mask(oracle_src), oracle_src),
        "E_estimated": (to_mask(est_src), est_src),
    }
    serial = {}
    for k,(m,img) in masks.items():
        serial[k]={"metrics":{"iou":iou(m,src_mask),"boundary":boundary_dist(m,src_mask)},
                   "mask_shape":[int(x) for x in m.shape]}
    # reg errors per obs
    errs=[]
    for i,(o,t) in enumerate(zip(obs,truths)):
        if i==0:
            sx,sy,disp = (0.0,0.0,0.0)
        else:
            sx,sy,esterr=phase_shift(o,obs[0])
            sx0=truths[i][0]-truths[0][0]; sy0=truths[i][1]-truths[0][1]
            disp=float(np.hypot(sx-sx0,sy-sy0))
            relative_i=(sx,sy)
        errs.append({"truth":[float(t[0]),float(t[1])],"target_origin":[float(truths[0][0]),float(truths[0][1])],
                     "est_rel_to_first":[sx,sy] if i!=0 else [0.0,0.0],
                     "disp_err":disp})
    serial["registration"] = errs
    # outputs
    tagdir=os.path.join(outdir,tag); os.makedirs(tagdir,exist_ok=True)
    write_image(os.path.join(tagdir,"source_mask.png"),src_mask,mask=True)
    for k,(m,img) in masks.items():
        write_image(os.path.join(tagdir,f"{k}_mask.png"),m,mask=True)
        write_image(os.path.join(tagdir,f"{k}_gray.png"),img)
    for j,o in enumerate(obs):
        write_image(os.path.join(tagdir,f"obs_{j}.png"),o)
    # exact arrays
    np.save(os.path.join(tagdir,"source.npy"),src)
    np.save(os.path.join(tagdir,"metas.npy"),np.array(metas,dtype=object),allow_pickle=True)
    serial["truths"]=[[float(t[0]),float(t[1])] for t in truths]
    serial["metas"]=metas
    return serial, os.path.basename(tagdir)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "work", "m1c_r3", "diag"))
    ap.add_argument("--ns", nargs="+", type=int, default=[1, 2, 4, 8])
    ap.add_argument("--tag", default="r3-diag")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    report = {"runs": []}
    font_hashes = {}
    for f in FONTS:
        font_hashes[f] = font_hash(f)
    summary = {n: {k: [] for k in ["A_single", "B_medoid", "C_unaligned", "D_oracle", "E_estimated"]} for n in args.ns}
    reg_all = []
    for font in FONTS:
        for ch in GLYPHS:
            for n in args.ns:
                res, tagdir = run(font, ch, n, args.out, f"{args.tag}_{os.path.basename(font)}_{ch}_n{n}")
                report["runs"].append({"font": os.path.basename(font), "glyph": ch, "n": n, "result": res, "dir": tagdir})
                # re-compute summary by loading masks again is awkward; store metrics directly in run
            print(f"DONE {os.path.basename(font)} {ch}")
    # load metrics: they are in report runs, keys under result group metric
    for rrr in report["runs"]:
        for k in ["A_single", "B_medoid", "C_unaligned", "D_oracle", "E_estimated"]:
            summary[rrr["n"]][k].append(rrr["result"][k]["metrics"])
        reg_all.extend(rrr["result"].get("registration", []))
    # medians
    final = {}
    for n in args.ns:
        final[str(n)] = {}
        for k in ["A_single", "B_medoid", "C_unaligned", "D_oracle", "E_estimated"]:
            bs = [r["boundary"] for r in summary[n][k]]
            io = [r["iou"] for r in summary[n][k]]
            final[str(n)][k] = {
                "boundary_median": float(np.median(bs)),
                "iou_median": float(np.median(io)),
                "n_groups": len(bs),
            }
    # registration stats
    disp = [r.get("disp_err", np.nan) for r in reg_all if r.get("disp_err") is not None]
    final["registration"] = {
        "median_disp_err": float(np.nanmedian(disp)),
        "max_disp_err": float(np.nanmax(disp)),
        "bias_x": float(np.nanmean([r["est_rel"][0] + r["truth"][0] for r in reg_all if "est_rel" in r])) if reg_all else float("nan"),
    }
    report["font_hashes"] = font_hashes
    report["environment"] = {
        "python": os.sys.version,
        "command": " ".join(os.sys.argv),
    }
    report["final"] = final
    json.dump(report, open(os.path.join(args.out, "diagnostic_full.json"), "w"), indent=2)
    # print table
    print("\nD (oracle) vs C (unaligned) median boundary (lower better):")
    for n in args.ns:
        print(f"N={n}: A={final[str(n)]['A_single']['boundary_median']:.3f} B={final[str(n)]['B_medoid']['boundary_median']:.3f} C={final[str(n)]['C_unaligned']['boundary_median']:.3f} D={final[str(n)]['D_oracle']['boundary_median']:.3f} E={final[str(n)]['E_estimated']['boundary_median']:.3f}")
    print("reg disp median/max:", final["registration"]["median_disp_err"], final["registration"]["max_disp_err"])
    # write markdown table
    with open(os.path.join(args.out, "table.md"), "w") as f:
        f.write("| N | A single | B medoid | C unaligned | D oracle | E estimated |\n")
        f.write("|---:|---:|---:|---:|---:|---:|\n")
        for n in args.ns:
            f.write(f"| {n} | {final[str(n)]['A_single']['boundary_median']:.3f} | {final[str(n)]['B_medoid']['boundary_median']:.3f} | {final[str(n)]['C_unaligned']['boundary_median']:.3f} | {final[str(n)]['D_oracle']['boundary_median']:.3f} | {final[str(n)]['E_estimated']['boundary_median']:.3f} |\n")
            f.write(f"| {n} IoU | {final[str(n)]['A_single']['iou_median']:.3f} | {final[str(n)]['B_medoid']['iou_median']:.3f} | {final[str(n)]['C_unaligned']['iou_median']:.3f} | {final[str(n)]['D_oracle']['iou_median']:.3f} | {final[str(n)]['E_estimated']['iou_median']:.3f} |\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
