"""Matched four-page document comparisons, preserving each converter's geometry."""
import json
from pathlib import Path

from anatomy import atlas
from render_compare import frame, features
from PIL import Image, ImageDraw

ROOT = Path('qualification/acr02/local')
rows = []
labels = ['source', 'Adobe XI', 'ACR01', 'coverage256/JPEG', 'coverage16/indexed16']
paths = [ROOT / name for name in ('prototype-input.pdf', 'prototype-adobe.pdf', 'prototype-acr01.pdf', 'prototype-controlled-jpeg.pdf', 'prototype-controlled-indexed.pdf')]
for page in range(4):
    for engine in ('pdfium', 'poppler'):
        images = [frame(str(path), page, engine, 300) for path in paths]
        out = ROOT / 'controlled-comparison'
        out.mkdir(exist_ok=True)
        atlas(images, labels, out / f'p{page}-{engine}.png')
        for region, rect in {'body': (90, 570, 1400, 850), 'logo': (1040, 140, 1420, 440), 'crossing': (100, 800, 1050, 1020)}.items():
            crops = [im.crop(rect) for im in images]
            canvas = Image.new('RGB', (crops[0].width * len(crops), crops[0].height + 25), 'white')
            d = ImageDraw.Draw(canvas)
            for i, crop in enumerate(crops):
                canvas.paste(crop, (i * crop.width, 25)); d.text((i * crop.width, 3), labels[i], fill='black')
            canvas.save(out / f'p{page}-{region}-{engine}.png')
            rows.append({'page': page, 'renderer': engine, 'region': region, 'rect_source_pixels300dpi': rect,
                         'metrics': {label: features(crops[0], im) for label, im in zip(labels[1:], crops[1:])}})
(ROOT / 'controlled-region-results.json').write_text(json.dumps(rows, indent=2) + '\n')
