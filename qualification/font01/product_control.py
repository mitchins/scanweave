"""Run the existing Rust dictionary with public glyph observations, not font labels.

This is a controlled OCR-input arm, not a claim about real Tesseract accuracy.
It never opens the evaluator manifest, font files, pristine images or oracle/.
"""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

from .observations import ORACLE_FIELDS, source_path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def span_from_record(record):
    x0, y0, x1, y1 = record['bbox']
    polygon = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    confidence = {'value': 99., 'scale': 'range_0_100', 'calibrated': False}
    identifier = 'g' + record['id']
    return {'id': identifier, 'text': record['character'], 'separator_after': '',
            'confidence': confidence, 'direction': 'ltr', 'provenance': 'source_generated',
            'role': 'body', 'language': None, 'polygon': polygon,
            'symbols': [{'id': identifier, 'confidence': confidence,
                         'text_range_utf8': [0, len(record['character'].encode('utf-8'))],
                         'polygon': polygon}]}


def write_page(root, output, records, page_number):
    dpi = records[0]['dpi']
    if isinstance(dpi, bool) or not isinstance(dpi, (int, float)) or not math.isfinite(dpi) or dpi <= 0:
        raise ValueError('Scan DPI must be finite and positive')
    if any(row['dpi'] != dpi for row in records):
        raise ValueError('Inconsistent scan DPI within one page')
    image_name = f'page-{page_number}.png'
    with Image.open(source_path(root, image_name)) as source:
        image = source.convert('RGB')
    image.save(output / image_name)
    width, height = image.size
    file_hash = sha((output / image_name).read_bytes())
    prefix = f'SWRASTER1\nrgb8\n{width}\n{height}\nsrgb\n-\n'.encode()
    page_id = f'p{page_number:03}'
    ocr = {'schema_version': '1.0', 'page_id': page_id, 'granularity': 'symbol',
           'page': {'width_pt': width*72/dpi, 'height_pt': height*72/dpi,
                    'raster_to_page_pt': [72/dpi, 0, 0, -72/dpi, 0, height*72/dpi]},
           'raster': {'asset_path': image_name, 'file_sha256': file_hash,
                      'pixel_sha256': sha(prefix+image.tobytes()), 'width_px': width,
                      'height_px': height, 'canonical_format': 'rgb8', 'colour_tag': 'srgb',
                      'icc_sha256': None, 'orientation_policy': 'applied_once',
                      'decoder_id': 'font01-public-observation-control-v1', 'dpi_x': dpi, 'dpi_y': dpi},
           'producer': {'name': 'font01-public-observation-control', 'version': '1',
                        'models': [], 'languages': []}, 'reading_order_status': 'supplied',
           'reading_order': ['g'+row['id'] for row in records], 'protected_regions': [],
           'spans': [span_from_record(row) for row in records]}
    ocr_name = f'page-{page_number}.ocr.json'
    (output / ocr_name).write_text(json.dumps(ocr, indent=2)+'\n')
    source = {'source_id': page_id, 'asset_path': image_name, 'file_sha256': file_hash, 'kind': 'image'}
    page = {'page_id': page_id, 'source_id': page_id, 'source_page_index': 0,
            'ocr_page_path': ocr_name, 'ocr_page_sha256': sha((output / ocr_name).read_bytes())}
    return source, page


def make_bundle(directory, destination):
    root, output = Path(directory).resolve(strict=True), Path(destination)
    rows = [json.loads(line) for line in source_path(root, 'observations.jsonl').read_text().splitlines()]
    if not rows or any(ORACLE_FIELDS.intersection(row) for row in rows):
        raise ValueError('Expected nonempty public observations without oracle fields')
    groups = {}
    for row in rows:
        if not isinstance(row['page'], int) or row['page'] < 0:
            raise ValueError('Page indices must be nonnegative integers')
        groups.setdefault(row['page'], []).append(row)
    output.mkdir(parents=True, exist_ok=False)
    sources, pages = [], []
    for page_number, records in sorted(groups.items()):
        source, page = write_page(root, output, records, page_number)
        sources.append(source)
        pages.append(page)
    document = {'schema_version': '1.0', 'document_id': 'font01-public-observation-control',
                'sources': sources, 'pages': pages}
    path = output / 'document.json'
    path.write_text(json.dumps(document, indent=2)+'\n')
    (output / 'observation-map.json').write_text(json.dumps(
        {'g'+row['id']: row['id'] for row in rows}, indent=2)+'\n')
    return path
