"""Mechanical controls for resource identity, nested Forms, masks and paint geometry."""
import tempfile
import unittest
from pathlib import Path

import pikepdf
from inspect_pdf import inspect, matrix


class InspectorTests(unittest.TestCase):
    def test_affine_order(self):
        self.assertEqual(matrix([2,0,0,3,10,20],[1,0,0,1,4,5]),[2,0,0,3,18,35])

    def test_form_mask_shared_resource_and_inline(self):
        pdf=pikepdf.Pdf.new();page=pdf.add_blank_page(page_size=(144,144))
        image=pikepdf.Stream(pdf,b'\x80'*4)
        image.update({'/Type':pikepdf.Name.XObject,'/Subtype':pikepdf.Name.Image,
                      '/Width':2,'/Height':2,'/BitsPerComponent':8,'/ColorSpace':pikepdf.Name.DeviceGray})
        mask=pikepdf.Stream(pdf,b'\xff'*4)
        mask.update({'/Type':pikepdf.Name.XObject,'/Subtype':pikepdf.Name.Image,
                     '/Width':2,'/Height':2,'/BitsPerComponent':8,'/ColorSpace':pikepdf.Name.DeviceGray})
        image.SMask=mask
        form=pikepdf.Stream(pdf,b'q 72 0 0 72 0 0 cm /I Do Q')
        form.update({'/Type':pikepdf.Name.XObject,'/Subtype':pikepdf.Name.Form,
                     '/BBox':pikepdf.Array([0,0,72,72]),'/Matrix':pikepdf.Array([1,0,0,1,10,20]),
                     '/Resources':pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image))})
        page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=form))
        page.Contents=pikepdf.Stream(pdf,b'/F Do /F Do q 10 0 0 10 0 0 cm BI /W 1 /H 1 /BPC 1 /IM true ID \x80 EI Q')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'test.pdf';pdf.save(path)
            before=path.read_bytes();result=inspect(path)
            self.assertEqual(before,path.read_bytes())
        self.assertEqual(len(result['images']),2)
        self.assertEqual(len(result['inline_images']),1)
        forms=[n for n in result['pages'][0]['paint_graph'] if n['kind']=='form']
        self.assertEqual(len(forms),2)
        self.assertEqual(forms[0]['children'][0]['effective_dpi'],[2.,2.])
        self.assertEqual(result['graphics_states'][forms[0]['children'][0]['state_ref']]['ctm'],[72.,0.,0.,72.,10.,20.])
        masks=[i for i in result['images'].values() if i['resource_role']=='/SMask']
        self.assertEqual(len(masks),1)
        self.assertTrue(masks[0]['selected_parents'])


if __name__=='__main__':
    unittest.main()
