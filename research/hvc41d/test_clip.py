"""Unit and rendered-PDF integration tests for exact source ownership clipping."""
import pathlib,sys,unittest,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from ownership_guard import clip_owned,require_owned,require_contained_bbox
class ClipTests(unittest.TestCase):
 def test_subset_and_boundary(self):
  proposed=np.ones((3,3),bool);owned=np.zeros((3,3),bool);owned[0,0]=owned[1,1]=True
  result=clip_owned(proposed,owned);self.assertTrue(np.array_equal(result,owned));self.assertFalse(np.any(result&~owned));require_owned(result,owned)
 def test_owner_box_contains_traced_box(self):
  self.assertTrue(require_contained_bbox([1,0,4,4],[0,0,4,4]))
  with self.assertRaises(ValueError):require_contained_bbox([-1,0,4,4],[0,0,4,4])
 def test_dimensions_fail_closed(self):
  with self.assertRaises(ValueError):clip_owned([[1]],[[1,0]])
 def test_foreign_ink_is_not_erased_in_rendered_pdf(self):
  owned=np.zeros((8,8),bool);owned[2:6,2:4]=True;foreign=np.zeros((8,8),bool);foreign[2:6,4]=True;proposed=owned|foreign;patch=clip_owned(proposed,owned);self.assertFalse(np.any(patch&foreign))
  with tempfile.TemporaryDirectory() as td:
   pdf=pikepdf.Pdf.new();page=pdf.add_blank_page(page_size=(8,8));ops=['0 0 0 rg 2 2 3 4 re f','1 1 1 rg']
   for y,x in zip(*np.nonzero(patch)):ops.append(f'{x} {7-y} 1 1 re')
   ops.append('f');page.Contents=pdf.make_stream(('\n'.join(ops)).encode());path=pathlib.Path(td)/'clip.pdf';pdf.save(path);pdf.close();doc=pdfium.PdfDocument(str(path));pg=doc[0];img=np.asarray(pg.render(scale=1,rev_byteorder=True).to_pil().convert('RGB'));self.assertTrue(np.all(img[2:6,4]==0));self.assertTrue(np.all(img[2:6,2:4]==255));pg.close();doc.close()
if __name__=='__main__':unittest.main()
