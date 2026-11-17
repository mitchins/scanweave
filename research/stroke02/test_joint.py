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

class PdfCoordinateTest(unittest.TestCase):
    def test_rectangle_roundtrip(self):
        import fitz
        import pypdfium2
        from skimage.measure import find_contours
        from joint_render import cubic_ring
        mask = np.zeros((32, 40), dtype=float)
        mask[8:24, 10:30] = 1
        up = ndi.zoom(mask, 4, order=3, grid_mode=True, mode='grid-constant')
        doc = fitz.open()
        page = doc.new_page(width=40, height=32)
        shape = page.new_shape()
        for ring in find_contours(np.pad(up, 1), .5):
            self.assertTrue(cubic_ring(shape, ring - 1, (0, 0), 1))
        shape.finish(fill=(0, 0, 0), color=None, even_odd=True, closePath=True)
        shape.commit()
        rendered = pypdfium2.PdfDocument(doc.tobytes())[0].render(scale=4).to_pil().convert('L')
        ink = 1 - np.asarray(rendered, dtype=float).reshape(32,4,40,4).mean((1,3))/255
        yy, xx = np.indices(mask.shape)
        self.assertLess(abs((ink*xx).sum()/ink.sum() - 19.5), .1)
        self.assertLess(abs((ink*yy).sum()/ink.sum() - 15.5), .1)
        self.assertLess(np.abs(ink-mask).mean(), .02)
