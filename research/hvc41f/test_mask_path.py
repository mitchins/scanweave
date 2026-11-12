import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import unittest
import numpy as np
from mask_path import mask_polygons

def reconstruct(loops,shape):
 # Even-odd point-in-polygon at pixel centres, independent of boundary tracing.
 result=np.zeros(shape,bool)
 for y in range(shape[0]):
  for x in range(shape[1]):
   px=x+.5;py=y+.5;inside=False
   for loop in loops:
    for a,b in zip(loop,loop[1:]):
     if (a[1]>py)!=(b[1]>py) and px<(b[0]-a[0])*(py-a[1])/(b[1]-a[1])+a[0]:inside=not inside
   result[y,x]=inside
 return result
class Boundary(unittest.TestCase):
 def check(self,m):self.assertTrue(np.array_equal(m,reconstruct(mask_polygons(m),m.shape)))
 def test_diagonal_contact(self):self.check(np.array([[1,0,1],[0,1,0],[1,0,1]],dtype=bool))
 def test_hole_and_narrow_bridges(self):self.check(np.array([[1,1,1,0],[1,0,1,1],[1,1,1,0]],dtype=bool))
 def test_foreign_pixel_never_covered(self):
  owned=np.array([[1,1,0],[0,1,0],[0,0,0]],dtype=bool);foreign=(1,2);actual=reconstruct(mask_polygons(owned),owned.shape);self.assertFalse(actual[foreign]);self.assertTrue(np.array_equal(actual,owned))
 def test_all_masks(self):
  for bits in range(512):self.check(np.array([(bits>>i)&1 for i in range(9)],dtype=bool).reshape(3,3))
if __name__=='__main__':unittest.main()
