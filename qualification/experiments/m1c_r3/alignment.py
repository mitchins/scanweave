import numpy as np
from PIL import Image

def shift_arr(arr, sx, sy):
    """Apply translation (sx,sy) in pixels to an image (affine inverse sign handled)."""
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    im = im.transform(im.size, Image.Transform.AFFINE,
                      (1, 0, sx, 0, 1, sy), fillcolor=0,
                      resample=Image.BILINEAR)
    return np.asarray(im, dtype=np.float32) / 255.0

_reference = None

def coarse_peak(obs, ref):
    fa = np.fft.fft2(obs); fb = np.conj(np.fft.fft2(ref))
    cross = fa * fb / (np.abs(fa * fb) + 1e-9)
    corr = np.abs(np.fft.fftshift(np.fft.ifft2(cross)))
    ys, xs = np.unravel_index(np.argmax(corr), corr.shape)
    return int(xs - obs.shape[1] // 2), int(ys - obs.shape[0] // 2)

def mse(a, b):
    return float(np.mean((a - b) ** 2))


def refine_x(obs,ref,sx,sy,step=0.125):
    left=mse(shift_arr(obs,sx-step,sy),ref)
    mid=mse(shift_arr(obs,sx,sy),ref)
    right=mse(shift_arr(obs,sx+step,sy),ref)
    den=left-2*mid+right
    if abs(den)>1e-12:
        return 0.5*step*(left-right)/den
    return 0.0

def refine_y(obs,ref,sx,sy,step=0.125):
    left=mse(shift_arr(obs,sx,sy-step),ref)
    mid=mse(shift_arr(obs,sx,sy),ref)
    right=mse(shift_arr(obs,sx,sy+step),ref)
    den=left-2*mid+right
    if abs(den)>1e-12:
        return 0.5*step*(left-right)/den
    return 0.0

def best_grid_shift(obs, ref, xs, ys, best, best_e):
    """Retain the original y-major search order and strict tie-breaking rule."""
    for y in ys:
        for x in xs:
            e = mse(shift_arr(obs, float(x), float(y)), ref)
            if e < best_e:
                best_e = e
                best = (float(x), float(y))
    return best, best_e

def phase_shift(obs, ref, stage='low'):
    """Estimate the shift to PASS to shift_arr(obs,...) so obs aligns with ref.

    Coarse Fourier peak + two-stage MSE refinement. No oracle / labels.
    """
    cx, cy = coarse_peak(obs, ref)
    # coarse correction may be opposite sign from image-domain direct FFT; build
    # candidates around coarse and optimize direct image MSE.
    def candidates(center, radius, step):
        vals = np.arange(center - radius, center + radius + 1e-9, step)
        if center not in vals:
            vals = np.append(vals, center)
        return np.unique(np.round(vals / step) * step)
    xs = candidates(cx, 4.0, 1.0)
    ys = candidates(cy, 4.0, 1.0)
    best = (0.0, 0.0); best_e = mse(shift_arr(obs, 0.0, 0.0), ref)
    best, best_e = best_grid_shift(obs, ref, xs, ys, best, best_e)
    # finer
    x0, y0 = best
    xs = candidates(x0, 1.25, 0.25)
    ys = candidates(y0, 1.25, 0.25)
    best, best_e = best_grid_shift(obs, ref, xs, ys, best, best_e)
    # finest
    x0, y0 = best
    xs = candidates(x0, 0.5, 0.125)
    ys = candidates(y0, 0.5, 0.125)
    best, best_e = best_grid_shift(obs, ref, xs, ys, best, best_e)
    sx,sy=best
    sx0=sx; sy0=sy
    dx=refine_x(obs,ref,sx,sy,0.125)
    dy=refine_y(obs,ref,sx,sy,0.125)
    sx=sx+max(-0.25,min(0.25,dx))
    sy=sy+max(-0.25,min(0.25,dy))
    err=mse(shift_arr(obs,sx,sy),ref)
    return (sx,sy,err)

def align(obs, ref):
    sx, sy, err = phase_shift(obs, ref)
    return shift_arr(obs, sx, sy), sx, sy, err
