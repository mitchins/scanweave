"""Shared painted-resource auditor; historical entry points supply their roots.

This preserves the original auditor's scope and assumptions. In particular,
resource classification requires its page report and does not divide mixed
encoded streams into inferred byte shares.
"""
import argparse
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import io
import json
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
import pikepdf


@dataclass
class AuditState:
    counts: Counter = field(default_factory=Counter)
    paths: Counter = field(default_factory=Counter)
    rows: list = field(default_factory=list)
    images: dict = field(default_factory=dict)
    assignments: list = field(default_factory=list)
    ttf_cache: dict = field(default_factory=dict)
    cff_cache: dict = field(default_factory=dict)
    shown_codes: int = 0


class PageContext:
    def __init__(self, page, index, dpi, root, report):
        self.page, self.index, self.dpi, self.root = page, index, dpi, root
        self.fonts = page.Resources.get('/Font', {})
        self.mode, self.matrix, self.font, self.symbol, self.cursor = 0, None, None, None, 0
        self.report = report['page_reports'][index] if report else None
        self.records = {r['symbol_id']: r for r in self.report['reconstruction']['occurrences']} if self.report else {}
        self.ordered = json.loads((root / f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page{index:02}.ocr.json').read_text())['reading_order'] if self.report else []
        self.truth = read_truth(root, dpi, index) if self.report else None
        self.truthmap = {r['id']: r for r in self.truth['records']} if self.truth else {}


def read_truth(root, dpi, page):
    return json.loads((root / f'qualification/experiments/m1g/fixture/dpi{dpi}/oracle/page{page:02}.truth.json').read_text())


def font_program(font, state):
    desc = font.get('/DescendantFonts', [font])[0]
    descriptor = desc.get('/FontDescriptor', {})
    stream = descriptor.get('/FontFile2')
    font_key = tuple(font.objgen)
    ttf, cff = None, None
    if stream is not None:
        key = tuple(stream.objgen)
        if key not in state.ttf_cache:
            state.ttf_cache[key] = TTFont(io.BytesIO(stream.read_bytes()))
        ttf = state.ttf_cache[key]
    elif descriptor.get('/FontFile3') is not None:
        from fontTools.cffLib import CFFFontSet
        stream = descriptor.FontFile3
        key = tuple(stream.objgen)
        if key not in state.cff_cache:
            fonts = CFFFontSet()
            fonts.decompile(io.BytesIO(stream.read_bytes()), None)
            state.cff_cache[key] = fonts[fonts.fontNames[0]]
        cff = state.cff_cache[key]
    program_hash = hashlib.sha256(stream.read_bytes()).hexdigest() if stream is not None else str(font_key)
    return desc, font_key, ttf, cff, program_hash


def ttf_outline(row, ttf, gid, context, state):
    name = ttf.getGlyphOrder()[gid]
    pen = RecordingPen()
    ttf.getGlyphSet()[name].draw(pen)
    digest = hashlib.sha256(repr(pen.value).encode()).hexdigest()
    state.paths[digest] += 1
    row['outline_hash'] = digest
    glyph = ttf['glyf'][name]
    if glyph.numberOfContours and context.matrix:
        a, b, c, d, e, f = context.matrix
        u = ttf['head'].unitsPerEm
        dpi = context.dpi
        row['bbox_px'] = [(e+a*glyph.xMin/u)*dpi/72,
                          (float(context.page.MediaBox[3])-f-d*glyph.yMax/u)*dpi/72,
                          (e+a*glyph.xMax/u)*dpi/72,
                          (float(context.page.MediaBox[3])-f-d*glyph.yMin/u)*dpi/72]
        if context.symbol in context.truthmap:
            truth = context.truthmap[context.symbol]
            pad = (4 if ord(truth['text'][0]) > 127 else 5)*dpi/300
            bb = truth['bbox']
            target = [bb[0]+pad, bb[1]+pad, bb[2]-pad, bb[3]-pad]
            bounds = row['bbox_px']
            row['design_vs_hinted_truth_delta_px'] = [bounds[j]-target[j] for j in range(4)]
    return pen


def glyph_outline(row, ttf, cff, cid, gid, context, state):
    pen = None
    if ttf is not None:
        pen = ttf_outline(row, ttf, gid, context, state)
    if cff is not None:
        name = f'cid{cid:05d}'
        pen = RecordingPen()
        cff.CharStrings[name if name in cff.CharStrings.charStrings else '.notdef'].draw(pen)
        digest = hashlib.sha256(repr(pen.value).encode()).hexdigest()
        state.paths[digest] += 1
        row['outline_hash'] = digest
    return bool(pen.value) if ttf is not None or cff is not None else True


def record_assignment(context, state):
    if not context.report or context.symbol not in context.records:
        return
    record = context.records[context.symbol]
    prototype = record.get('prototype_id')
    geometry = next((g for g in context.report['reconstruction'].get('canonical_geometry', [])
                     if g['prototype_id'] == prototype), None)
    if geometry:
        symbol = geometry['witness_symbol_id'].split(':')[-1]
        witness_page = int(symbol[1:3])
        truth = read_truth(context.root, context.dpi, witness_page)
        witness = next(t for t in truth['records'] if t['id'] == symbol)
        state.assignments.append({'page': context.index, 'symbol': context.symbol,
                                  'text': record['text'], 'witness': symbol,
                                  'witness_text': witness['text'],
                                  'same_identity': record['text'] == witness['text'],
                                  'same_typeface': context.truth['font'] == truth['font'],
                                  'prototype': prototype})


def record_code(data, context, state, program):
    desc, font_key, ttf, cff, program_hash = program
    cid = int.from_bytes(data, 'big')
    gid = cid
    mapping = desc.get('/CIDToGIDMap')
    if isinstance(mapping, pikepdf.Stream):
        gid = int.from_bytes(mapping.read_bytes()[cid*2:cid*2+2], 'big')
    state.shown_codes += 1
    key = f'{program_hash}:{gid}'
    row = {'page': context.index, 'symbol': context.symbol, 'cid': cid,
           'gid': gid, 'font': font_key, 'matrix': context.matrix}
    if not glyph_outline(row, ttf, cff, cid, gid, context, state):
        if row.get('outline_hash'):
            state.paths[row['outline_hash']] -= 1
        return
    state.counts[key] += 1
    state.rows.append(row)
    record_assignment(context, state)


def show_text(operator, operands, context, state):
    strings = [operands[0]] if operator == 'Tj' else [s for s in operands[0] if isinstance(s, pikepdf.String)]
    program = font_program(context.font, state)
    for string in strings:
        data = bytes(string)
        step = 2 if context.font.get('/Subtype') == '/Type0' else 1
        for i in range(0, len(data), step):
            record_code(data[i:i+step], context, state, program)


def visit_instruction(instruction, context, state):
    operator, values = str(instruction.operator), instruction.operands
    if operator == 'Tr':
        context.mode = int(values[0])
    elif operator == 'Tf':
        context.font = context.fonts[str(values[0])]
    elif operator == 'Tm':
        context.matrix = list(map(float, values))
    elif operator == 'BDC' and len(values) > 1 and isinstance(values[1], pikepdf.Dictionary) and '/ActualText' in values[1] and context.report:
        context.symbol = context.ordered[context.cursor]
        context.cursor += 1
    elif operator in ('Tj', 'TJ') and context.mode in (0, 1, 2) and context.font is not None:
        show_text(operator, values, context, state)


def classify_images(context, state):
    if not context.report:
        return
    patches = context.report['patches']
    resources = [v for k, v in sorted(context.page.Resources.get('/XObject', {}).items(),
                                     key=lambda kv: int(str(kv[0]).removeprefix('/Im')))]
    # Retain the original report-only, first-object-reference byte accounting.
    for patch, obj in zip(patches, resources):
        if obj.get('/Subtype') != '/Image':
            continue
        key = tuple(obj.objgen)
        bb, width, height = patch['bbox_px'], patch['w'], patch['h']
        kind = 'native_fallback_artwork_unknown'
        if bb[0] == 0 and bb[1] == 0 and width < bb[2] and height < bb[3]:
            kind = 'residual_background'
        if key not in state.images:
            state.images[key] = {'bytes': len(obj.read_raw_bytes()), 'class': kind,
                                 'bbox': bb, 'dimensions': [width, height],
                                 'filter': str(obj.get('/Filter'))}


def summarize(state):
    classes = Counter()
    for image in state.images.values():
        classes[image['class']] += image['bytes']
    paths = Counter({k: v for k, v in state.paths.items() if v > 0})
    return {'shown_character_codes': state.shown_codes,
            'painted_occurrences': len(state.rows), 'used_font_gids': len(state.counts),
            'distinct_painted_outline_hashes': len(paths) if paths else None,
            'outline_reuse': dict(paths), 'gid_reuse': dict(state.counts),
            'placements': state.rows, 'resource_bytes_by_class': dict(classes),
            'resource_classes': list(state.images.values()), 'assignments': state.assignments,
            'wrong_witness_identity': sum(not r['same_identity'] for r in state.assignments),
            'wrong_witness_typeface': sum(not r['same_typeface'] for r in state.assignments),
            'scope': 'Assignment checks known source identity/style of selected witnesses, not a complete visual-identity classifier. Byte classes cannot split already encoded mixed-content streams.'}


def audit(dpi, arm, path, report_path=None, *, root):
    document = pikepdf.open(path)
    state = AuditState()
    report = json.loads(report_path.read_text()) if report_path else None
    for index, page in enumerate(document.pages):
        context = PageContext(page, index, dpi, root, report)
        for instruction in pikepdf.parse_content_stream(page):
            visit_instruction(instruction, context, state)
        classify_images(context, state)
    return summarize(state)


def main(base, root):
    parser = argparse.ArgumentParser()
    parser.add_argument('dpi', type=int)
    parser.add_argument('arm')
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.dpi, args.arm, args.pdf, args.report, root=root)
    output = base / str(args.dpi) / args.arm / 'audit.json'
    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(json.dumps(result, indent=2))
    print(args.dpi, args.arm, {k: v for k, v in result.items()
                             if k not in ['placements', 'assignments', 'gid_reuse', 'outline_reuse', 'resource_classes']})
