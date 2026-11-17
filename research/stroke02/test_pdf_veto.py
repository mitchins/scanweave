"""Exercise real PDFium rendering of a vetoed glyph and an empty counter area."""
import json,pathlib,sys,unittest
import fitz,numpy as np
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import verify_pdf_veto
D=pathlib.Path('/data/coding/scanweave/work/books01/stroke02/tmp/pdf-veto-test')
class PdfVetoTest(unittest.TestCase):
 def test_rendered_ink_fails_and_far_paper_passes(self):
  D.mkdir(parents=True,exist_ok=True);doc=fitz.open();p=doc.new_page(width=100,height=100);p.insert_text((20,50),'M',fontsize=30,color=(0,0,0));doc.save(D/'candidate.pdf');doc.close()
  (D/'extensions.json').write_text(json.dumps({'decisions':[{'decision':'accepted','symbol_id':'s','bbox':[20,25,50,52]}]}))
  (D/'prepass.json').write_text(json.dumps({'lines':[{'bbox':[20,25,50,52],'sigma':.5,'noise_proxy':.03}]}))
  veto=np.zeros((100,100),np.uint8);veto[35:40,22:27]=255;Image.fromarray(veto).save(D/'paper-veto.png');bad=verify_pdf_veto.verify(D,72);self.assertEqual(bad['blocked'],['s'])
  veto[:]=0;veto[27,49]=255;Image.fromarray(veto).save(D/'paper-veto.png');good=verify_pdf_veto.verify(D,72);self.assertEqual(good['blocked'],[])
if __name__=='__main__':unittest.main()
