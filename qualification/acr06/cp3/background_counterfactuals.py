#!/usr/bin/env python3
"""ACR-06 CP3: what drives page-background JPEG bytes.

For every page-layer DCT image of an arm, decode the stored background and re-encode it
with PIL/libjpeg under controlled changes. Measures only the background stream:
  same      Q85 4:2:0 at stored size (calibration against the stored bytes)
  dpi150    resampled to 150 DPI (Lanczos), Q85
  q75       stored size, Q75
  flat      near-paper pixels (|v - local paper| <= 12) set to the local paper estimate
  noink     pixels darker than local paper by > 40 replaced by local paper
Also reports residual-ink coverage: the fraction of pixels darker than local paper by > 40.
Local paper = 31x31 median of a 4x-downsampled grey image, upsampled.
Usage: background_counterfactuals.py OUT.json ARM=PDF [ARM=PDF ...]"""
import sys, io, json
from pathlib import Path
import numpy as np, pikepdf
from PIL import Image, ImageFilter


def jpeg_bytes(im, q=85, subsampling=2):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q, subsampling=subsampling, optimize=True)
    return b.tell()


def paper(im):
    g = im.convert("L")
    small = g.resize((max(1, g.width // 4), max(1, g.height // 4)), Image.Resampling.BOX)
    small = small.filter(ImageFilter.MedianFilter(31 if min(small.size) > 31 else 3))
    return np.asarray(small.resize(g.size, Image.Resampling.BILINEAR), dtype=np.int16), np.asarray(g, dtype=np.int16)


def page_backgrounds(pdf):
    for i, pg in enumerate(pdf.pages):
        mb = [float(v) for v in pg.mediabox]
        page_w = mb[2] - mb[0]
        for _, x in (pg.get("/Resources", {}).get("/XObject") or {}).items():
            if x.get("/Subtype") != "/Image":
                continue
            f = x.get("/Filter")
            f = [str(v) for v in f] if isinstance(f, pikepdf.Array) else [str(f)]
            if "/DCTDecode" not in f:
                continue
            w, h = int(x.Width), int(x.Height)
            dpi = w * 72 / page_w
            if w * h < 0.25 * (page_w / 72 * dpi) * ((mb[3] - mb[1]) / 72 * dpi):
                continue
            yield i, x, dpi


def main():
    res = {}
    for arg in sys.argv[2:]:
        arm, path = arg.split("=", 1)
        pdf = pikepdf.open(path)
        rows = []
        for i, x, dpi in page_backgrounds(pdf):
            im = pikepdf.PdfImage(x).as_pil_image().convert("RGB")
            stored = len(x.read_raw_bytes())
            p, g = paper(im)
            arr = np.asarray(im, dtype=np.int16)
            dark = (p - g) > 40
            near = np.abs(g - p) <= 12
            flat = arr.copy(); flat[near] = p[near][:, None]
            noink = arr.copy(); noink[dark] = p[dark][:, None]
            s = 150 / dpi
            r = dict(page=i, dpi=round(dpi, 1), w=im.width, h=im.height, stored=stored,
                     same=jpeg_bytes(im),
                     dpi150=jpeg_bytes(im.resize((round(im.width * s), round(im.height * s)), Image.Resampling.LANCZOS)) if dpi > 151 else None,
                     q75=jpeg_bytes(im, 75),
                     flat=jpeg_bytes(Image.fromarray(np.clip(flat, 0, 255).astype(np.uint8))),
                     noink=jpeg_bytes(Image.fromarray(np.clip(noink, 0, 255).astype(np.uint8))),
                     ink_coverage=round(float(dark.mean()), 4))
            rows.append(r)
            print(arm, i, r, flush=True)
        res[arm] = rows
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
