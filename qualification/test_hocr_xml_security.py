"""Exercise the real region-OCR parser options without running its OCR side effects."""
import ast
from pathlib import Path
import tempfile
import runpy
import subprocess
from unittest.mock import patch

from PIL import Image
import unittest

from lxml import etree

SOURCE = Path(__file__).parent / 'clearscan_competitive' / 'real' / 'region_ocr.py'


def parser_options():
    module = ast.parse(SOURCE.read_text())
    calls = [node for node in ast.walk(module)
             if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name)
             and node.func.value.id == 'etree'
             and node.func.attr == 'XMLParser']
    if len(calls) != 1:
        raise AssertionError('Expected one region-OCR XML parser boundary')
    return {item.arg: ast.literal_eval(item.value) for item in calls[0].keywords}


class HocrXmlSecurity(unittest.TestCase):
    def parse(self, data):
        return etree.fromstring(data, etree.XMLParser(**parser_options()))

    def test_explicit_entity_and_external_resource_policy(self):
        options = parser_options()
        for name in ('resolve_entities', 'load_dtd'):
            self.assertIs(options[name], False)
        self.assertIs(options['no_network'], True)

    def test_custom_internal_entities_are_not_expanded(self):
        root = self.parse(b'<!DOCTYPE html [<!ENTITY mark "INJECTED_CONTENT">]>'
                          b'<html><body>&mark;</body></html>')
        self.assertNotIn('INJECTED_CONTENT', ''.join(root.itertext()))

    def test_local_file_entities_are_not_expanded(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / 'sentinel.txt'
            sentinel.write_text('LOCAL_FILE_SENTINEL')
            payload = (f'<!DOCTYPE html [<!ENTITY mark SYSTEM "{sentinel.as_uri()}">]>'
                       '<html><body>&mark;</body></html>').encode()
            root = self.parse(payload)
            self.assertNotIn('LOCAL_FILE_SENTINEL', ''.join(root.itertext()))

    def test_actual_region_script_preserves_text_without_entity_expansion(self):
        # Exercise the production parser/coordinate rewrite. Only Tesseract is
        # mocked; private images and hOCR keep this independent of the corpus.
        original_resolve = Path.resolve
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new('L', (32, 32), 220).save(root / 'history-unit.png')

            def resolve(path, *args, **kwargs):
                if path == SOURCE:
                    return root / 'region_ocr.py'
                return original_resolve(path, *args, **kwargs)

            def tesseract(command, **kwargs):
                self.assertEqual(command[0], 'tesseract')
                self.assertEqual(command[-1], 'hocr')
                self.assertTrue(kwargs['check'])
                Path(command[2] + '.hocr').write_bytes(
                    b'<!DOCTYPE html [<!ENTITY mark "INJECTED_CONTENT">]>'
                    b'<html><body><div class="ocr_page" title="bbox 0 0 32 32">'
                    b'<span title="bbox 1 2 3 4">caf&#233; &amp; 8</span>'
                    b'<span>&mark;</span></div></body></html>')
                return subprocess.CompletedProcess(command, 0, '', '')

            with patch.object(Path, 'resolve', resolve), patch(
                    'subprocess.run', side_effect=tesseract) as runner:
                runpy.run_path(str(SOURCE))
            runner.assert_called_once()
            output = root / 'history-unit.regions.hocr'
            doc = etree.parse(str(output), etree.XMLParser(resolve_entities=False))
            spans = doc.findall('.//span')
            self.assertEqual(spans[0].text, 'caf\u00e9 & 8')
            self.assertEqual(spans[0].get('title'), 'bbox 1 2 3 4')
            self.assertNotIn('INJECTED_CONTENT', ''.join(doc.getroot().itertext()))
            self.assertEqual(doc.find('.//div').get('title'),
                             'bbox 0 0 32 32; scan_res 300 300')
            self.assertTrue((root / 'region-ocr-manifest.json').is_file())

    def test_normal_namespaced_hocr_and_external_doctype_survive(self):
        class NoExternalAccess(etree.Resolver):
            def resolve(self, url, public_id, context):
                raise AssertionError('External resource access attempted')

        parser = etree.XMLParser(**parser_options())
        parser.resolvers.add(NoExternalAccess())
        root = etree.fromstring(
            b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
            b'"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
            b'<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            b'<span title="bbox 1 2 3 4">caf&#233; &amp; 8</span></body></html>', parser)
        span = root[0][0]
        self.assertEqual(span.text, 'caf\u00e9 & 8')
        self.assertEqual(span.get('title'), 'bbox 1 2 3 4')
        span.set('title', 'bbox 5 6 7 8')
        reparsed = self.parse(etree.tostring(root))
        self.assertEqual(reparsed[0][0].get('title'), 'bbox 5 6 7 8')
        self.assertEqual(reparsed[0][0].text, span.text)


if __name__ == '__main__':
    unittest.main()
