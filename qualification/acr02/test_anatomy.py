"""Mechanical contracts for derivative-only ablation; no external corpus required."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pikepdf

from anatomy import derivative, render


class AblationTests(unittest.TestCase):
    def fixture(self, path):
        pdf = pikepdf.new()
        page = pdf.add_blank_page(page_size=(72, 72))
        image = pikepdf.Stream(pdf, bytes([255, 0, 0] * 4))
        image.Type = pikepdf.Name.XObject
        image.Subtype = pikepdf.Name.Image
        image.Width = image.Height = 2
        image.BitsPerComponent = 8
        image.ColorSpace = pikepdf.Name.DeviceRGB
        form = pikepdf.Stream(pdf, b'q 0 0 .5 1 re W n /Im Do Q')
        form.Type = pikepdf.Name.XObject
        form.Subtype = pikepdf.Name.Form
        form.BBox = pikepdf.Array([0, 0, 1, 1])
        form.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm=form))
        page.Contents = pikepdf.Stream(pdf, b'q 72 0 0 72 0 0 cm /Fm Do Q 0 0 1 rg 36 0 36 36 re f')
        pdf.save(path)

    def test_nested_image_clip_and_path_isolation_both_renderers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.pdf'
            self.fixture(source)
            original_hash = source.read_bytes()
            for mode in ('all', 'images', 'paths', 'fonts'):
                derivative(source, 0, mode, root / f'{mode}.pdf')
            for engine in ('pdfium', 'poppler'):
                original = np.asarray(render(source, 0, engine, 72))
                replay = np.asarray(render(root / 'all.pdf', 0, engine, 72))
                self.assertTrue(np.array_equal(original, replay))
                images = np.asarray(render(root / 'images.pdf', 0, engine, 72))
                paths = np.asarray(render(root / 'paths.pdf', 0, engine, 72))
                fonts = np.asarray(render(root / 'fonts.pdf', 0, engine, 72))
                self.assertTrue((images[20, 20] == [255, 0, 0]).all())
                self.assertTrue((images[20, 55] == 255).all())
                self.assertTrue((paths[55, 55] == [0, 0, 255]).all())
                self.assertTrue((fonts == 255).all())
            self.assertEqual(original_hash, source.read_bytes())

    def test_text_clipping_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'clip.pdf'
            self.fixture(source)
            with pikepdf.open(source, allow_overwriting_input=True) as pdf:
                pdf.pages[0].Contents = pikepdf.Stream(pdf, b'BT 7 Tr ET')
                pdf.save(source)
            with self.assertRaisesRegex(ValueError, 'Text stroke/clip'):
                derivative(source, 0, 'fonts', source.with_name('out.pdf'))


if __name__ == '__main__':
    unittest.main()
