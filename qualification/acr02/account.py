"""Bind final prototype results to exact PDFs; no image-area byte allocation."""
import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import PIL
import numpy
import pikepdf
import pypdfium2
import scipy


ROOT = Path('qualification/acr02/local')
PDFS = ['controlled-input.pdf', 'controlled-adobe.pdf', 'prototype-input.pdf',
        'prototype-adobe.pdf', 'prototype-acr01.pdf', 'prototype-controlled-jpeg.pdf',
        'prototype-controlled-indexed.pdf', 'history-jpeg256-final.pdf',
        'history-indexed16.pdf', 'financial-jpeg256-final.pdf',
        'financial-indexed16.pdf', 'financial-all-indexed16-final.pdf', 'financial-full13-indexed16.pdf']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resource_account(path):
    # Paint/clip forensics use the full inspector separately. Size accounting
    # does not need to decode thousands of unchanged historical image patches.
    with pikepdf.open(path) as pdf:
        fonts = set()
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Dictionary):
                for key in ('/FontFile', '/FontFile2', '/FontFile3'):
                    if key in obj:
                        fonts.add(obj[key].objgen)
        totals = dict(image=0, font_program=0, other_stream=0)
        images = []
        for obj in pdf.objects:
            if not isinstance(obj, pikepdf.Stream):
                continue
            category = ('image' if obj.get('/Subtype') == pikepdf.Name.Image else
                        'font_program' if obj.objgen in fonts else 'other_stream')
            size = len(obj.read_raw_bytes())
            totals[category] += size
            if category == 'image':
                images.append({'object': list(obj.objgen), 'bytes': size,
                               'pixels': [int(obj.Width), int(obj.Height)],
                               'filter': str(obj.get('/Filter')), 'bits': int(obj.BitsPerComponent),
                               'color_space': str(obj.ColorSpace),
                               'soft_mask': str(obj.get('/SMask').objgen) if '/SMask' in obj else None})
        return {'encoded_stream_bytes': totals, 'images': images,
                'pages': list(range(len(pdf.pages))),
                'serialized_residual_bytes': path.stat().st_size - sum(totals.values())}

def main():
    rows = []
    for name in PDFS:
        path = ROOT / name
        inv = resource_account(path)
        (ROOT / (path.stem + '-inventory.json')).write_text(json.dumps(inv, indent=2) + '\n')
        rows.append({'pdf': name, 'sha256': digest(path), 'pdf_bytes': path.stat().st_size,
                     'raster_bytes': inv['encoded_stream_bytes']['image'],
                     'font_program_bytes': inv['encoded_stream_bytes']['font_program'],
                     'other_stream_bytes': inv['encoded_stream_bytes']['other_stream'],
                     'serialized_residual_bytes': inv['serialized_residual_bytes'],
                     'images': len(inv['images']), 'pages': len(inv['pages'])})
    destination = Path('qualification/acr02/byte-accounting.csv')
    with destination.open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    files = [*Path('qualification/acr02').glob('*.py'), ROOT / 'fixtures.json',
             ROOT / 'prototype-membership.json', ROOT / 'verification.json',
             ROOT / 'anatomy-summary.json', ROOT / 'independent-code-review.md',
             ROOT / 'independent-visual-review.md']
    baseline = json.loads(Path('qualification/acr01/local/frozen-hashes.json').read_text())
    for row in baseline:
        assert digest(Path(row['path'])) == row['sha256'], row['path']
    metadata = {'base': '8f14cd329493ad0cc226e480d152d7a464fb4731',
                'product_main': '0ca94aecd74c35ea1b28bcebe7e11e863aae7f08',
                'research_helper_revision': 'ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e',
                'production_changed': False, 'frozen_hashes_verified': len(baseline),
                'scanweave_binary_sha256': digest(Path('target/release/scanweave')),
                'acrobat_runner_sha256': digest(Path('adobe-acrobat-sandbox/clearscan.sh')),
                'tools': {'python': platform.python_version(), 'Pillow': PIL.__version__,
                          'numpy': numpy.__version__, 'scipy': scipy.__version__,
                          'pikepdf': pikepdf.__version__, 'pdfium': str(pypdfium2.PDFIUM_INFO),
                          'wine': subprocess.check_output(['wine', '--version'], text=True).strip(),
                          'acrobat': '11.0.20 Paper Capture Plug-in with ClearScan (PDF Producer)',
                          'acrobat_settings': 'ClearScan explicitly selected by existing runner; sticky downsampling selector not reasserted; effective output resolution measured per object'},
                'files': [{'path': str(path), 'sha256': digest(path)} for path in files],
                'results': rows,
                'full36_scanweave': {'status': 'stopped; no output used', 'wall_seconds': 905.46,
                                     'peak_rss_kib': 689136, 'reason': 'bounded runtime after OCR; four-page prototypes separately named and converted as complete documents'},
                'commands': {'anatomy': 'anatomy.py controlled-adobe.pdf local/adobe-layers --pages 0,...,35',
                             'prototype': 'prototypes.py SOURCE OUT --pages INDICES --coverage-levels 256|16 --foreground jpeg|indexed16',
                             'financial_all': 'prototypes.py qualification/acr01/local/product/financial.pdf local/financial-full13-indexed16.pdf --pages 0,1,2,3,4,5,6,7,8,9,10,11,12 --coverage-levels 16 --foreground indexed16'}}
    Path('qualification/acr02/run-manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print([(row['pdf'], row['pdf_bytes']) for row in rows])


if __name__ == '__main__':
    main()
