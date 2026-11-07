#!/usr/bin/env python3
"""ACR-06 CP3: visual panels for the background-structure counterfactuals.

For each crop (relative page coordinates) the columns are, at 300 DPI-equivalent:
  source | ScanWeave now | A: background at 150 DPI | B: 1-bit ink mask @300 + paper @150 | Adobe XI | Archive MRC
A and B are offline simulations from ScanWeave's own stored background. They are meant
for crops whose text is raster in ScanWeave (vector glyphs are not redrawn there).
Comparator pages are scaled to the source width; Adobe's page box differs slightly, so
its crop can be offset by a few pixels.
Usage: panels.py OUTDIR"""
import io, sys
from pathlib import Path
import numpy as np, pikepdf, pypdfium2 as pdfium
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
from background_counterfactuals import page_backgrounds, paper

Q = Path(__file__).resolve().parents[2]
CROPS = [  # group, page, (x0, y0, x1, y1) relative
    ("historical", 3, (0.10, 0.30, 0.62, 0.45)),
    ("historical", 1, (0.08, 0.20, 0.60, 0.33)),
    ("receipts", 5, (0.05, 0.30, 0.95, 0.48)),
    ("financial", 0, (0.08, 0.15, 0.60, 0.28)),
]
ARMS = {"source": "pdf_packaging/groups/{g}-input.pdf", "now": "acr06/local/donorfix/candidate/{g}.pdf",
        "adobe": "pdf_packaging/groups/{g}-adobe.pdf", "archive": "pdf_packaging/groups/{g}-archive.pdf"}


def render(path, page, width_px):
    pg = pdfium.PdfDocument(str(path))[page]
    return pg.render(scale=width_px / pg.get_width()).to_pil().convert("RGB")


def jpeg_roundtrip(im, q=85):
    b = io.BytesIO(); im.save(b, "JPEG", quality=q, subsampling=2, optimize=True); b.seek(0)
    return Image.open(b).convert("RGB")


def simulations(g, page, size):
    pdf = pikepdf.open(Q / ARMS["now"].format(g=g))
    for i, x, dpi in page_backgrounds(pdf):
        if i != page:
            continue
        bg = pikepdf.PdfImage(x).as_pil_image().convert("RGB")
        p, gray = paper(bg)
        dark = (p - gray) > 40
        arr = np.asarray(bg, dtype=np.int16)
        s = 150 / dpi
        a = jpeg_roundtrip(bg.resize((round(bg.width * s), round(bg.height * s)), Image.Resampling.LANCZOS)).resize(size, Image.Resampling.BICUBIC)
        noink = arr.copy(); noink[dark] = p[dark][:, None]
        paper150 = jpeg_roundtrip(Image.fromarray(np.clip(noink, 0, 255).astype(np.uint8)).resize((round(bg.width * s), round(bg.height * s)), Image.Resampling.LANCZOS)).resize(size, Image.Resampling.BICUBIC)
        ink = np.median(arr[dark], axis=0) if dark.any() else np.array([0, 0, 0])
        mask = np.asarray(Image.fromarray((dark * 255).astype(np.uint8)).resize(size, Image.Resampling.NEAREST)) > 127
        b = np.asarray(paper150).copy(); b[mask] = ink.astype(np.uint8)
        return a, Image.fromarray(b)
    raise SystemExit(f"no DCT background on {g} p{page}")


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    for g, page, rel in CROPS:
        src = pdfium.PdfDocument(str(Q / ARMS["source"].format(g=g)))[page]
        width = round(src.get_width() / 72 * 300)
        full = {k: render(Q / v.format(g=g), page, width) for k, v in ARMS.items()}
        size = full["now"].size
        a, b = simulations(g, page, size)
        cols = [("source", full["source"]), ("ScanWeave now", full["now"]), ("A: background 150 DPI", a),
                ("B: ink mask 300 + paper 150", b), ("Adobe XI", full["adobe"]), ("Archive MRC", full["archive"])]
        tiles = []
        for name, im in cols:
            w, h = im.size
            box = (round(rel[0] * w), round(rel[1] * h), round(rel[2] * w), round(rel[3] * h))
            tiles.append((name, im.crop(box)))
        tw, th = tiles[0][1].size
        sheet = Image.new("RGB", (tw, (th + 22) * len(tiles)), "white")
        d = ImageDraw.Draw(sheet)
        for k, (name, t) in enumerate(tiles):
            y = k * (th + 22)
            d.text((4, y + 4), name, fill=(0, 0, 160))
            sheet.paste(t.resize((tw, th)), (0, y + 20))
        path = out / f"{g}-p{page}.png"
        sheet.save(path, optimize=True)
        print(path, sheet.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
