"""Focused algorithm contracts; no pristine fonts or evaluation labels in inference."""
import unittest
import numpy as np
from prototype import paper_and_chroma, boxes, compound_ownership, overlaps, sparse_tiles


class ObjectFirstTests(unittest.TestCase):
    def test_solid_blue_interior_is_an_object_not_paper(self):
        image=np.full((512,512,3),250,dtype=np.float32)
        image[100:300,120:310]=[20,85,150]
        paper,chroma,_=paper_and_chroma(image)
        self.assertTrue(chroma[200,200])
        self.assertLess(float(np.ptp(paper[200,200])),1)
        self.assertGreater(float(paper[200,200].min()),240)
        regions=boxes(chroma,(13,13),4)
        self.assertTrue(any(x0<=200<x1 and y0<=200<y1 for x0,y0,x1,y1 in regions))

    def test_neutral_ink_on_yellow_paper_is_not_coloured_art(self):
        image=np.full((512,512,3),[220,210,180],dtype=np.float32)
        for x,coverage in enumerate(np.linspace(0,1,64)):
            image[180:230,100+x]=(1-coverage)*np.array([220,210,180])+coverage*30
        _,chroma,_=paper_and_chroma(image)
        self.assertFalse(chroma[180:230,100:164].any())

    def test_crossing_glyph_is_wholly_transferred_to_compound_object(self):
        regions=[[10,10,20,20]]
        glyphs=[(4,[18,15,30,25]),(8,[50,50,60,60])]
        hidden=compound_ownership(regions,glyphs,100,100)
        self.assertEqual(hidden,{4})
        self.assertEqual(regions,[[10,10,30,25]])
        self.assertFalse(overlaps(regions[0],glyphs[1][1]))

    def test_sparse_native_tiles_cover_all_support(self):
        support=np.zeros((1100,1100),dtype=bool)
        support[0,0]=True
        support[511:514,511:514]=True
        support[1099,1099]=True
        covered=np.zeros_like(support)
        for x0,y0,x1,y1 in sparse_tiles(support):
            covered[y0:y1,x0:x1]=True
        self.assertTrue(np.all(covered[support]))
        self.assertLess(int(covered.sum()),1100*1100)


if __name__=='__main__':unittest.main()
