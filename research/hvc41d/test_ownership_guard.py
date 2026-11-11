import sys,pathlib,unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from ownership_guard import require_owned
class GuardTest(unittest.TestCase):
 def test_subset(self):self.assertTrue(require_owned([[0,1],[0,0]],[[0,1],[1,0]]))
 def test_outside(self):
  with self.assertRaisesRegex(ValueError,'exceeds recorded ownership'):require_owned([[1,1],[0,0]],[[0,1],[1,0]])
 def test_dimensions(self):
  with self.assertRaisesRegex(ValueError,'dimensions differ'):require_owned([[1]],[[1,0]])
if __name__=='__main__':unittest.main()
