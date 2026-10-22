"""CPU research challenger tests; no optional skips or product model activation."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from font01 import challenger, context, linear_metric
from font01.metric_encoder import Encoder, training_loss
from font01.observations import Observation


class ChallengerTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        torch.manual_seed(10303)

    def test_encoder_and_training_selection(self):
        model = Encoder()
        self.assertEqual(sum(p.numel() for p in model.parameters()), 63696)
        images = torch.rand(8, 1, 48, 48)
        vectors = model(images)
        np.testing.assert_allclose(torch.linalg.vector_norm(vectors, dim=1).detach(), 1., atol=1e-6)
        targets = torch.tensor([0, 0, 1, 1, 0, 0, 1, 1])
        characters = torch.tensor([0, 1, 0, 1, 2, 3, 2, 3])
        weights = torch.ones(8)
        loss = training_loss(vectors, torch.zeros(8, 2), targets, characters, weights)
        self.assertTrue(torch.isfinite(loss))
        no_positive = training_loss(vectors, torch.zeros(8, 2), targets, torch.zeros(8), weights)
        self.assertTrue(torch.isfinite(no_positive))
        pairs = (np.zeros((4, 11)), np.array([True, False, True, False]), [],
                 np.array([0, 0, 2, 2]), np.array([1, 2, 3, 0]), np.ones(4, bool))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            selected = challenger.train_encoder(images, targets, characters, weights, images, pairs, output, epochs=5)
            self.assertEqual(json.loads((output/'selected.json').read_text())['epoch'], 5)
            np.testing.assert_array_equal(challenger.embed(selected, images), challenger.embed(selected, images))
            self.assertEqual(len(json.loads((output/'history.json').read_text())), 1)

    def test_geometry_context_excludes_query_character(self):
        rows = [{'page': 0, 'bbox': [i*10, y, i*10+8, y+10], 'character': char}
                for i, (char, y) in enumerate([('a', 0), ('a', 1), ('b', 0), ('c', 0), ('d', 0), ('e', 40)])]
        self.assertEqual(context.source_lines(rows), [[0, 2, 3, 4, 1], [5]])
        embeddings = np.eye(6, dtype=np.float32)
        vectors, dispersion, counts, lines = context.context_vectors(rows, embeddings)
        self.assertEqual(counts[0], 3)
        self.assertEqual(vectors[0, 0], 0)
        self.assertEqual(vectors[0, 1], 0)
        self.assertGreater(dispersion[0], 0)
        self.assertEqual(lines[-1], -1)
        self.assertFalse(vectors[-1].any())

    def test_extended_research_metric(self):
        rng = np.random.default_rng(2)
        x = rng.normal(size=(30, 15))
        y = np.array([True]*15+[False]*15)
        model = challenger.fit_extended(x, y)
        self.assertEqual(len(model['coefficients']), 15)
        self.assertFalse(model['qualified_for_product'])
        self.assertTrue(np.isfinite(challenger.predict_extended(model, x)).all())
        with patch.object(challenger.optimize, 'minimize', return_value=type('Failed', (), {'success': False, 'message': 'unit'})()):
            with self.assertRaisesRegex(RuntimeError, 'unit'):
                challenger.fit_extended(x, y)

    def test_source_only_tensor_and_frozen_baseline_validation(self):
        rows = [Observation('unit', 'e', {}, {'image': np.zeros((48, 48), np.float32)})]
        with patch.object(challenger, 'load_observations', return_value=(rows, [])):
            loaded, tensor = challenger.source_tensor(Path('controlled'), 'train')
            self.assertEqual(loaded, rows)
            self.assertEqual(tuple(tensor.shape), (1, 1, 48, 48))
        with patch.object(challenger, 'load_observations', return_value=([], [{'id': 'blank'}])):
            with self.assertRaisesRegex(ValueError, 'full observation'):
                challenger.source_tensor(Path('controlled'), 'train')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            x, y = np.zeros((2, 11)), np.asarray([True, False])
            np.savez_compressed(root/'train.npz', x=x, y=y)
            (root/'train-pairs.json').write_text('[]')
            (root/'linear-model.json').write_text('{}')
            record = {'fixture_manifest_sha256': 'unit-fixture', 'records': [{'split': 'train', 'array_sha256': hashlib.sha256(x.tobytes()+y.tobytes()).hexdigest(),
                                  'pair_metadata_sha256': hashlib.sha256(b'[]').hexdigest()}],
                      'linear_model_sha256': hashlib.sha256(b'{}').hexdigest()}
            frozen = root/'frozen.json'
            frozen.write_text(json.dumps(record))
            challenger.validate_baseline(root, 'unit-fixture', frozen)
            with self.assertRaisesRegex(ValueError, 'fixture identities differ'):
                challenger.validate_baseline(root, 'changed-fixture', frozen)
            (root/'linear-model.json').write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'model differs'):
                challenger.validate_baseline(root, 'unit-fixture', frozen)
            (root/'train-pairs.json').write_text('[{}]')
            with self.assertRaisesRegex(ValueError, 'arrays and pairs'):
                challenger.validate_baseline(root, 'unit-fixture', frozen)

    def test_run_freezes_before_test_and_checks_unchanged_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root/'baseline'
            baseline.mkdir()
            metric = linear_metric.LinearMetric(np.zeros(11), np.ones(11), np.zeros(11), 0.)
            metric.save(baseline/'linear-model.json')
            output = root/'output'
            rows = [Observation(str(i), char, {'character': char, 'page': 0, 'bbox': [i*8, 0, i*8+6, 10]},
                                {'image': np.ones((48, 48), np.float32)*i/10}) for i, char in enumerate('abcd')]
            pairs = (np.zeros((4, 11)), np.array([True, False, True, False]), [],
                     np.array([0, 0, 1, 1]), np.array([1, 2, 2, 3]), np.ones(4, bool))
            def sources(corpus, split):
                if split == 'test':
                    frozen = json.loads((output/'pretest-freeze.json').read_text())
                    self.assertEqual(len(frozen['thresholds']), 5)
                    self.assertEqual(frozen['encoder_sha256'], hashlib.sha256((output/'encoder.pt').read_bytes()).hexdigest())
                return rows, torch.ones(4, 1, 48, 48)
            def train(*args):
                model = Encoder()
                torch.save(model.state_dict(), output/'encoder.pt')
                return model
            labels = {str(i): {'font_sha256': str(i%2), 'severity': 0} for i in range(4)}
            with patch.object(challenger, 'verify_corpus', return_value='fixture'), \
                    patch.object(challenger, 'validate_baseline'), \
                    patch.object(challenger, 'source_tensor', side_effect=sources), \
                    patch.object(challenger, 'pair_inputs', return_value=pairs), \
                    patch.object(challenger, 'evaluator_labels', return_value=labels), \
                    patch.object(challenger, 'validate_evaluator_join'), \
                    patch.object(challenger, 'train_encoder', side_effect=train):
                results = challenger.run(root, baseline, output)
            self.assertEqual(len(results), 10)
            self.assertTrue((output/'pretest-freeze.json').exists())


if __name__ == '__main__':
    unittest.main()
