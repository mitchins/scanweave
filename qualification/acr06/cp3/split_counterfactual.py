#!/usr/bin/env python3
"""ACR-06 CP3: byte estimate for separating residual raster text from the page background.

Offline estimate on ScanWeave's own stored page backgrounds; no product change. For each
page-layer DCT background:
  ink mask   pixels darker than the local paper by > 40, upsampled to 300 DPI (nearest),
             1-bit, Flate (zlib level 9) = an MRC-style foreground stencil without a new codec
  paper      the background with ink pixels replaced by local paper, JPEG Q85 4:2:0
             at 150 and at 100 DPI
  ink colour one fill colour per page (negligible bytes; tone variation is lost)
The estimate is an upper bound on mask quality: it is cut from the 200-DPI JPEG, not the
source. Usage: split_counterfactual.py OUT.json background.json PDF... (ScanWeave arm)"""
import sys, io, json, zlib
from pathlib import Path
import numpy as np, pikepdf
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from background_counterfactuals import page_backgrounds, paper, jpeg_bytes

res = {}
for path in sys.argv[3:]:
    pdf = pikepdf.open(path); rows = []
    for i, x, dpi in page_backgrounds(pdf):
        im = pikepdf.PdfImage(x).as_pil_image().convert("RGB")
        p, g = paper(im)
        dark = (p - g) > 40
        arr = np.asarray(im, dtype=np.int16)
        noink = arr.copy(); noink[dark] = p[dark][:, None]
        paper_im = Image.fromarray(np.clip(noink, 0, 255).astype(np.uint8))
        s300 = 300 / dpi
        mask = Image.fromarray((dark * 255).astype(np.uint8)).resize((round(im.width * s300), round(im.height * s300)), Image.Resampling.NEAREST)
        packed = np.packbits(np.asarray(mask) > 127, axis=1).tobytes()
        row = dict(page=i, stored=len(x.read_raw_bytes()), mask_flate=len(zlib.compress(packed, 9)))
        for t in (150, 100):
            s = t / dpi
            row[f"paper{t}"] = jpeg_bytes(paper_im.resize((round(im.width * s), round(im.height * s)), Image.Resampling.LANCZOS))
        rows.append(row)
        print(Path(path).stem, row, flush=True)
    res[Path(path).stem] = rows
Path(sys.argv[1]).write_text(json.dumps(res, indent=1) + "\n")
