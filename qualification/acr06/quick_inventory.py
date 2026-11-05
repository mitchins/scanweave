"""ACR-06 Checkpoint 1 quick stream inventory (reviewer).

Unique PDF streams are classified as image XObjects (raster), embedded font programs or other streams.
Structure is total file bytes minus all stream payloads. Bytes are raw encoded stream lengths.
Usage: qualification/.venv/bin/python -I qualification/acr06/quick_inventory.py > qualification/acr06/checkpoint1-inventory.json
"""
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

import pikepdf

ROOT = Path(__file__).resolve().parents[2]
ARMS = {
    'adobe_xi': 'qualification/pdf_packaging/groups/{g}-adobe.pdf',
    'scanweave_default_main': 'qualification/font04/local/R2a/baseline/{g}-off.pdf',
    'input': 'qualification/pdf_packaging/groups/{g}-input.pdf',
}
GROUPS = ('financial', 'historical', 'receipts', 'mixed', 'forms')


def inventory(path):
    pdf = pikepdf.open(path)
    seen, classes, counts, filters = set(), collections.Counter(), collections.Counter(), collections.Counter()
    images = []
    for o in pdf.objects:
        if not isinstance(o, pikepdf.Stream) or o.objgen in seen:
            continue
        seen.add(o.objgen)
        size = len(o.read_raw_bytes())
        subtype = o.get('/Subtype')
        flt = o.get('/Filter')
        flt = '+'.join(str(x) for x in flt) if isinstance(flt, pikepdf.Array) else str(flt)
        if subtype == '/Image':
            kind = 'raster'
            images.append(dict(w=int(o.Width), h=int(o.Height), bpc=int(o.get('/BitsPerComponent', 0)), cs=str(o.get('/ColorSpace'))[:40],
                               filter=flt, bytes=size, smask='/SMask' in o, imagemask=bool(o.get('/ImageMask', False))))
            filters[flt] += size
        elif '/Length1' in o or '/Length2' in o or subtype in ('/Type1C', '/CIDFontType0C', '/OpenType'):
            kind = 'font'
            filters['font:' + ('TrueType' if '/Length1' in o else str(subtype))] += size
        else:
            kind = 'other_streams'
        classes[kind] += size
        counts[kind] += 1
    total = os.path.getsize(path)
    classes['structure'] = total - sum(classes.values())
    return dict(path=str(path.relative_to(ROOT)), bytes=total, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pages=len(pdf.pages),
                classes=dict(classes), counts=dict(counts), filters=dict(filters), image_count=len(images),
                largest_images=sorted(images, key=lambda i: -i['bytes'])[:8])


def main():
    out = {'schema': 'acr06-quick-inventory-v1', 'groups': {}}
    for g in GROUPS:
        out['groups'][g] = {arm: inventory(ROOT / p.format(g=g)) for arm, p in ARMS.items()}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == '__main__':
    main()
