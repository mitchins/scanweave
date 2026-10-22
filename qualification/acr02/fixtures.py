"""Deterministic image-only paired anatomy fixtures; evaluator backgrounds stay local."""
import hashlib
import json
import zlib
from pathlib import Path

import numpy as np
import pikepdf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('qualification/acr02/local')
FAMILIES = ('mono-logo', 'flat-logo', 'photo-logo', 'receipt', 'statement', 'ornament')
VARIANTS = ('white', 'texture', 'yellow', 'illumination', 'annotation', 'stamp')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
W, H = 1500, 1800


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def font(size):
    return ImageFont.truetype(FONT, size)


def image_stream(pdf, image):
    obj = pikepdf.Stream(pdf, zlib.compress(image.tobytes(), 6))
    obj.Type = pikepdf.Name.XObject
    obj.Subtype = pikepdf.Name.Image
    obj.Width, obj.Height = image.size
    obj.ColorSpace = pikepdf.Name.DeviceRGB
    obj.BitsPerComponent = 8
    obj.Filter = pikepdf.Name.FlateDecode
    return obj


def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261022)
    grain = rng.normal(0, 2, (H, W, 1))
    y, x = np.mgrid[:H, :W]
    with pikepdf.open('qualification/pdf_packaging/groups/receipts-input.pdf') as src:
        resource = next(iter(src.pages[5].Resources.XObject.values()))
        photo = pikepdf.PdfImage(resource).as_pil_image().convert('RGB').resize((340, 280))
    pdf = pikepdf.new()
    rows = []
    for family in FAMILIES:
        for variant in VARIANTS:
            base = np.full((H, W, 3), 250., dtype=np.float32)
            if variant == 'texture':
                base += grain
            elif variant == 'yellow':
                base[:] = (239, 224, 184)
            elif variant == 'illumination':
                base -= (70 * (x / W) ** 2 + 35 * (y / H))[:, :, None]
            paper = Image.fromarray(np.uint8(np.clip(base, 0, 255)))
            image = paper.copy()
            d = ImageDraw.Draw(image)
            d.text((100, 80), 'SCANWEAVE / DOCUMENT OFFICE', font=font(48), fill=(25, 25, 25))
            if family in ('mono-logo', 'flat-logo'):
                color = (20, 20, 20) if family == 'mono-logo' else (20, 85, 150)
                d.ellipse((1070, 150, 1390, 350), outline=color, width=12)
                d.polygon([(1100, 310), (1230, 170), (1360, 310)], fill=color)
                d.text((1120, 360), 'S W', font=font(55), fill=color)
            elif family == 'photo-logo':
                image.paste(photo, (1050, 150))
            elif family == 'ornament':
                for k in range(12):
                    d.arc((100 + k * 100, 170, 240 + k * 100, 330), 0, 330, fill=(60, 40, 30), width=3)
            d.text((100, 480), 'Statement 204 — 22 October 2026', font=font(44), fill=(25, 25, 25))
            lines = ['Payment received: $1,204.08; balance $39.50.',
                     'Reference 018806 — invoice 6608 / account 109.',
                     'Small punctuation: 0.01, 1.10; 8/6; e a g.',
                     'Printed details, thin serifs and fine rules remain.']
            for i in range(14):
                text = lines[i % len(lines)]
                ink = (125, 125, 125) if family == 'receipt' and i % 3 == 0 else (35, 35, 35)
                d.text((100, 580 + i * 58), text, font=font(32), fill=ink)
            if family == 'statement':
                for yy in range(560, 1470, 58):
                    d.line((85, yy, 1410, yy), fill=(90, 90, 90), width=2)
                for xx in (85, 940, 1190, 1410):
                    d.line((xx, 560, xx, 1430), fill=(90, 90, 90), width=2)
                d.rectangle((90, 1500, 1400, 1590), fill=(215, 225, 235))
                d.text((120, 1510), 'TOTAL     $1,204.08', font=font(40), fill=(20, 20, 20))
            if variant == 'annotation':
                # Controlled drawn signature/scribble, not represented as genuine handwriting.
                d.line([(140, 900), (320, 850), (410, 980), (570, 810), (660, 960), (1000, 880)], fill=(20, 55, 160), width=7)
                d.line((200, 1520, 1250, 1580), fill=(145, 30, 20), width=3)
            if variant == 'stamp':
                d.ellipse((1000, 1430, 1390, 1710), outline=(175, 35, 45), width=5)
                d.text((1060, 1530), 'PAID 08', font=font(40), fill=(175, 35, 45))
            name = f'{family}-{variant}'
            path = ROOT / 'sources' / f'{name}.png'
            path.parent.mkdir(exist_ok=True)
            image.save(path, dpi=(300, 300))
            paper.save(path.with_name(name + '-paper.png'), dpi=(300, 300))
            page = pdf.add_blank_page(page_size=(W * 72 / 300, H * 72 / 300))
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image_stream(pdf, image)))
            page.Contents = pikepdf.Stream(pdf, f'q {W*72/300} 0 0 {H*72/300} 0 0 cm /Im Do Q'.encode())
            rows.append({'id': name, 'page': len(rows), 'family': family, 'variant': variant,
                         'source': str(path), 'sha256': digest(path), 'dpi': 300, 'pixels': [W, H]})
    out = ROOT / 'controlled-input.pdf'
    pdf.save(out, deterministic_id=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    (ROOT / 'fixtures.json').write_text(json.dumps({'font': FONT, 'font_sha256': digest(FONT),
        'photo_source': 'receipts-input.pdf page 6; existing licensed CORD development image',
        'pdf': str(out), 'pdf_sha256': digest(out), 'pages': rows}, indent=2) + '\n')
    print(out, len(rows), out.stat().st_size)


if __name__ == '__main__':
    build()
