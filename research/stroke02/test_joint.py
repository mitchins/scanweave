"""Sanity check the pooled model on an isolated known synthetic stroke."""
import unittest
import numpy as np
from scipy import ndimage as ndi
import joint_fit

class ProfileTest(unittest.TestCase):
    def test_known_straight_stroke(self):
        mask = np.zeros((36, 36), dtype=bool)
        mask[5:31, 16:20] = True
        observed = ndi.gaussian_filter(mask.astype(float), 1.1) * .7
        result = joint_fit.profile_fit(observed, mask, [1.1], .6, 1.4)
        self.assertGreaterEqual(result['n_profiles'], 2)
        best = min(result['grid'], key=lambda x: x['rmse'])
        self.assertLess(abs(best['median_width_px'] - 4), .3)
        self.assertLess(abs(best['t'] * .6 - .7), .06)
        self.assertLess(best['rmse'], .02)

if __name__ == '__main__':
    unittest.main()
