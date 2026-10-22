"""Frozen-source, registration, metric, clustering and uncertainty contracts."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from font01 import clustering, evaluation, linear_metric, observations, pair_data, product_control, registration, run_baseline

INPUTS = Path(__file__).parent/'font01/test_inputs'


class ObservationTests(unittest.TestCase):
    def test_frozen_source_and_registered_features(self):
        rows, abstentions = observations.load_observations(INPUTS)
        self.assertFalse(abstentions)
        self.assertEqual(len(rows), 4)
        registration.attach_registration_candidates(rows)
        values, transforms = registration.compare(rows[0], rows[1])
        expected = json.loads((INPUTS/'frozen.json').read_text())
        np.testing.assert_array_equal(values, expected['feature_values'])
        self.assertEqual(transforms, expected['registration'])
        reverse, _ = registration.compare(rows[1], rows[0])
        np.testing.assert_array_equal(reverse, values)
        for transform in transforms.values():
            self.assertLessEqual(abs(transform['dy']), 2)
            self.assertLessEqual(abs(transform['dx']), 2)
            self.assertLessEqual(abs(transform['angle']), 1.5)
            self.assertTrue(.97 <= transform['scale'] <= 1.03)
        self.assertLess(float(registration.deterministic_score(values)), 0)
        with self.assertRaisesRegex(ValueError, 'identical character'):
            registration.compare(rows[0], rows[2])

    def test_blank_invalid_and_topological_evidence(self):
        self.assertIsNone(observations.preprocess_samples(np.full((10, 10), 255)))
        for sample in [np.zeros((2, 2, 2)), np.zeros((0, 2)), np.full((2, 2), np.nan), np.full((2, 2), -1)]:
            with self.assertRaises(ValueError):
                observations.preprocess_samples(sample)
        self.assertIsNone(observations.normalized_coverage(np.zeros((2, 2))))
        ring = np.zeros((9, 9), bool)
        ring[1:8, 1:8] = True
        ring[3:6, 3:6] = False
        self.assertEqual(observations.topology(ring), (1, 1))
        with self.assertRaises(ValueError):
            registration.best_alignment(np.zeros((48, 48)), [])

    def test_source_containment_hashes_oracle_rejection_and_abstention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root/'corpus'
            corpus.mkdir()
            inside = corpus/'inside'
            inside.write_text('source')
            (corpus/'internal').symlink_to(inside)
            self.assertEqual(observations.source_path(corpus, 'internal'), inside)
            external = root/'external'
            external.write_text('not authorized')
            (corpus/'link').symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'outside'):
                observations.source_path(corpus, 'link')
            record = json.loads((INPUTS/'observations.jsonl').read_text().splitlines()[0])
            record['image'] = str(INPUTS.resolve()/record['image'])
            (corpus/'observations.jsonl').write_text(json.dumps(dict(record, face='oracle'))+'\n')
            with self.assertRaisesRegex(ValueError, 'Oracle fields'):
                observations.load_observations(corpus)
            record['image'] = 'sample.png'
            (corpus/'sample.png').write_bytes((INPUTS/'glyph-0.png').read_bytes())
            (corpus/'observations.jsonl').write_text(json.dumps(dict(record, image_sha256='invalid'))+'\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                observations.load_observations(corpus)
            (corpus/'observations.jsonl').write_text(json.dumps(record)+'\n'+json.dumps(record)+'\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                observations.load_observations(corpus)
            (corpus/'observations.jsonl').write_text(json.dumps(record)+'\n')
            with patch.object(observations, 'preprocess_samples', return_value=None):
                rows, abstentions = observations.load_observations(corpus)
            self.assertFalse(rows)
            self.assertEqual(abstentions[0]['reason'], 'insufficient_source_ink')


class MetricTests(unittest.TestCase):
    def test_linear_fit_serialization_batch_parity_and_fail_closed_schema(self):
        x = np.zeros((20, 11))
        x[10:, 0] = 1
        y = np.arange(20) >= 10
        metric = linear_metric.fit_metric(x, y)
        self.assertLess(float(metric.scores(x[0])), .2)
        self.assertGreater(float(metric.scores(x[-1])), .8)
        np.testing.assert_allclose(metric.scores(x), [metric.scores(row) for row in x],
                                   rtol=1e-12, atol=1e-12)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'model.json'
            metric.save(path)
            loaded = linear_metric.load_metric(path)
            np.testing.assert_array_equal(metric.scores(x), loaded.scores(x))
            self.assertFalse(json.loads(path.read_text())['qualified_for_product'])
            for replacement in [dict(schema='unknown'), dict(feature_names=['wrong']), dict(scale=[0]*11), dict(mean=[1]), dict(intercept=float('inf'))]:
                data = metric.document()
                data.update(replacement)
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    linear_metric.load_metric(path)
        for invalid in [np.zeros(12), np.full(11, np.nan)]:
            with self.assertRaises(ValueError):
                metric.scores(invalid)
        for a, b in [(np.zeros((2, 10)), [0, 1]), (np.full((2, 11), np.nan), [0, 1]), (x, [1]*20)]:
            with self.assertRaises(ValueError):
                linear_metric.fit_metric(a, b)
        with patch.object(linear_metric.optimize, 'minimize') as minimize:
            minimize.return_value.success = False
            minimize.return_value.message = 'controlled failure'
            with self.assertRaisesRegex(RuntimeError, 'optimization failed'):
                linear_metric.fit_metric(x, y)

    def test_pair_metrics_ties_probabilities_and_thresholds(self):
        labels = np.array([False, False, True, True])
        scores = np.array([.1, .2, .8, .9])
        result = evaluation.pair_metrics(labels, scores, .5, probabilities=True)
        self.assertEqual(result['roc_auc'], 1)
        self.assertEqual(result['pr_auc'], 1)
        self.assertEqual(result['false_merge_rate'], 0)
        self.assertAlmostEqual(result['ece'], .15)
        self.assertIsNone(evaluation.pair_metrics(labels, scores, .5)['ece'])
        tied = np.full(4, .5)
        threshold = evaluation.threshold_at_fpr(labels, tied, 0)
        self.assertGreater(threshold, .5)
        self.assertIsNone(evaluation.pair_metrics(labels, tied, threshold)['precision'])
        self.assertEqual(evaluation.false_merge_at_recall(labels, scores, .5)['recall'], .5)
        self.assertIsNone(evaluation.pair_metrics(np.array([True]), np.array([.5]), .4)['roc_auc'])
        with self.assertRaises(ValueError):
            evaluation.pair_metrics(labels, scores+1, .5, probabilities=True)
        for y, p in [(labels.astype(int), scores), (labels, np.array([1.])), (labels, scores*np.nan)]:
            with self.assertRaises(ValueError):
                evaluation.pair_metrics(y, p, .5)
        with self.assertRaises(ValueError):
            evaluation.threshold_at_fpr(np.array([True]), np.array([.5]))
        with self.assertRaises(ValueError):
            evaluation.false_merge_at_recall(labels, scores, 0)


class ClusteringTests(unittest.TestCase):
    def test_complete_link_avoids_chaining_and_preserves_character_identity(self):
        matrix = np.array([[0, .1, .8], [.1, 0, .1], [.8, .1, 0]])
        ids = ['a', 'b', 'c']
        result = clustering.complete_groups(ids, matrix, .2)
        self.assertEqual(result, [['a', 'b'], ['c']])
        order = [2, 0, 1]
        self.assertEqual(result, clustering.complete_groups([ids[i] for i in order], matrix[np.ix_(order, order)], .2))
        self.assertEqual(clustering.complete_groups(ids, np.zeros((3, 3)), .2, ['e', 'e', 'c']), [['a', 'b'], ['c']])
        self.assertEqual(clustering.complete_groups([], np.empty((0, 0)), 0), [])
        self.assertEqual(clustering.complete_groups(['a'], np.zeros((1, 1)), 0), [['a']])
        for distances, maximum, chars in [(matrix, -1, None), (matrix, .2, ['e']), (matrix[:2], .2, None), (np.full((3, 3), np.nan), .2, None)]:
            with self.assertRaises(ValueError):
                clustering.complete_groups(ids, distances, maximum, chars)

    def test_ari_and_separate_purity_completeness(self):
        perfect = clustering.clustering_metrics(['a', 'a', 'b', 'b'], [2, 2, 1, 1])
        self.assertEqual(perfect['adjusted_rand_index'], 1)
        split = clustering.clustering_metrics(['a', 'a', 'b', 'b'], [0, 1, 2, 3])
        self.assertEqual(split['purity'], 1)
        self.assertEqual(split['completeness'], .5)
        mixed = clustering.clustering_metrics(['a', 'a', 'b', 'b'], [0, 1, 0, 1])
        self.assertLess(mixed['adjusted_rand_index'], 0)
        with self.assertRaises(ValueError):
            clustering.clustering_metrics([], [])


class PairDataTests(unittest.TestCase):
    def test_evaluator_join_and_stratified_pairs_are_separate_from_inference(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in INPUTS.glob('*.png'):
                shutil.copy2(path, root/path.name)
            records = [json.loads(line) for line in (INPUTS/'observations.jsonl').read_text().splitlines()]
            records.append(dict(records[0], id='controlled-unit-copy'))
            (root/'observations.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in records))
            (root/'oracle').mkdir()
            labels = [dict(id=row['id'], font_sha256='unit-B' if i == 1 else 'unit-A',
                           character=row['character'], family='unit-family', severity=0)
                      for i, row in enumerate(records)]
            path = root/'oracle/labels.jsonl'
            path.write_text(''.join(json.dumps(row)+'\n' for row in labels))
            loaded, abstentions = observations.load_observations(root)
            self.assertFalse(abstentions)
            lookup = pair_data.evaluator_labels(root)
            pair_data.validate_evaluator_join(root, lookup)
            for changed in [dict(list(lookup.items())[1:]), dict(lookup, extra=labels[0])]:
                with self.assertRaisesRegex(ValueError, 'complete source ID'):
                    pair_data.validate_evaluator_join(root, changed)
            changed = dict(lookup)
            changed[labels[0]['id']] = dict(labels[0], character='x')
            with self.assertRaisesRegex(ValueError, 'character differs'):
                pair_data.validate_evaluator_join(root, changed)
            first = pair_data.sample_pairs(loaded, lookup, 100, 1)
            self.assertEqual(first, pair_data.sample_pairs(loaded, lookup, 100, 1))
            with self.assertRaises(ValueError):
                pair_data.sample_pairs(loaded, lookup, 1, 1)
            x, y, metadata, timing = pair_data.build_pairs(root, 100, 1)
            self.assertEqual(x.shape, (3, 11))
            self.assertEqual(int(y.sum()), 1)
            self.assertEqual(timing['usable_observations'], 5)
            self.assertTrue(all(row['character'] == 'e' for row in metadata))
            path.write_text(json.dumps(labels[0])+'\n'+json.dumps(labels[0])+'\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate evaluator'):
                pair_data.evaluator_labels(root)


class RunnerTests(unittest.TestCase):
    def test_input_binding_and_pretest_freeze_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root/'run'
            x = np.zeros((4, 11))
            y = np.asarray([True, False, True, False])
            pairs = [{'severity': 0} for _ in y]
            model = linear_metric.LinearMetric(np.zeros(11), np.ones(11), np.zeros(11), 0.)
            calls = []
            def build(path, count, seed):
                calls.append(path.name)
                if path.name == 'test':
                    freeze = json.loads((output/'pretest-freeze.json').read_text())
                    self.assertEqual(freeze['fixture_manifest_sha256'], 'controlled-hash')
                    for name in ['validation.json', 'linear-model.json']:
                        self.assertEqual(freeze[name], hashlib.sha256((output/name).read_bytes()).hexdigest())
                return x, y, pairs, {'seconds': 0.}
            with patch.object(run_baseline, 'verify_corpus', return_value='controlled-hash') as verify, \
                    patch.object(run_baseline, 'build_pairs', side_effect=build), \
                    patch.object(run_baseline, 'fit_metric', return_value=model):
                run_baseline.run(root, output)
                self.assertEqual(calls, ['train', 'validation', 'test'])
                self.assertEqual(verify.call_count, 3)
            with patch.object(run_baseline, 'verify_corpus', side_effect=ValueError('changed corpus')):
                with self.assertRaisesRegex(ValueError, 'changed corpus'):
                    run_baseline.run(root, root/'rejected')
                self.assertFalse((root/'rejected').exists())
            frozen = root/'bad-manifest.json'
            frozen.write_text(json.dumps({'split_records': []}))
            with self.assertRaisesRegex(ValueError, 'exactly'):
                run_baseline.verify_corpus(root, frozen)
            frozen.write_text(json.dumps({'split_records': [{'split': s} for s in ['train', 'validation', 'test']]}))
            with patch.object(run_baseline, 'verify_frozen_document') as verify:
                self.assertEqual(len(run_baseline.verify_corpus(root, frozen)), 64)
                self.assertEqual(verify.call_count, 3)


class ProductControlTests(unittest.TestCase):
    def test_public_only_bundle_geometry_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            from PIL import Image
            Image.new('RGB', (30, 60), 'white').save(source/'page-0.png')
            record = {'id': '1opaque', 'character': 'é', 'page': 0, 'dpi': 300,
                      'bbox': [1, 2, 10, 20]}
            public = source/'observations.jsonl'
            public.write_text(json.dumps(record)+'\n')
            output = root/'bundle'
            path = product_control.make_bundle(source, output)
            self.assertEqual(json.loads(path.read_text())['pages'][0]['page_id'], 'p000')
            ocr = json.loads((output/'page-0.ocr.json').read_text())
            self.assertEqual(ocr['page']['width_pt'], 7.2)
            self.assertEqual(ocr['spans'][0]['id'], 'g1opaque')
            self.assertEqual(ocr['spans'][0]['symbols'][0]['text_range_utf8'], [0, 2])
            self.assertEqual(ocr['raster']['file_sha256'], hashlib.sha256((output/'page-0.png').read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                product_control.make_bundle(source, output)
            for value in [0, -1, float('nan'), True, '300']:
                with self.assertRaisesRegex(ValueError, 'finite and positive'):
                    product_control.write_page(source, output, [dict(record, dpi=value)], 0)
            with self.assertRaisesRegex(ValueError, 'Inconsistent'):
                product_control.write_page(source, output, [record, dict(record, dpi=200)], 0)
            for key in observations.ORACLE_FIELDS:
                public.write_text(json.dumps(dict(record, **{key: 'oracle'}))+'\n')
                with self.assertRaisesRegex(ValueError, 'oracle fields'):
                    product_control.make_bundle(source, root/'rejected')
                with self.assertRaisesRegex(ValueError, 'Oracle fields'):
                    observations.load_observations(source)
            for rows in [[], [dict(record, page=-1)]]:
                public.write_text(''.join(json.dumps(row)+'\n' for row in rows))
                with self.assertRaises(ValueError):
                    product_control.make_bundle(source, root/'rejected')


if __name__ == '__main__':
    unittest.main()
