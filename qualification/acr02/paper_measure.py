"""Decoded-background measurements in the controlled blank strip, not an ink oracle."""
import json
from pathlib import Path

import numpy as np
import pikepdf

ROOT = Path('qualification/acr02/local')
fixtures = json.loads((ROOT / 'fixtures.json').read_text())
inventory = json.loads((ROOT / 'adobe-layers/inventory.json').read_text())
rows = []
with pikepdf.open(ROOT / 'controlled-adobe.pdf') as pdf:
    for page in inventory['pages']:
        draws = [op for op in page['paint_graph'] if op['kind'] == 'image']
        first = inventory['images'][draws[0]['resource']]
        image = pikepdf.PdfImage(pdf.get_object(tuple(first['object']))).as_pil_image().convert('RGB')
        box = (round(100 * image.width / 1500), round(430 * image.height / 1800),
               round(1400 * image.width / 1500), round(460 * image.height / 1800))
        samples = np.asarray(image.crop(box), dtype=float)
        rows.append({'id': fixtures['pages'][page['page']]['id'], 'first_image_object': first['object'],
                     'effective_dpi': draws[0]['effective_dpi'],
                     'paper_mean_rgb': samples.mean(axis=(0, 1)).tolist(),
                     'paper_channel_std': samples.std(axis=(0, 1)).tolist()})
(ROOT / 'paper-measurements.json').write_text(json.dumps(rows, indent=2) + '\n')
