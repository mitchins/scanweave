#!/usr/bin/env python3
"""PDF-backed controls for the shared auditor and stable product sampling."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
import pikepdf

from clearscan_audit import audit
from clearscan_product.measure import first_replaced_samples

ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINTS = ('clearscan_background', 'clearscan_competitive',
                'clearscan_contours', 'clearscan_typography')


def font_program_bytes(cff=False):
    names = ['.notdef', 'cid00001', 'empty']
    builder = FontBuilder(1000, isTTF=not cff)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({65: 'cid00001'})
    builder.setupHorizontalMetrics({name: (200, 0) for name in names})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({'familyName': 'AuditControl', 'styleName': 'Regular'})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    glyphs = {}
    for name in names:
        pen = T2CharStringPen(200, None) if cff else TTGlyphPen(None)
        if name == 'cid00001':
            pen.moveTo((0, 0))
            pen.lineTo((100, 0))
            pen.lineTo((50, 200))
            pen.closePath()
        glyphs[name] = pen.getCharString() if cff else pen.glyph()
    if cff:
        builder.setupCFF('AuditControl', {}, glyphs, {})
        return builder.font['CFF '].compile(builder.font)
    builder.setupGlyf(glyphs)
    buffer = io.BytesIO()
    builder.save(buffer)
    return buffer.getvalue()


def fixture(root, cff=False):
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(72, 72))
    descriptor = pikepdf.Dictionary()
    descriptor['/FontFile3' if cff else '/FontFile2'] = pdf.make_stream(font_program_bytes(cff))
    descendant = pikepdf.Dictionary(FontDescriptor=descriptor,
                                    CIDToGIDMap=pdf.make_stream(b'\0\0\0\1\0\2'))
    font = pdf.make_indirect(pikepdf.Dictionary(Subtype=pikepdf.Name.Type0,
                                               DescendantFonts=[descendant]))
    first = pdf.make_stream(b'\xc0')
    first.Subtype = pikepdf.Name.Image
    second = pdf.make_stream(b'\xc0\xbf\xc0')
    second.Subtype = pikepdf.Name.Image
    page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font),
                                        XObject=pikepdf.Dictionary(Im0=first, Im1=first, Im2=second))
    page.Contents = pdf.make_stream(
        b'BT /F1 10 Tf 1 0 0 1 1 2 Tm '
        b'/Span << /ActualText (A) >> BDC <0001> Tj EMC '
        b'/Span << /ActualText (A) >> BDC [<0001> -10 <0002>] TJ EMC '
        b'3 Tr <0001> Tj ET')
    path = root / 'input.pdf'
    pdf.save(path)
    pdf.close()
    base = root / 'qualification/experiments/m1g/fixture/dpi300'
    (base / 'input').mkdir(parents=True)
    (base / 'oracle').mkdir()
    (base / 'input/page00.ocr.json').write_text(json.dumps({'reading_order': ['g00000', 'g00001']}))
    truth = {'font': 'Control', 'records': [
        {'id': 'g00000', 'text': 'A', 'bbox': [0, 0, 15, 15]},
        {'id': 'g00001', 'text': 'A', 'bbox': [0, 0, 15, 15]}]}
    (base / 'oracle/page00.truth.json').write_text(json.dumps(truth))
    geometry = [{'prototype_id': 7, 'witness_symbol_id': 'doc:g00000'}]
    occurrences = [{'symbol_id': symbol, 'text': 'A', 'prototype_id': 7}
                   for symbol in ['g00000', 'g00001']]
    patches = [dict(bbox_px=[0, 0, 300, 300], w=1, h=1),
               dict(bbox_px=[1, 1, 2, 2], w=1, h=1),
               dict(bbox_px=[2, 2, 3, 3], w=1, h=1)]
    report = root / 'report.json'
    report.write_text(json.dumps({'page_reports': [dict(
        reconstruction=dict(occurrences=occurrences, canonical_geometry=geometry), patches=patches)]}))
    return path, report, base


class SharedAuditorTests(unittest.TestCase):
    def test_ttf_codes_empty_outlines_ownership_bbox_and_shared_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, report, _ = fixture(root)
            result = audit(300, 'control', pdf, report, root=root)
            self.assertEqual(result['shown_character_codes'], 3)
            self.assertEqual(result['painted_occurrences'], 2)
            self.assertEqual(result['used_font_gids'], 1)
            self.assertEqual(result['distinct_painted_outline_hashes'], 1)
            self.assertEqual(list(result['outline_reuse'].values()), [2])
            self.assertEqual([r['symbol'] for r in result['placements']], ['g00000', 'g00001'])
            row = result['placements'][0]
            self.assertLess(list(row).index('outline_hash'), list(row).index('bbox_px'))
            self.assertEqual(row['bbox_px'], [300/72, 69.8*300/72, 1.1*300/72, 70*300/72])
            self.assertEqual(len(result['assignments']), 2)
            self.assertEqual(result['wrong_witness_identity'], 0)
            self.assertEqual(result['wrong_witness_typeface'], 0)
            self.assertEqual([r['class'] for r in result['resource_classes']],
                             ['residual_background', 'native_fallback_artwork_unknown'])
            self.assertEqual(sum(result['resource_bytes_by_class'].values()),
                             sum(r['bytes'] for r in result['resource_classes']))
            self.assertEqual(len(result['resource_classes']), 2)  # Shared Im1 is not counted twice.

    def test_cff_and_absent_reports_keep_original_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, _, _ = fixture(root, cff=True)
            result = audit(300, 'control', pdf, root=root)
            self.assertEqual(result['shown_character_codes'], 3)
            self.assertEqual(result['painted_occurrences'], 2)
            self.assertEqual(result['distinct_painted_outline_hashes'], 1)
            self.assertNotIn('bbox_px', result['placements'][0])
            self.assertIsNone(result['placements'][0]['symbol'])
            self.assertEqual(result['assignments'], [])
            self.assertEqual(result['resource_classes'], [])  # No invented report-free classification.

    def test_witness_mismatch_and_missing_geometry_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, report, base = fixture(root)
            witness = {'font': 'Alternate', 'records': [{'id': 'g01000', 'text': 'B'}]}
            (base / 'oracle/page01.truth.json').write_text(json.dumps(witness))
            data = json.loads(report.read_text())
            reconstruction = data['page_reports'][0]['reconstruction']
            reconstruction['canonical_geometry'][0]['witness_symbol_id'] = 'doc:g01000'
            report.write_text(json.dumps(data))
            result = audit(300, 'control', pdf, report, root=root)
            self.assertEqual((result['wrong_witness_identity'], result['wrong_witness_typeface']), (2, 2))
            reconstruction['canonical_geometry'] = []
            report.write_text(json.dumps(data))
            self.assertEqual(audit(300, 'control', pdf, report, root=root)['assignments'], [])

    def test_all_historic_command_entry_points_write_identical_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, _, _ = fixture(root)
            hashes = []
            for name in ENTRY_POINTS:
                destination = root / name
                with patch('sys.argv', ['audit.py', '300', str(destination), str(pdf)]), redirect_stdout(io.StringIO()):
                    runpy.run_path(str(ROOT / 'qualification' / name / 'audit.py'), run_name='__main__')
                output = (destination / 'audit.json').read_bytes()
                hashes.append(hashlib.sha256(output).hexdigest())
                self.assertEqual(json.loads(output)['painted_occurrences'], 2)
            self.assertEqual(len(set(hashes)), 1)

    def test_blank_pdf_and_nonembedded_font_keep_original_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = pikepdf.new()
            page = pdf.add_blank_page(page_size=(72, 72))
            path = root / 'blank.pdf'
            pdf.save(path)
            self.assertIsNone(audit(300, 'control', path, root=root)['distinct_painted_outline_hashes'])
            page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(
                F1=pdf.make_indirect(pikepdf.Dictionary(Subtype=pikepdf.Name.Type1))))
            page.Contents = pdf.make_stream(b'BT /F1 10 Tf (A) Tj ET')
            pdf.save(path)
            pdf.close()
            result = audit(300, 'control', path, root=root)
            self.assertEqual(result['painted_occurrences'], 1)
            self.assertIsNone(result['distinct_painted_outline_hashes'])

    def test_product_samples_keep_first_replaced_character_and_order(self):
        first = {'text': 'e', 'replaced': True, 'symbol_id': 'first'}
        rows = [{'text': 'a', 'replaced': False}, first,
                {'text': 'e', 'replaced': True, 'symbol_id': 'second'},
                {'text': 'カ', 'replaced': True}]
        result = first_replaced_samples(rows)
        self.assertEqual(list(result), ['e', 'カ'])
        self.assertIs(result['e'], first)
        self.assertEqual(first_replaced_samples([]), {})


if __name__ == '__main__':
    unittest.main()
