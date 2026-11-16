"""Small checks for the experimental model and its ground-truth metrics."""
import pathlib
import sys
import unittest
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prototype as p
import local_model
import calibration

class PrototypeChecks(unittest.TestCase):
    def test_forward_zero_and_full_coverage(self):
        b = np.full((9, 9, 3), 0.8)
        k = np.array([0.1, 0.2, 0.3])
        np.testing.assert_allclose(p.forward(np.zeros((9, 9)), b, k, 1), b)
        np.testing.assert_allclose(p.forward(np.ones((9, 9)), b, k, 1), np.broadcast_to(k, b.shape))

    def test_metrics_detect_missing_and_join(self):
        truth = np.zeros((20, 20), bool)
        truth[4:15, 3:6] = True
        truth[4:15, 12:15] = True
        joined = truth.copy()
        joined[8:11, 6:12] = True
        self.assertEqual(p.scores(truth, truth)['false_joins'], 0)
        self.assertGreater(p.scores(truth, joined)['false_joins'], 0)
        self.assertGreater(p.scores(truth, np.zeros_like(truth))['missing_fraction'], .99)

    def test_component_ink_excludes_large_illustration(self):
        bg = np.full((100, 150, 3), .8)
        obs = bg.copy()
        obs[30:45, 20:25] = [.15, .15, .15]
        obs[20:70, 90:140] = [.32, .14, .045]
        result = local_model.estimate(obs, bg)
        self.assertTrue(result['eligible'][35, 22])
        self.assertFalse(result['eligible'][40, 110])
        self.assertLess(abs(result['ink'][35, 22, 0] - result['ink'][35, 22, 1]), .01)

    def test_calibration_does_not_use_heldout_font(self):
        metrics = {'boundary_f1': 1., 'missing_fraction': 0., 'false_ink_fraction': 0., 'false_joins': 0}
        train = {'font':'DejaVuSerif.ttf','declined':False,'confidence':10.,'uncertainty':.01,'methods':{'local':metrics}}
        held = {'font':'LiberationSerif-Italic.ttf','declined':False,'confidence':100.,'uncertainty':.01,'methods':{'local':metrics}}
        self.assertEqual(calibration.calibrate([train]), calibration.calibrate([train, held]))

    def test_flat_patch_declines(self):
        rgb = np.full((32, 32, 3), 225, np.uint8)
        self.assertTrue(p.reconstruction(rgb, 225)['decline'])

if __name__ == '__main__':
    unittest.main()
