#!/usr/bin/env python3
"""Evaluator-only PDF control using the fixture's original full TrueType fonts.

Starts from a completed ScanWeave ClearScan PDF. For each emitted visible glyph,
replace F1 with a full, licensed source font retaining its original hinting and
map the existing CID/ToUnicode entry to the source font GID. Substitute the
fixture's known nominal per-character position. Invisible OCR ownership,
ActualText, raster layers, and page structure remain from the input PDF.
"""
import argparse, copy, hashlib, json, math, re
from pathlib import Path

import pikepdf
from PIL import ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
TEXT = "e8a0g6e,a; 8e0ag6! e8a0g6e,a; 8e0ag6?"
KANA = "かなカナかなカナ"
LATIN_RES = pikepdf.Name('/SourceLatin')
KANA_RES = pikepdf.Name('/SourceKana')

def parse_unicode_map(stream):
    data = stream.read_bytes().decode('latin1')
    result = {}
    for src, dst in re.findall(r'<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]+)>', data):
        raw = bytes.fromhex(dst)
        try: text = raw.decode('utf-16-be')
        except UnicodeDecodeError: continue
        result[int(src, 16)] = text
    return result

def positions_for_page(dpi, page_index, font_path):
    scale = dpi / 300
    pt = 72 / dpi
    out = {}
    font = ImageFont.truetype(font_path, round(44 * scale))
    ascent = font.getmetrics()[0]
    for row in range(2):
        x = 70 * scale
        y = (75 + 178 * row) * scale
        for j, ch in enumerate(TEXT):
            sid = f'p{page_index:02}s{row * len(TEXT) + j:04}'
            out[sid] = (ch, x, y + ascent, 44 * scale, font_path)
            x += int(font.getlength(ch)) + 7 * scale
    if page_index == 0:
        fp = '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'
        kfont = ImageFont.truetype(fp, round(30 * scale))
        x = 75 * scale
        for j, ch in enumerate(KANA):
            sid = f'p00kana{2 * len(TEXT) + j:03}'
            out[sid] = (ch, x, 710 * scale + kfont.getmetrics()[0], 30 * scale, fp)
            x += int(kfont.getlength(ch)) + 5 * scale
    return out

def toplevel_font(pdf, oldtop, font_name, source_path, unicode_map):
    src = TTFont(source_path, recalcBBoxes=False, recalcTimestamp=False)
    cmap = src.getBestCmap()
    order = src.getGlyphOrder()
    gid_by_name = {name: i for i, name in enumerate(order)}
    upem = src['head'].unitsPerEm
    olddesc = oldtop.DescendantFonts[0]
    maxcid = max(unicode_map, default=0)
    gidmap = bytearray((maxcid + 1) * 2)
    widths = []
    for cid in range(1, maxcid + 1):
        text = unicode_map.get(cid, '')
        cp = ord(text[0]) if text else None
        name = cmap.get(cp) if cp is not None else None
        gid = gid_by_name.get(name, 0) if name else 0
        gidmap[2 * cid:2 * cid + 2] = int(gid).to_bytes(2, 'big')
        adv = src['hmtx'].metrics[order[gid]][0] if gid < len(order) else upem
        widths.extend([cid, pikepdf.Array([adv * 1000.0 / upem])])
    cmap_stream = pdf.make_indirect(pdf.make_stream(bytes(gidmap)))
    font_bytes = Path(source_path).read_bytes()
    font_stream = pdf.make_indirect(pdf.make_stream(font_bytes))
    font_stream['/Length1'] = len(font_bytes)
    olddesc_copy = copy.copy(olddesc)
    desc_copy = copy.copy(olddesc.FontDescriptor)
    desc_copy['/FontName'] = font_name
    desc_copy['/FontFile2'] = font_stream
    desc_copy['/FontBBox'] = pikepdf.Array([round(v * 1000 / upem) for v in (src['head'].xMin, src['head'].yMin, src['head'].xMax, src['head'].yMax)])
    desc_copy['/Ascent'] = round(src['hhea'].ascent * 1000 / upem)
    desc_copy['/Descent'] = round(src['hhea'].descent * 1000 / upem)
    if 'OS/2' in src:
        desc_copy['/CapHeight'] = round(src['OS/2'].sCapHeight * 1000 / upem) if hasattr(src['OS/2'], 'sCapHeight') else round(src['hhea'].ascent * 1000 / upem)
    olddesc_copy['/FontDescriptor'] = pdf.make_indirect(desc_copy)
    olddesc_copy['/CIDToGIDMap'] = cmap_stream
    olddesc_copy['/W'] = pikepdf.Array(widths)
    olddesc_copy['/DW'] = round(src['hmtx'].metrics[order[0]][0] * 1000 / upem)
    olddesc_copy['/BaseFont'] = font_name
    oldtop_copy = copy.copy(oldtop)
    oldtop_copy['/BaseFont'] = font_name
    oldtop_copy['/DescendantFonts'] = pikepdf.Array([pdf.make_indirect(olddesc_copy)])
    return pdf.make_indirect(oldtop_copy), {'font_path': source_path, 'font_sha256': hashlib.sha256(font_bytes).hexdigest(), 'upem': upem, 'glyphs': len(order)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dpi', type=int)
    ap.add_argument('pdf', type=Path)
    args = ap.parse_args()
    dpi = args.dpi
    base = ROOT / f'qualification/experiments/m1g/fixture/dpi{dpi}'
    outdir = ROOT / f'qualification/clearscan_competitive/{dpi}/source-font-control'
    outdir.mkdir(parents=True, exist_ok=True)
    pdf = pikepdf.open(args.pdf)
    manifest = json.loads((base / 'input/document.json').read_text())
    truth0 = json.loads((base / 'oracle/page00.truth.json').read_text())
    default_font = truth0['font']
    latin_by_page = []
    unicode_by_page = []
    positions = []
    sid_orders = []
    for pi, page in enumerate(pdf.pages):
        truth = json.loads((base / f'oracle/page{pi:02}.truth.json').read_text())
        font_path = truth['font']
        latin_by_page.append(font_path)
        umap = parse_unicode_map(page.Resources.Font.F1.ToUnicode)
        unicode_by_page.append(umap)
        positions.append(positions_for_page(dpi, pi, font_path))
        ocr_name = manifest['pages'][pi]['ocr_page_path']
        sid_orders.append(json.loads((base / 'input' / ocr_name).read_text())['reading_order'])
    if len(set(latin_by_page)) > 2:
        raise ValueError(f'unexpected fixture font families: {set(latin_by_page)}')
    audits = []
    for pi, page in enumerate(pdf.pages):
        resources = copy.copy(page.Resources)
        fonts = copy.copy(page.Resources.Font)
        oldtop = page.Resources.Font.F1
        umap = unicode_by_page[pi]
        latin_path = latin_by_page[pi]
        latin_top, latin_meta = toplevel_font(pdf, oldtop, pikepdf.Name('/FixtureLatin'), latin_path, umap)
        fonts[ str(LATIN_RES) ] = latin_top
        if pi == 0:
            kana_path = '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'
            kana_top, kana_meta = toplevel_font(pdf, oldtop, pikepdf.Name('/FixtureKana'), kana_path, umap)
            fonts[str(KANA_RES)] = kana_top
        resources['/Font'] = fonts
        page.Resources = resources
        insns = list(pikepdf.parse_content_stream(page))
        rewritten = []
        sid_cursor = 0
        sid = None
        mode = 0
        last_tm = None
        replaced = []
        for ins in insns:
            op = str(ins.operator)
            vals = ins.operands
            if op == 'BDC' and len(vals) > 1 and isinstance(vals[1], pikepdf.Dictionary) and '/ActualText' in vals[1]:
                sid_order = sid_orders[pi]
                if sid_cursor < len(sid_order): sid = sid_order[sid_cursor]; sid_cursor += 1
            elif op == 'Tr':
                mode = int(vals[0])
            if op == 'Tm':
                last_tm = len(rewritten)
            if op == 'Tj' and mode == 0 and sid in positions[pi]:
                ch, x, baseline, size, fp = positions[pi][sid]
                res = KANA_RES if pi == 0 and ch in KANA else LATIN_RES
                pt = 72 / dpi
                matrix = pikepdf.ContentStreamInstruction(
                    [size * pt, 0, 0, size * pt, x * pt, (900 * (dpi / 300) - baseline) * pt],
                    pikepdf.Operator('Tm'))
                if last_tm is None:
                    rewritten.append(matrix)
                    last_tm = len(rewritten) - 1
                else:
                    rewritten[last_tm] = matrix
                rewritten.append(pikepdf.ContentStreamInstruction([res, 1], pikepdf.Operator('Tf')))
                rewritten.append(ins)
                rewritten.append(pikepdf.ContentStreamInstruction([pikepdf.Name('/F1'), 1], pikepdf.Operator('Tf')))
                replaced.append({'span_id': sid, 'char': ch, 'cid': int.from_bytes(bytes(vals[0]), 'big'), 'font': str(res)})
                last_tm = None
            else:
                rewritten.append(ins)
        page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(rewritten))
        audits.append({'page': pi, 'source_latin_font': latin_meta, 'replaced_visible_instances': replaced, 'visible_replacement_count': len(replaced), 'source_kana_font': kana_meta if pi == 0 else None})
    outfile = outdir / 'oracle-source-font.pdf'
    pdf.save(outfile)
    (outdir / 'audit.json').write_text(json.dumps(audits, indent=2, ensure_ascii=False) + '\n')
    print(outfile)

if __name__ == '__main__': main()
