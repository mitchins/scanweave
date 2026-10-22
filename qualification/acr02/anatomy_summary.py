"""Compact per-page evidence from the exact-object Adobe inventory."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path('qualification/acr02/local')
x = json.loads((ROOT / 'adobe-layers/inventory.json').read_text())
f = json.loads((ROOT / 'fixtures.json').read_text())
rows = []
for page in x['pages']:
    draws = page['paint_graph']
    images = []
    for op in draws:
        if op['kind'] != 'image':
            continue
        im = x['images'][op['resource']]
        images.append({'object': op['resource'], 'pixels': [im['Width'], im['Height']],
                       'effective_dpi': op['effective_dpi'], 'encoded_bytes': im['encoded_bytes'],
                       'filter': im['filter'], 'mask': im['Mask'], 'soft_mask': im['SMask'],
                       'state': x['graphics_states'][op['state_ref']]})
    rows.append({'id': f['pages'][page['page']]['id'], 'page': page['page'], 'images': images,
                 'font_paint_operations': sum(o['kind'] == 'text' and o['render_mode'] != 3 for o in draws),
                 'vector_path_paints': sum(o['kind'] == 'non-font-vector' for o in draws),
                 'crop_box': page['CropBox'], 'media_box': page['MediaBox']})
(ROOT / 'anatomy-summary.json').write_text(json.dumps({'adobe_sha256': x['sha256'],
    'pdf_bytes': x['pdf_bytes'], 'stream_bytes': x['encoded_stream_bytes'],
    'unique_images': len(x['images']), 'unique_fonts': len(x['fonts']),
    'image_filters': dict(Counter(str(o['filter']) for o in x['images'].values())), 'pages': rows}, indent=2) + '\n')
print(x['pdf_bytes'], x['encoded_stream_bytes'], 'fonts',len(x['fonts']), 'images',len(x['images']))
