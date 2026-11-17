"""Focused physical checks; no converter or full-page runs."""
import pathlib,sys,unittest
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit
class InverseChecks(unittest.TestCase):
 def test_bounds(self):
  obs=np.random.default_rng(7).uniform(0,1,(20,20));x=crop_fit.bounded_inverse(obs,1.2,50)
  self.assertGreaterEqual(float(x.min()),0);self.assertLessEqual(float(x.max()),1)
 def test_constant_is_fixed_point(self):
  obs=np.full((20,20),.4);np.testing.assert_allclose(crop_fit.bounded_inverse(obs,1.2,20),obs,atol=1e-12)
 def test_forward_residual_decreases_on_blurred_shape(self):
  truth=np.zeros((40,40));truth[10:30,16:23]=1.;obs=ndi.gaussian_filter(truth,1.2);candidate=crop_fit.bounded_inverse(obs,1.2,20)
  before=np.mean((ndi.gaussian_filter(obs,1.2)-obs)**2);after=np.mean((ndi.gaussian_filter(candidate,1.2)-obs)**2);self.assertLess(after,before)
 def test_small_mark_is_protected_from_neighbour_dilation(self):
  m=np.zeros((15,20),bool);m[5:10,3:6]=True;m[6,8]=True
  eligible,forbidden,small,cross=crop_fit.protected_components(m,[[2,4,7,11],[8,5,10,9]],0,0)
  self.assertTrue(eligible[7,4]);self.assertTrue(forbidden[6,8]);self.assertEqual(small,1)
 def test_join_between_ocr_groups_is_left_raster(self):
  m=np.zeros((15,20),bool);m[5:10,3:12]=True
  eligible,forbidden,small,cross=crop_fit.protected_components(m,[[2,4,7,11],[8,4,13,11]],0,0)
  self.assertFalse(eligible.any());self.assertTrue(forbidden[7,7]);self.assertEqual(cross,1)
if __name__=='__main__':unittest.main()
