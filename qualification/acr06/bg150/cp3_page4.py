#!/usr/bin/env python3
"""Reproduce CP3's zero-based historical-p4 background OCR comparison.

This is an offline re-encoding of an existing 200-DPI JPEG, not the proposed
encoder operating on the original residual pixels.
"""
import io
import json
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium
import numpy as np
from PIL import Image
from scipy import ndimage

Q = Path('/data/coding/scanweave/qualification')
OUT = Q / 'acr06/bg150/cp3_page4.json'

def words(im):
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        im.save(f.name)
        result = subprocess.run(['tesseract', f.name, '-', '--psm', '3', '-l', 'eng'],
                                capture_output=True, text=True, check=True)
    return Counter(re.findall(r'[A-Za-z0-9]{2,}', result.stdout))

pdf = pikepdf.open(Q / 'acr06/local/donorfix/candidate/historical.pdf')
page = pdf.pages[4]
images = [x for x in page.Resources.XObject.values()
          if x.get('/Subtype') == '/Image' and str(x.get('/Filter')) == '/DCTDecode']
x = max(images, key=lambda v: int(v.Width) * int(v.Height))
bg = pikepdf.PdfImage(x).as_pil_image().convert('RGB')
mb = [float(v) for v in page.mediabox]
dpi = bg.width * 72 / (mb[2] - mb[0])
size = (round(bg.width * 300 / dpi), round(bg.height * 300 / dpi))
buf = io.BytesIO()
bg.resize((round(bg.width * 150 / dpi), round(bg.height * 150 / dpi)),
          Image.Resampling.LANCZOS).save(buf, 'JPEG', quality=85, subsampling=2)
buf.seek(0)
low = Image.open(buf).convert('RGB').resize(size, Image.Resampling.BICUBIC)
src = pdfium.PdfDocument(str(Q / 'pdf_packaging/groups/historical-input.pdf'))[4]
ref = words(src.render(scale=size[0] / src.get_width()).to_pil().convert('RGB'))
now = words(bg.resize(size, Image.Resampling.BICUBIC))
reduced = words(low)
default_pixels = np.asarray(bg.resize(size, Image.Resampling.BICUBIC).convert('L'), dtype=np.float32)
low_pixels = np.asarray(low.convert('L'), dtype=np.float32)
paper = ndimage.gaussian_filter(default_pixels, sigma=16)
ink = paper - default_pixels > 30
default_contrast = paper - default_pixels
low_contrast = paper - low_pixels
labels, count = ndimage.label(ink)
areas = np.bincount(labels.ravel())[1:]
tiny = (areas >= 2) & (areas <= 20)
tiny_labels = np.flatnonzero(tiny) + 1
survives = ndimage.maximum(low_contrast, labels=labels, index=tiny_labels) >= 30
output = {'page_zero_based': 4, 'source_words': sum(ref.values()),
          'default_recalled': sum((ref & now).values()),
          'counterfactual_recalled': sum((ref & reduced).values()),
          'lost_source_words': list(((ref & now) - (ref & reduced)).elements()),
          'gained_source_words': list(((ref & reduced) - (ref & now)).elements()),
          'all_default_words_lost': list((now - reduced).elements()),
          'all_counterfactual_words_gained': list((reduced - now).elements()),
          'stored_dimensions': list(bg.size), 'stored_dpi': dpi,
          'counterfactual_dimensions': [round(bg.width * 150 / dpi), round(bg.height * 150 / dpi)],
          'exploratory_300dpi_background_metrics': {
              'ink_threshold': 'stored background >30 levels darker than Gaussian local paper, sigma 16 px',
              'tiny_component_area_px': [2, 20], 'tiny_components': int(len(tiny_labels)),
              'tiny_components_with_30_level_peak_after': int(np.count_nonzero(survives)),
              'mean_default_contrast_at_ink': float(default_contrast[ink].mean()),
              'mean_counterfactual_contrast_at_same_pixels': float(low_contrast[ink].mean()),
              'note': 'Exploratory stored-JPEG comparison; components are not classified punctuation and are not source truth.'}}
OUT.write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output, indent=2))
