#!/usr/bin/env python3
"""Bounded contracts for qualification-only HIGH maintenance changes.

Historical command scripts execute at import. Load their actual definitions or
constant assignments without running their corpus-writing top-level programs.
Integration equality against 0816d8a is separately recorded in the wave report.
"""
import ast
from contextlib import chdir
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pikepdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def definitions(relative):
    path = ROOT / 'qualification' / relative
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body if isinstance(
        node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))]
    namespace = {'__file__': str(path), '__name__': 'wave1_control'}
    exec(compile(tree, str(path), 'exec'), namespace)
    return namespace


def run_script(relative, scratch):
    """Execute an actual historical entry point with only its output tree relocated."""
    path = ROOT / 'qualification' / relative
    relocated = scratch / 'qualification' / relative
    relocated.parent.mkdir(parents=True, exist_ok=True)
    namespace = {'__file__': str(relocated), '__name__': '__main__'}
    with chdir(scratch):
        exec(compile(path.read_text(), str(path), 'exec'), namespace)
    return namespace


def small_pdf(image=None):
    """A real one-page PDF, optionally with one lossless RGB image resource."""
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(72, 72) if image is None else (4.8, 3.84))
    if image is not None:
        stream = pdf.make_stream(image.tobytes())
        stream.update({'/Type': pikepdf.Name.XObject, '/Subtype': pikepdf.Name.Image,
                       '/Width': image.width, '/Height': image.height,
                       '/ColorSpace': pikepdf.Name.DeviceRGB, '/BitsPerComponent': 8})
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=stream))
        page.Contents = pdf.make_stream(b'q 4.8 0 0 3.84 0 0 cm /Im0 Do Q')
    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()


class HighWave1Tests(unittest.TestCase):
    def test_local_constants_preserve_every_literal_value(self):
        contracts = json.loads((ROOT / 'docs/maintenance/sonar-high-wave1-literal-contracts.json').read_text())
        for contract in contracts:
            path = ROOT / contract['file']
            tree = ast.parse(path.read_text())
            tree.body = [n for n in tree.body if isinstance(n, ast.Assign)
                         and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                         and n.targets[0].id in contract['constants']]
            namespace = {}
            exec(compile(tree, str(path), 'exec'), namespace)
            for name, expected in contract['constants'].items():
                with self.subTest(file=contract['file'], constant=name):
                    if isinstance(expected, dict):
                        expected = bytes.fromhex(expected['bytes_hex'])
                    self.assertEqual(namespace[name], expected)

    def test_grid_search_preserves_first_tie_and_empty_candidates(self):
        ns = definitions('experiments/m1c_r3/alignment.py')
        original = ((3., 4.), 0.)
        image = np.zeros((8, 8), dtype=np.float32)
        self.assertEqual(ns['best_grid_shift'](image, image, [-1, 0, 1], [-1, 0, 1], *original), original)
        self.assertEqual(ns['best_grid_shift'](image, image, [], [], *original), original)
        with patch.dict(ns, mse=lambda *_: 1.):
            self.assertEqual(ns['best_grid_shift'](image, image, [2, 1], [4, 3], (0, 0), 2.), ((2., 4.), 1.))
        with patch.dict(ns, mse=lambda *_: float('nan')):
            self.assertEqual(ns['best_grid_shift'](image, image, [0], [0], *original), original)

    def test_alignment_identity_and_shift(self):
        ns = definitions('experiments/m1c_r3/alignment.py')
        image = np.zeros((15, 15), dtype=np.float32)
        image[4:10, 5:8] = 1
        # Preserve the existing subpixel/uint8 sampling phase, including its
        # tiny nonzero refinement; idealized zero-shift output is not baseline.
        expected = image.copy()
        expected[4:10, 5] = np.float32(254 / 255)
        aligned, sx, sy, error = ns['align'](image, image)
        np.testing.assert_array_equal(aligned, expected)
        self.assertEqual((sx, sy, error), (-2.234504968305603e-09, 0., 4.1009863593899354e-07))
        moved = ns['shift_arr'](image, 1, -1)
        aligned, sx, sy, error = ns['align'](moved, image)
        np.testing.assert_array_equal(aligned, expected)
        self.assertEqual((sx, sy, error), (-1.000000002234505, 1., 4.1009863593899354e-07))
        self.assertEqual(ns['refine_x'](image*0, image*0, 0, 0), 0.)
        self.assertEqual(ns['refine_y'](image*0, image*0, 0, 0), 0.)

    def test_ridge_counts_preserve_dark_and_light_thin_marks(self):
        ns = definitions('tonal_raster/compare.py')
        for value in [0, 255]:
            with self.subTest(value=value):
                image = np.full((7, 9, 3), 127, dtype=np.uint8)
                image[3, 1:8] = value
                same = ns['stats'](image, image)
                self.assertEqual(same['lost_ridges'], 0)
                self.assertGreater(same['dark_and_light_ridge_tests'], 0)
                erased = ns['stats'](image, np.full_like(image, 127))
                self.assertGreater(erased['lost_ridges'], 0)

    def test_tonal_chunk_boundaries_and_identity(self):
        ns = definitions('tonal_raster/compare.py')
        for height in [2, 127, 128, 129, 257]:
            with self.subTest(height=height):
                image = np.random.default_rng(10).integers(0, 256, (height, 7, 3), dtype=np.uint8)
                with np.errstate(invalid='ignore', divide='ignore'):
                    result = ns['stats'](image, image)
                for key in ['mae', 'max_channel_error', 'changed_fraction', 'lost_ridges', 'gradient_error_x']:
                    self.assertEqual(result[key], 0)
                if height > 1:
                    self.assertEqual(result['gradient_error_y'], 0)

    def test_one_row_tonal_image_preserves_existing_error(self):
        ns = definitions('tonal_raster/compare.py')
        image = np.zeros((1, 7, 3), dtype=np.uint8)
        with self.assertRaises(ZeroDivisionError):
            ns['stats'](image, image)

    def test_family_statistics_keep_unicode_sort_and_empty_input(self):
        ns = definitions('clearscan_competitive/measure_source_font_control.py')
        self.assertEqual(ns['family_statistics']([], None), {})
        rows = [{'text': ch, 'value': value} for ch, value in [('カ', 3.), ('e', 1.), ('e', 2.)]]
        calls = []
        def stats(key, subset):
            calls.append((key, [r['value'] for r in subset]))
            return {'mean': float(np.mean([r['value'] for r in subset]))}
        result = ns['family_statistics'](rows, stats)
        self.assertEqual(list(result), ['e', 'カ'])
        self.assertEqual(result['e']['source'], 1.5)
        self.assertEqual(result['e']['n'], 2)
        self.assertEqual(calls[0], ('source', [1., 2.]))

    def test_open_contour_defers_closure_to_pdf_fill(self):
        ns = definitions('clearscan_contours/font_render_control.py')
        pen = ns['Pen'](None)
        pen.moveTo((1, 2)); pen.lineTo((3, 4)); pen.endPath()
        self.assertEqual(pen.ops, ['1 2 m', '3 4 l'])
        pen.moveTo((0, 0)); pen.qCurveTo((3, 6), (6, 0)); pen.closePath()
        self.assertEqual(pen.ops[-1], ' h')
        self.assertIn('c', pen.ops[-2])

    def test_sample_crop_names_and_pixels(self):
        ns = definitions('clearscan_product/measure.py')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ['oracle', 'input', 'poppler', 'crops']:
                (root/name).mkdir()
            image = np.arange(256, dtype=np.uint8).reshape(16, 16)
            for name in ['oracle/page00.png', 'input/scan.png', 'poppler/page-1.png']:
                Image.fromarray(image).save(root/name)
            (root/'oracle/page00.truth.json').write_text(json.dumps({'records': [{'id': 'g', 'bbox': [1, 2, 9, 10]}]}))
            manifest = {'pages': [{'page_id': 'page', 'source_id': 'scan'}], 'sources': [{'source_id': 'scan', 'asset_path': 'scan.png'}]}
            ns['write_sample_crops']({'e': {'page': 'page', 'symbol_id': 'g'}}, manifest, root/'oracle', root/'input', root/'poppler', [image], root/'crops')
            files = list((root/'crops').iterdir())
            self.assertEqual([p.name for p in files], ['0065-e.png'])
            with Image.open(files[0]) as result:
                self.assertEqual(result.size, (104, 528))
                np.testing.assert_array_equal(np.asarray(result)[20:132], np.repeat(np.repeat(image[:14, :13], 8, 0), 8, 1))

    def test_window_search_handles_unrelated_match_and_no_match(self):
        source = (ROOT/'qualification/clearscan_competitive/reference-runner.sh').read_text()
        function = source[source.index('input_wid() {'):source.index('# dismiss the 3-button')]
        with tempfile.TemporaryDirectory() as temporary:
            tool = Path(temporary)/'xdotool-control'
            tool.write_text('#!/bin/bash\nif [[ "$1" == search ]]; then printf "1\\n2\\n"; elif [[ "$2" == 1 ]]; then echo "Adobe Acrobat Pro"; else echo "$TEST_TITLE"; fi\n')
            tool.chmod(0o700)
            script = 'XDO="$1"\nTEST_TITLE="$2"\nexport TEST_TITLE\n'+function+'\ninput_wid\n'
            for title, status, stdout in [('input.pdf - Adobe Acrobat Pro', 0, '2\n'), ('other.pdf', 1, '')]:
                with self.subTest(title=title):
                    result = subprocess.run(['bash', '-c', script, 'runner-test', str(tool), title], capture_output=True, text=True)
                    self.assertEqual((result.returncode, result.stdout), (status, stdout))


    def test_real_result_packager_writes_exact_names_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root/'qualification/real_convergence'
            previous = root/'qualification/pdf_packaging'
            current.mkdir(parents=True); previous.mkdir(parents=True)
            resources = dict(pdf_bytes=101, raster_bytes=50, font_bytes=20,
                             content_bytes=10, overhead_bytes=21)
            measurement = [{'pdf': 'qualification/real_convergence/collections/case.pdf',
                            'resources': resources, 'pages': [{'id': 'case', 'funnel': {'ocr_chars': 3}}],
                            'native': [{'class': 'whole_page', 'bytes': 50, 'histogram': [1]+[0]*254+[1]}]}]
            (current/'measurements.json').write_text(json.dumps(measurement))
            (previous/'group-measurements.json').write_text(json.dumps([{'group': 'case', 'arm': 'scanweave', 'resources': resources}]))
            (current/'outline-inventory.json').write_text(json.dumps([{'pdf': 'qualification/real_convergence/collections/case.pdf', 'pages': [{'draws': 2, 'unique_gids': 1}], 'unique_painted_gids': 1}]))
            (current/'starting-head.txt').write_text('0816d8a\n')
            pdf = small_pdf()
            expected = set()
            for directory in [current/'outputs', current/'collections', current/'300', current/'600', previous/'groups']:
                directory.mkdir(); file = directory/'case.pdf'; file.write_bytes(pdf)
                expected.add(str(file.relative_to(root)))
            run_script('real_convergence/package_results.py', root)
            manifest = json.loads((current/'run-manifest.json').read_text())
            self.assertEqual({r['path'] for r in manifest['artifacts']}, expected)
            self.assertTrue(all(r['sha256'] == hashlib.sha256(pdf).hexdigest() and r['bytes'] == len(pdf) for r in manifest['artifacts']))
            totals = json.loads((current/'totals.json').read_text())
            self.assertEqual(totals['pdf_bytes'], 101)
            self.assertEqual(totals['strict_bitonal_objects'], {'whole_page': 1})
            self.assertEqual(totals['actual_visible_draws'], 2)
            with (current/'scorecard.csv').open() as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([r['arm'] for r in rows], ['previous_scanweave', 'updated_scanweave'])
            self.assertEqual(json.loads((current/'page-results.json').read_text())[0]['id'], 'case')

    def test_outline_inventory_runs_on_real_pdf_in_all_glob_locations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); base = root/'qualification/tonal_raster'
            pdf = small_pdf()
            for name in ['collections', 'baseline-collections', '300', '600', 'control-runs']:
                directory = base/name; directory.mkdir(parents=True)
                (directory/('final.pdf' if name in ['300', '600'] else 'tiny.pdf')).write_bytes(pdf)
            run_script('tonal_raster/outline_inventory.py', root)
            rows = json.loads((base/'outline-inventory.json').read_text())
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(r['visible_glyph_draws'] == 0 and r['pages'] == [{'draws': 0, 'unique_gids': 0}] for r in rows))
            self.assertEqual({Path(r['pdf']).parent.name for r in rows}, {'collections', 'baseline-collections', '300', '600', 'control-runs'})

    def test_tonal_full_and_resumed_report_paths_with_both_renderers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); base = root/'qualification/tonal_raster'
            base.mkdir(parents=True)
            (base/'controls.json').write_text(json.dumps({'regions': {'tiny': [['mark', 0, 0, 1, 1]]}}))
            image = Image.new('RGB', (20, 16), 'white')
            image.putpixel((7, 5), (100, 100, 100))
            pdf = small_pdf(image)
            for arm in ['baseline', 'q98', 'q100']:
                directory = base/arm; directory.mkdir()
                (directory/'tiny.pdf').write_bytes(pdf)
                (directory/'tiny.pdf.json').write_text(json.dumps({'conversion': {'page_reports': [{'occurrences': []}]}}))
            run_script('tonal_raster/compare.py', root)
            first = (base/'comparison.json').read_bytes()
            rows = json.loads(first)
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]['regions']), 2)
            for arm in ['q98', 'q100']:
                for renderer in ['pdfium', 'poppler']:
                    self.assertEqual(rows[0]['arms'][arm][renderer]['mae'], 0.)
                    self.assertEqual(rows[0]['arms'][arm][renderer]['changed_fraction'], 0.)
                    self.assertEqual(rows[0]['arms'][arm][renderer]['lost_ridges'], 0)
                    self.assertTrue((base/'renders'/arm/f'tiny-{renderer}.png').exists())
            run_script('tonal_raster/compare.py', root)
            self.assertEqual((base/'comparison.json').read_bytes(), first)


if __name__ == '__main__':
    unittest.main()
