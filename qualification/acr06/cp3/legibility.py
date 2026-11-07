#!/usr/bin/env python3
"""ACR-06 CP3: does a 150-DPI page background keep raster text legible?

For each ScanWeave page-layer DCT background, OCR (Tesseract, eng, psm 3) three images at
300 DPI-equivalent: the source page render, the stored background, and the background
resampled to 150 DPI (Q85 round trip). Report word recall of each against the source's
OCR words (multiset). Only raster text is visible in the background, so recall is over
words the source shows; vector-drawn words are absent from both background variants alike.
Usage: legibility.py OUT.json GROUP...  (ScanWeave outputs from acr06/local/donorfix/candidate)"""
import io, json, re, subprocess, sys, tempfile
from collections import Counter
from pathlib import Path
import pikepdf, pypdfium2 as pdfium
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from background_counterfactuals import page_backgrounds

Q = Path(__file__).resolve().parents[2]


def ocr(im):
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        im.save(f.name)
        t = subprocess.run(["tesseract", f.name, "-", "--psm", "3", "-l", "eng"], capture_output=True, text=True).stdout
    return Counter(w for w in re.findall(r"[A-Za-z0-9]{2,}", t))


def recall(ref, got):
    return sum((ref & got).values()), sum(ref.values())


res = {}
for g in sys.argv[2:]:
    pdf = pikepdf.open(Q / f"acr06/local/donorfix/candidate/{g}.pdf")
    src = pdfium.PdfDocument(str(Q / f"pdf_packaging/groups/{g}-input.pdf"))
    for i, x, dpi in page_backgrounds(pdf):
        bg = pikepdf.PdfImage(x).as_pil_image().convert("RGB")
        size = (round(bg.width * 300 / dpi), round(bg.height * 300 / dpi))
        s = 150 / dpi
        b = io.BytesIO()
        bg.resize((round(bg.width * s), round(bg.height * s)), Image.Resampling.LANCZOS).save(b, "JPEG", quality=85, subsampling=2)
        b.seek(0)
        low = Image.open(b).convert("RGB").resize(size, Image.Resampling.BICUBIC)
        page = src[i]
        ref = ocr(page.render(scale=size[0] / page.get_width()).to_pil().convert("RGB"))
        now = ocr(bg.resize(size, Image.Resampling.BICUBIC))
        r = dict(source_words=sum(ref.values()), now=recall(ref, now)[0], dpi150=recall(ref, ocr(low))[0])
        res[f"{g}-p{i}"] = r
        print(g, i, r, flush=True)
tot = Counter()
for r in res.values():
    tot.update(r)
print("TOTAL", dict(tot))
Path(sys.argv[1]).write_text(json.dumps(dict(pages=res, total=dict(tot)), indent=1) + "\n")
