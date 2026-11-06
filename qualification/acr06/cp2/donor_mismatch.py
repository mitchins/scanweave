#!/usr/bin/env python3
"""ACR-06 CP2: list default-ClearScan donor/canonical substitutions whose replacement bbox differs from the observed glyph,
and render source vs output crops for a deterministic sample. Usage: donor_mismatch.py <qualification dir> <out dir> [per_group]"""
import sys, json, collections
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
Q, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True); K = int(sys.argv[3]) if len(sys.argv) > 3 else 8
APPLIED = ('repaired_from_document_donors', 'canonical_reuse_of_document_outline')
def mismatch(b, rb):
    ow, oh, rw, rh = b[2]-b[0], b[3]-b[1], rb[2]-rb[0], rb[3]-rb[1]
    return abs(rw-ow) > max(4, 0.35*ow) or abs(rh-oh) > max(4, 0.35*oh)
summary = {}; tiles = []
for g in ('financial', 'forms', 'historical', 'mixed', 'receipts'):
    r = json.loads((Q/f'font04/local/R2a/baseline/{g}-off.pdf.json').read_text())
    src, out = pdfium.PdfDocument(str(Q/f'pdf_packaging/groups/{g}-input.pdf')), pdfium.PdfDocument(str(Q/f'font04/local/R2a/baseline/{g}-off.pdf'))
    rows = []
    for pi, pr in enumerate(r['conversion']['page_reports']):
        rec = pr['reconstruction']; ob = {o['symbol_id']: o for o in rec['observations']}
        for o in rec['occurrences']:
            if o['decision'] in APPLIED and o.get('replacement_bbox_px') and mismatch(ob[o['symbol_id']]['bbox_px'], o['replacement_bbox_px']):
                rows.append(dict(page=pi, id=o['symbol_id'], text=o['text'], decision=o['decision'], obs_bbox=ob[o['symbol_id']]['bbox_px'], repl_bbox=o['replacement_bbox_px'], similarity=o.get('similarity'), source_mask_iou=o.get('source_mask_iou')))
    applied = sum(1 for pr in r['conversion']['page_reports'] for o in pr['reconstruction']['occurrences'] if o['decision'] in APPLIED)
    summary[g] = dict(applied=applied, size_mismatch=len(rows), rows=rows)
    step = max(1, len(rows)//K)
    for row in rows[::step][:K]:
        pi = row['page']; w = r['pages'][pi]['raster_width']
        ims = []
        for doc in (src, out):
            p = doc[pi]; im = p.render(scale=w/p.get_width()).to_pil().convert('L')
            x0, y0 = min(row['obs_bbox'][0], row['repl_bbox'][0]), min(row['obs_bbox'][1], row['repl_bbox'][1])
            x1, y1 = max(row['obs_bbox'][2], row['repl_bbox'][2]), max(row['obs_bbox'][3], row['repl_bbox'][3])
            ims.append(im.crop((int(x0)-60, int(y0)-14, int(x1)+60, int(y1)+14)))
        tiles.append((f"{g} p{pi} {row['id']} '{row['text']}' {row['decision'][:9]}", ims))
(OUT/'donor-mismatch.json').write_text(json.dumps(summary, indent=1)+'\n')
Z = 2; W = max(max(i.width for i in t[1]) for t in tiles)*Z; H = max(max(i.height for i in t[1]) for t in tiles)*Z
sheet = Image.new('L', (W*2+20, len(tiles)*(H+18)), 255); d = ImageDraw.Draw(sheet)
for k, (label, ims) in enumerate(tiles):
    d.text((2, k*(H+18)), label + '   [source | scanweave default]', fill=0)
    for c, im in enumerate(ims): sheet.paste(im.resize((im.width*Z, im.height*Z), Image.NEAREST), (c*(W+20), k*(H+18)+14))
sheet.save(OUT/'donor-mismatch-sample.png')
print({g: (v['applied'], v['size_mismatch']) for g, v in summary.items()}, len(tiles), sheet.size)
