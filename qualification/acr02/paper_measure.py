"""Decoded-background measurements in a fixed PDF-coordinate blank strip."""
import json
from pathlib import Path

import numpy as np
import pikepdf

ROOT = Path('qualification/acr02/local')
# Source-pixel strip x100..1400,y430..460 at300DPI on a432pt-high page.
STRIP = (24.0, 321.6, 336.0, 328.8)


def measurement_image(inventory, page):
    for draw in page['paint_graph']:
        if draw['kind'] != 'image':
            continue
        state = inventory['graphics_states'][draw['state_ref']]
        a, b, c, d, e, f = state['ctm']
        if b != 0 or c != 0 or a <= 0 or d <= 0 or state['clips']:
            continue  # This measurement supports unrotated, unclipped rectangles.
        left, bottom, right, top = STRIP
        if not (e <= left and f <= bottom and e + a >= right and f + d >= top):
            continue
        image = inventory['images'][draw['resource']]
        w, h = image['Width'], image['Height']
        box = (round((left - e) * w / a), round((1 - (top - f) / d) * h),
               round((right - e) * w / a), round((1 - (bottom - f) / d) * h))
        return draw, image, box
    raise ValueError('No supported image placement covers the fixed paper strip')


def main():
    fixtures = json.loads((ROOT / 'fixtures.json').read_text())
    inventory = json.loads((ROOT / 'adobe-layers/inventory.json').read_text())
    rows = []
    with pikepdf.open(ROOT / 'controlled-adobe.pdf') as pdf:
        for page in inventory['pages']:
            draw, record, box = measurement_image(inventory, page)
            image = pikepdf.PdfImage(pdf.get_object(tuple(record['object']))).as_pil_image().convert('RGB')
            samples = np.asarray(image.crop(box), dtype=float)
            rows.append({'id': fixtures['pages'][page['page']]['id'], 'image_object': record['object'],
                         'fixed_pdf_strip': STRIP, 'decoded_pixel_box': box,
                         'effective_dpi': draw['effective_dpi'],
                         'paper_mean_rgb': samples.mean(axis=(0, 1)).tolist(),
                         'paper_channel_std': samples.std(axis=(0, 1)).tolist()})
    (ROOT / 'paper-measurements.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
