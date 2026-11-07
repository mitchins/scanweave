#!/usr/bin/env python3
"""Issue #31: visible output must be unchanged. Render every page of two PDFs with PDFium
and Poppler at 150 DPI and count differing pixels. Usage: render_identity.py A.pdf B.pdf"""
import sys, subprocess, tempfile, pathlib
import numpy as np, pypdfium2 as pdfium
from PIL import Image
a, b = sys.argv[1:3]
da, db = pdfium.PdfDocument(a), pdfium.PdfDocument(b)
assert len(da) == len(db)
diff = 0
for i in range(len(da)):
    x = np.asarray(da[i].render(scale=150 / 72).to_pil()); y = np.asarray(db[i].render(scale=150 / 72).to_pil())
    diff += int((x != y).any(axis=-1).sum()) if x.shape == y.shape else -1
with tempfile.TemporaryDirectory() as t:
    for n, p in (("a", a), ("b", b)):
        subprocess.run(["pdftoppm", "-r", "150", "-png", p, f"{t}/{n}"], check=True)
    pd = 0
    for f in sorted(pathlib.Path(t).glob("a-*.png")):
        x = np.asarray(Image.open(f)); y = np.asarray(Image.open(str(f).replace("/a-", "/b-")))
        pd += int((x != y).any(axis=-1).sum()) if x.shape == y.shape else -1
print(f"pages={len(da)} pdfium_diff_px={diff} poppler_diff_px={pd}")
