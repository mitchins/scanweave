"""Contracts for deterministic source crops, split isolation and oracle separation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pikepdf
from PIL import Image

from font01 import benchmark as b


class FontBenchmarkTests(unittest.TestCase):
    def test_installed_manifest_and_family_isolation(self):
        faces = b.font_manifest(b.installed_faces())
        self.assertEqual(len(faces), 23)
        b.split_isolation(faces)
        self.assertTrue(all(len(f['sha256']) == 64 for f in faces))
        with self.assertRaisesRegex(ValueError, 'crosses splits'):
            b.split_isolation([faces[0], dict(faces[0], split='test')])

    def test_missing_asset_is_explicit(self):
        with self.assertRaises(FileNotFoundError):
            b.font_manifest([dict(path='/tmp/no-font-font01.ttf')])

    def test_line_schedule_is_not_a_face_position_key(self):
        rng = np.random.default_rng(19)
        first, second = b.page_schedule(8, rng), b.page_schedule(8, rng)
        self.assertNotEqual(first, second)
        self.assertEqual(sorted(first), sorted(second))
        self.assertEqual(len(set(first)), 32)

    def test_rare_punctuation_damage_is_not_a_dpi_key(self):
        schedules = [b.page_schedule(8, np.random.default_rng(7 + i)) for i in range(3)]
        plan = b.plan_damage(8, schedules, 10301)
        signatures = []
        for face in range(8):
            locations = []
            for page, schedule in enumerate(schedules):
                line = schedule.index((face, 1))
                locations.append((page, line, b.PHRASES[1].index('!')))
            values = [plan[location] for location in locations]
            self.assertIn(0, values)
            self.assertTrue(any(value > 0 for value in values))
            signatures.append(tuple(values))
        self.assertGreater(len(set(signatures)), 1)
        self.assertGreater(len({values[0] for values in signatures}), 1)

    def test_grayscale_geometry_and_structured_damage(self):
        path = b.installed_faces()[0]['path']
        image, metrics = b.render_glyph(path, 'e', 12, 300)
        self.assertGreater(metrics['advance'], 0)
        pristine, transform = b.geometry(image, np.random.default_rng(1))
        self.assertEqual(len(transform['inverse_affine']), 6)
        clean, damage = b.degrade(pristine, 0, np.random.default_rng(2))
        self.assertEqual(clean.tobytes(), pristine.tobytes())
        self.assertFalse(np.asarray(damage).any())
        for severity in range(1, 5):
            scan, damage = b.degrade(pristine, severity, np.random.default_rng(3))
            self.assertEqual(scan.size, pristine.size)
            self.assertNotEqual(scan.tobytes(), pristine.tobytes())
            if severity >= 2:
                self.assertTrue(np.asarray(damage).any())
        with self.assertRaises(ValueError):
            b.degrade(pristine, 5, np.random.default_rng(2))
        self.assertFalse(b.structured_loss(np.zeros((3, 3)), 4, np.random.default_rng(2)).any())

    def test_documents_are_deterministic_and_crops_are_source_bound(self):
        faces = b.font_manifest(b.installed_faces()[:1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = b.generate_document(root / 'a', faces, 42, dpis=(200,))
            second = b.generate_document(root / 'b', faces, 42, dpis=(200,))
            self.assertEqual(first, second)
            public = [json.loads(line) for line in (root/'a/observations.jsonl').read_text().splitlines()]
            labels = [json.loads(line) for line in (root/'a/oracle/labels.jsonl').read_text().splitlines()]
            self.assertEqual(len(public), len(labels))
            self.assertEqual({row['severity'] for row in labels}, set(range(5)))
            for line in {row['line'] for row in labels}:
                members = [row for row in labels if row['line'] == line]
                if len(members) == len('expires'):
                    self.assertEqual({row['word'] for row in members}, {0})
            page = Image.open(root/'a/page-0.png')
            with pikepdf.open(root/'a/scan.pdf') as pdf:
                self.assertEqual(list(pdf.pages[0].MediaBox), [0, 0, 432, 648])
                self.assertEqual(pdf.pages[0].Resources.XObject.Im0.read_bytes(), page.tobytes())
            self.assertEqual((root/'a/scan.pdf').read_bytes(), (root/'b/scan.pdf').read_bytes())
            record = b.document_record(root/'a/manifest.json')
            b.verify_frozen_document(root/'a/manifest.json', record)
            with self.assertRaisesRegex(ValueError, 'document mismatch'):
                b.verify_frozen_document(root/'a/manifest.json', dict(record, observations=0))
            for row in public:
                self.assertNotIn('face', row)
                self.assertNotIn('master_id', row)
                self.assertNotIn('baseline', row)
                self.assertNotIn('nominal_height_px', row)
                sample = Image.open(root/'a'/row['image'])
                self.assertEqual(sample.tobytes(), page.crop(row['bbox']).tobytes())
                self.assertEqual(b.digest((root/'a'/row['image']).read_bytes()), row['image_sha256'])
            with self.assertRaises(FileExistsError):
                b.generate_document(root / 'a', faces, 42, dpis=(200,))

    def test_main_dispatches_only_disjoint_partitions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'new'
            with patch('sys.argv', ['benchmark', '--out', str(output)]), \
                 patch.object(b, 'generate_document', return_value={'damage_coverage': {'incomplete': []}}) as generate:
                b.main()
            self.assertEqual(generate.call_count, 3)
            for call in generate.call_args_list:
                self.assertEqual(len({f['split'] for f in call.args[1]}), 1)

    def test_geometry_does_not_depend_on_degradation_draw_count(self):
        faces = b.font_manifest(b.installed_faces()[:1])
        original = b.degrade
        def extra_draws(pristine, severity, rng):
            rng.random(100)
            return original(pristine, severity, rng)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            b.generate_document(root/'a', faces, 42, dpis=(200,))
            with patch.object(b, 'degrade', side_effect=extra_draws):
                b.generate_document(root/'b', faces, 42, dpis=(200,))
            first = [json.loads(line)['transform'] for line in (root/'a/oracle/labels.jsonl').read_text().splitlines()]
            second = [json.loads(line)['transform'] for line in (root/'b/oracle/labels.jsonl').read_text().splitlines()]
            self.assertEqual(first, second)

    def test_per_face_character_damage_coverage_and_frozen_asset_gate(self):
        labels = [dict(font_sha256='a', character='e', severity=0),
                  dict(font_sha256='a', character='e', severity=3),
                  dict(font_sha256='b', character='e', severity=1)]
        self.assertEqual(b.damage_coverage(labels)['incomplete'], [['b', 'e']])
        faces = b.font_manifest(b.installed_faces()[:1])
        frozen = {'split_records': [{'faces': faces}]}
        b.verify_frozen_assets(faces, frozen)
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            b.verify_frozen_assets([dict(faces[0], sha256='changed')], frozen)

    def test_main_fails_incomplete_coverage_and_verifies_frozen_reproduction(self):
        faces = b.font_manifest(b.installed_faces())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = root/'frozen.json'
            frozen.write_text(json.dumps({'split_records': [dict(split=s, faces=faces) for s in ['train', 'validation', 'test']]}))
            with patch('sys.argv', ['benchmark', '--out', str(root/'new'), '--verify-manifest', str(frozen)]), \
                 patch.object(b, 'generate_document', return_value={'damage_coverage': {'incomplete': []}}), \
                 patch.object(b, 'verify_frozen_document') as verify:
                b.main()
            self.assertEqual(verify.call_count, 3)
            with patch('sys.argv', ['benchmark', '--out', str(root/'bad')]), \
                 patch.object(b, 'generate_document', return_value={'damage_coverage': {'incomplete': [['a','e']]}}):
                with self.assertRaisesRegex(ValueError, 'Incomplete clean/damaged'):
                    b.main()


if __name__ == '__main__':
    unittest.main()
