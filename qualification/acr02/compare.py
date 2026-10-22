"""Fixed physical-coordinate comparison, no image registration or glyph resizing."""
import json
from pathlib import Path

import numpy as np

from anatomy import HELPERS, atlas
from render_compare import frame, features

ROOT = Path('qualification/acr02/local')
HISTORICAL_CANDIDATE = 'history-indexed16.pdf'
CASES = [('history-01', 'historical', 1, HISTORICAL_CANDIDATE),
         ('history-02', 'historical', 2, HISTORICAL_CANDIDATE),
         ('history-04', 'historical', 4, HISTORICAL_CANDIDATE),
         ('annual-111', 'financial', 10, 'financial-full13-indexed16.pdf')]


def main():
    rows = []
    out = ROOT / 'comparison'
    out.mkdir(exist_ok=True)
    for name, group, page, candidate in CASES:
        for engine in ('pdfium', 'poppler'):
            paths = [Path(f'qualification/pdf_packaging/groups/{group}-input.pdf'),
                     Path(f'qualification/pdf_packaging/groups/{group}-adobe.pdf'),
                     Path(f'qualification/acr01/local/product/{group}.pdf'), ROOT / candidate]
            images = [frame(str(p), page, engine, 300) for p in paths]
            labels = ['source', 'Adobe XI', 'ACR01', 'indexed-color + C16 mask']
            atlas(images, labels, out / f'{name}-{engine}.png')
            h, w = images[0].height, images[0].width
            boxes = [(0.05, 0.18, .90, .40), (.12, .70, .88, .92)]
            for number, box in enumerate(boxes):
                # Same source-selected physical rectangle in each canvas.
                rect = tuple(round(c * (w if i % 2 == 0 else h)) for i, c in enumerate(box))
                crops = [image.crop(rect) for image in images]
                canvas_path = out / f'{name}-r{number}-{engine}.png'
                # Large detail sheets retain native pixels, rather than thumb scaling.
                from PIL import Image, ImageDraw
                sheet = Image.new('RGB', (crops[0].width * 4, crops[0].height + 25), 'white')
                draw = ImageDraw.Draw(sheet)
                for i, crop in enumerate(crops):
                    sheet.paste(crop, (i * crop.width, 25)); draw.text((i * crop.width, 3), labels[i], fill='black')
                sheet.save(canvas_path)
                rows.append({'id': name, 'renderer': engine, 'region': number, 'source_box_fraction': box,
                             'candidate_pdf': str(paths[-1]),
                             'candidate': features(crops[0], crops[-1]), 'acr01': features(crops[0], crops[2])})
    (ROOT / 'region-results.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
