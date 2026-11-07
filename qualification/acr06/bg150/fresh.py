#!/usr/bin/env python3
"""Frozen ACR-06 fresh tonal scans; seed 609150. Generates truth PNGs and PDFs."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pikepdf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path('/data/coding/scanweave/qualification/acr06/local/bg150/fresh')
OUT.mkdir(parents=True, exist_ok=True)
SEED = 609150
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
W, H = 2550, 3300
rng = np.random.default_rng(SEED)
pages = []
for page in range(2):
    yy, xx = np.mgrid[:H, :W]
    grain = rng.normal(0, 3.5, (H, W))
    shade = 243 - 7 * xx / W - 8 * yy / H + 3 * np.sin(xx / 210)
    a = np.clip(shade + grain, 0, 255).astype('uint8')
    im = Image.fromarray(a, 'L').convert('RGB')
    draw = ImageDraw.Draw(im)
    draw.text((150, 115), 'PRESERVATION STUDY — TONAL ORIGINAL', font=ImageFont.truetype(str(FONT), 46), fill=(55, 48, 39))
    for row in range(24):
        pt = 6 + row % 3
        font = ImageFont.truetype(str(FONT), round(pt * 300 / 72))
        text = f'Item {row+1:02d}: café naïve; 1.25, 3.14 : total ${row+1}.09. Faint marks i, j.'
        level = 90 if row % 5 else 155
        draw.text((155, 210 + row * 68), text, font=font, fill=(level, level-4, level-8))
    for y in range(1930, 2440, 60):
        draw.line((150, y, 1900, y), fill=(110, 105, 98), width=2)
    for x in range(150, 1901, 350):
        draw.line((x, 1930, x, 2410), fill=(110, 105, 98), width=2)
    # Repeatable halftone gradient and a soft, photo-like tonal region.
    for y in range(2550, 3100, 9):
        for x in range(160, 1050, 9):
            radius = 1 + int(3 * (x - 160) / 890)
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(90, 85, 78))
    art = rng.normal(145, 35, (550, 750)).clip(0,255).astype('uint8')
    art = Image.fromarray(art).filter(ImageFilter.GaussianBlur(8)).convert('RGB')
    im.paste(art, (1200, 2550))
    # Fine gaps in faint print model broken ink.
    for i in range(55):
        x = int(rng.integers(200, 1250)); y = int(rng.integers(220, 1800))
        draw.line((x, y, x+3, y), fill=(231, 225, 215), width=1)
    png = OUT / f'truth-{page+1}.png'; im.save(png)
    pdf = pikepdf.Pdf.new(); pw = 612 if page == 0 else 612.37; ph = 792 if page == 0 else 791.63
    pg = pdf.add_blank_page(page_size=(pw, ph))
    stream = pdf.make_stream(im.tobytes())
    stream.Type = pikepdf.Name.XObject; stream.Subtype = pikepdf.Name.Image
    stream.Width = W; stream.Height = H; stream.ColorSpace = pikepdf.Name.DeviceRGB; stream.BitsPerComponent = 8
    pg.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=stream))
    pg.Contents = pdf.make_stream(f'q {pw} 0 0 {ph} 0 0 cm /Im0 Do Q\n'.encode())
    path = OUT / f'page-{page+1}.pdf'; pdf.save(path)
    pages.append({'input': str(path), 'truth': str(png), 'pixels': [W,H], 'page_pt': [pw,ph], 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
manifest = {'seed': SEED, 'font': str(FONT), 'font_sha256': hashlib.sha256(FONT.read_bytes()).hexdigest(), 'font_license': 'Bitstream Vera; DejaVu changes public domain; /usr/share/doc/fonts-dejavu-core/copyright', 'blackletter': 'No identified permissively licensed blackletter font', 'pages': pages}
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
