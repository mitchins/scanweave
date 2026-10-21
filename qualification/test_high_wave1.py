#!/usr/bin/env python3
"""Bounded contracts for qualification-only HIGH maintenance changes.

Historical command scripts execute at import. Load their actual definitions or
constant assignments without running their corpus-writing top-level programs.
Integration equality against 0816d8a is separately recorded in the wave report.
"""
import ast
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
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


if __name__ == '__main__':
    unittest.main()
