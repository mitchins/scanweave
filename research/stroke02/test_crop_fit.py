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
if __name__=='__main__':unittest.main()
