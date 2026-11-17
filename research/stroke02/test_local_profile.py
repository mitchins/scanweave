"""Regression for transferring the original 613 crop fit to the page pre-pass."""
import pathlib,sys,unittest
import numpy as np
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import local_profile
class LocalProfileTest(unittest.TestCase):
 def test_613_matches_crop_fit(self):
  image=Image.open('/data/coding/scanweave/work/books01/stroke02/native/8967062-000.png').convert('RGB')
  rgb=np.asarray(image.crop((1135,718,1266,821)))
  boxes=[(1179,762,1193,779),(1196,764,1204,778),(1205,761,1220,780)]
  result=local_profile.fit_context(rgb,boxes,(1135,718))
  self.assertEqual([r['best']['sigma'] for r in result],[.7,.93,.7])
  page_result,_,_,_=local_profile.fit_line(np.asarray(image),boxes,(1179,761,1220,780))
  self.assertEqual([r['best']['sigma'] for r in page_result],[.7,.93,.7])
  for row in result+page_result:
   self.assertLess(row['best']['t'],row['t_max_physical'])
if __name__=='__main__':unittest.main()
