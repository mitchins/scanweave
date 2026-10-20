"""Exercise the real region-OCR parser options without running its OCR side effects."""
import ast
from pathlib import Path
import tempfile
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
