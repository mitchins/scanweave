#!/usr/bin/env python3
"""M0-Q Q2 — visual-failure characterization.

Questions (operator charter):
  (A) Is PDFium's ~1.1px displacement a geometry/placement defect or renderer AA?
      - signed displacement histograms vs Poppler on the same PDFs
      - rasterizer-independent outline check: render the embedded TTF directly
        (FreeType via PIL) and compare against the source mask
      - high-resolution convergence: 600dpi renders downsampled to 300dpi
  (B) Where does p01's MAE 0.0206 come from? Decompose by distance band from the
      source ink boundary (AA band / near / far) and by source content class.
  (C) Localized crops: counters (8/6/𝐀), punctuation, currency, kana dakuten.

Writes qualification/characterization.json and prints a summary.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, "work", "m0-checks")
FIX = os.path.join(HERE, "fixtures", "probe")

sys.path.insert(0, os.path.join(HERE, ".venv", "lib", "python3.12", "site-packages"))
import pypdfium2 as pdfium  # noqa: E402

THRESH = 60.0


def paper_lum(rgb):
    patches = np.concatenate(
        [rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3),
         rgb[-8:, :8].reshape(-1, 3), rgb[-8:, -8:].reshape(-1, 3)]
    )
    med = np.median(patches, axis=0)
    return 0.2126 * med[0] + 0.7152 * med[1] + 0.0722 * med[2]


def gray_of(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def fg(gray, paper, t=THRESH):
    return np.abs(gray.astype(float) - paper) > t


def load_page(name, engine):
    if engine == "source":
        return np.asarray(Image.open(os.path.join(FIX, name, f"{name}.png")).convert("L"))
    p = os.path.join(WORK, name, f"render_{engine}.png")
    if not os.path.exists(p):
        return None
    img = np.asarray(Image.open(p).convert("L"))
    src_shape = np.asarray(Image.open(os.path.join(FIX, name, f"{name}.png")).convert("L")).shape
    return img[: src_shape[0], : src_shape[1]]


def boundary_points_mask(m):
    """Integer boundary pixels (centres +0.5)."""
    er = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    b = m & ~er
    ys, xs = np.nonzero(b)
    return np.stack([xs + 0.5, ys + 0.5], axis=1).astype(np.float64)


def signed_displacement(points_from, target, cap=8.0):
    """For each point in points_from: vector to nearest point of target (dx, dy)."""
    if len(points_from) == 0 or len(target) == 0:
        return np.zeros((0, 2))
    if len(target) > 30000:
        target = target[:: len(target) // 30000 + 1]
    d2 = (
        (points_from[:, 0][:, None] - target[:, 0][None, :]) ** 2
        + (points_from[:, 1][:, None] - target[:, 1][None, :]) ** 2
    )
    nearest = np.argmin(d2, axis=1)
    d = np.sqrt(d2[np.arange(len(points_from)), nearest])
    keep = d <= cap
    dx = target[nearest][keep, 0] - points_from[keep, 0]
    dy = target[nearest][keep, 1] - points_from[keep, 1]
    return np.stack([dx, dy], axis=1)


def char_a(name):
    out = {}
    src = load_page(name, "source")
    pop = load_page(name, "poppler")
    pdf = load_page(name, "pdfium")
    if pop is None or pdf is None:
        return {"error": "missing renders"}
    p_lum = paper_lum(np.stack([src] * 3, -1)[..., :3]) if src.ndim == 2 else None
    # paper from RGB files
    rgb = np.asarray(Image.open(os.path.join(FIX, name, f"{name}.png")).convert("RGB"))
    p_lum = paper_lum(rgb)
    ms, mp, mf = fg(src, p_lum), fg(pop, paper_lum(rgb)), fg(pdf, paper_lum(rgb))
    bs, bp, bf = boundary_points_mask(ms), boundary_points_mask(mp), boundary_points_mask(mf)

    # signed displacement: pdfium boundary -> nearest poppler boundary
    d_pf = signed_displacement(bf, bp)
    d_ps = signed_displacement(bp, bs)
    for label, d in (("pdfium_vs_poppler", d_pf), ("poppler_vs_source", d_ps)):
        if len(d) == 0:
            continue
        mag = np.hypot(d[:, 0], d[:, 1])
        out[label] = {
            "n": int(len(d)),
            "mean_dx": round(float(d[:, 0].mean()), 3),
            "mean_dy": round(float(d[:, 1].mean()), 3),
            "mean_mag": round(float(mag.mean()), 3),
            "p95_mag": round(float(np.percentile(mag, 95)), 3),
            "max_mag": round(float(mag.max()), 3),
            "frac_lt_0.5px": round(float((mag < 0.5).mean()), 4),
            "frac_lt_1px": round(float((mag < 1.0).mean()), 4),
        }
    return out


def char_b():
    """p01 MAE decomposition by distance band from source ink boundary."""
    src = load_page("p01_latin", "source")
    pop = load_page("p01_latin", "poppler")
    rgb = np.asarray(Image.open(os.path.join(FIX, "p01_latin", "p01_latin.png")).convert("RGB"))
    p_lum = paper_lum(rgb)
    ms = fg(src, p_lum)
    # distance from source ink boundary via iterative dilation (integer bands)
    band = np.zeros(ms.shape, dtype=np.int32)
    cur = boundary_points_mask(ms)
    # rasterize boundary points to a mask
    bmask = np.zeros(ms.shape, dtype=bool)
    bmask[cur[:, 1].astype(int), cur[:, 0].astype(int)] = True
    d = np.full(ms.shape, 99, dtype=np.int32)
    cur2 = bmask.copy()
    for r in range(1, 20):
        grown = cur2.copy()
        grown[1:, :] |= cur2[:-1, :]
        grown[:-1, :] |= cur2[1:, :]
        grown[:, 1:] |= cur2[:, :-1]
        grown[:, :-1] |= cur2[:, 1:]
        d[grown & (d > r)] = r
        cur2 = grown
    diff = np.abs(src.astype(float) - pop.astype(float))
    ink_dilated = __import__("scipy_ndali", fromlist=["x"]) if False else None
    res = {}
    bands = {"edge_0_1px": (d <= 1), "near_2_3px": (d >= 2) & (d <= 3), "far_gt3": (d > 3) & (d < 99)}
    for label, msk in bands.items():
        if msk.any():
            res[label] = {
                "px": int(msk.sum()),
                "mean_abs_diff": round(float(diff[msk].mean()), 4),
                "contribution_pct": round(float(diff[msk].sum() / diff.sum() * 100), 2),
            }
    res["overall_mae"] = round(float(diff.mean() / 255.0), 4)
    return res


def char_c_outline_ground_truth():
    """Rasterizer-independent: render the EMBEDDED TTF glyphs via FreeType
    (PIL) at the source scale and compare with the source masks."""
    out = {}
    for name, glyph_chars in (
        ("p02_wronglabel", [("8", 0)]),  # gid 1 -> chars mapping via PIL: load by index
    ):
        ttf = os.path.join(WORK, name, "out.ttf")
        try:
            font = ImageFont.truetype(ttf, 152)  # p02 8 is ~150px tall ink
            img = Image.new("L", (200, 200), 255)
            d = ImageDraw.Draw(img)
            # draw via glyph index: PIL doesn't expose gid; use cmap char '8'
            d.text((10, 10), "8", font=font, fill=0)
            a = np.asarray(img)
            m = a < 128
            ys, xs = np.nonzero(m)
            out[name] = {
                "outline_render_ink": int(m.sum()),
                "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None,
                "note": "outline renders; geometry sanity only (exact compare needs the source crop)",
            }
        except Exception as e:  # noqa: BLE001
            out[name] = {"error": str(e)}
    return out


def char_d_highres_convergence():
    """Render p02 at 600dpi, downsample to the 300dpi grid, compare IoU.
    If convergence improves, the 300dpi difference is rasterization detail."""
    out = {}
    pdf = os.path.join(WORK, "p02_wronglabel", "out.pdf")
    src = load_page("p02_wronglabel", "source")
    rgb = np.asarray(Image.open(os.path.join(FIX, "p02_wronglabel", "p02_wronglabel.png")).convert("RGB"))
    p_lum = paper_lum(rgb)
    ms = fg(src, p_lum)
    for engine in ("poppler", "pdfium"):
        if engine == "pdfium":
            doc = pdfium.PdfDocument(pdf)
            pil = doc[0].render(scale=600 / 72.0).to_pil().convert("L")
            doc.close()
            hi = np.asarray(pil)
        else:
            r = __import__("subprocess").run(
                ["pdftoppm", "-r", "600", "-png", "-singlefile", pdf,
                 os.path.join(WORK, "p02_wronglabel", "hi600")], capture_output=True)
            hi = np.asarray(Image.open(os.path.join(WORK, "p02_wronglabel", "hi600.png")).convert("L"))
        # downsample 2x by averaging
        h, w = hi.shape
        lo = hi[: (h // 2) * 2, : (w // 2) * 2].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
        lo = lo[: src.shape[0], : src.shape[1]]
        mf = fg(lo, p_lum)
        inter = (ms & mf).sum()
        union = (ms | mf).sum()
        out[engine + "_600dpi_to_300"] = {"iou": round(float(inter / union), 4)}
    return out


def main():
    res = {}
    for name in ("p01_latin", "p02_wronglabel", "p04_ligature", "p05_colour", "p08_symbols"):
        res.setdefault("A_displacement", {})[name] = char_a(name)
    res["B_p01_mae_decomposition"] = char_b()
    res["C_outline_ground_truth"] = char_c_outline_ground_truth()
    res["D_highres_convergence"] = char_d_highres_convergence()
    with open(os.path.join(HERE, "characterization.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1)[:3000])
    print("written qualification/characterization.json")


if __name__ == "__main__":
    main()
