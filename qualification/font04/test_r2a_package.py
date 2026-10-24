"""Real-corpus generator regressions; writes only temporary review PDFs.

Run: python -m unittest qualification.font04.test_r2a_package
Requires the R2a local corpus and its frozen review-font helper.
"""
from collections import defaultdict
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pikepdf

from qualification.font04.metrics import inspect, render
from qualification.font04.r2a_blind_review import LOCAL, rejected_context, bounds, context_crop
from qualification.font04.r2a_metrics import bind, load_snapshot
from qualification.font04.r2a_package_checks import member_mask, check_panel, candidate_arm


class PackageRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='font04-package-test-')
        cls.data = {}
        for group in ('mixed', 'financial'):
            source = LOCAL/f'export/{group}-observations'
            rows = load_snapshot(source/'source.json')['rows']
            obs = json.loads((source/'observations.json').read_text())
            choices = defaultdict(list)
            for p in json.loads((source/'plan.json').read_text())['fits']:
                if obs[p['member']]['frame'] is not None and obs[p['canonical']]['canonical'] is not None:
                    choices[p['member']].append(p)
            pairs = {i: min(pp, key=lambda p: (len(p['reasons']), p['error'], p['canonical']))
                     for i, pp in choices.items()}
            default = LOCAL/f'baseline/{group}-off.pdf'
            geometry = json.loads(Path(str(default)+'.json').read_text())['pages']
            bindings = bind(rows, inspect(default), geometry)
            cls.data[group] = dict(rows=rows, obs=obs, pairs=pairs, default=default, bindings=bindings)
        old = json.loads((LOCAL/'blind-private/sealed-key.json').read_text())
        # Locate the actual reported Term collage in decoded public order.
        panels = json.loads((LOCAL/'blind-review/panels.json').read_text())
        cls.term = old[panels[155]['id']]['metadata']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def generate(self, group, member, pair=None):
        d = self.data[group]
        directory = Path(tempfile.mkdtemp(dir=self.temp.name))
        path = directory/'context.pdf'
        pairs = dict(d['pairs'])
        if pair is not None:
            pairs[member] = pair
        mapping = rejected_context(d['default'], path, d['rows'], d['bindings'],
                                   d['obs'], pairs, {member}, directory,
                                   LOCAL/'export/font04_r2a_review')
        i, page = next(iter(mapping.items()))
        return d, path, i, page

    def assert_context(self, d, path, i, page):
        row = d['rows'][i]
        for engine in ('pdfium', 'poppler'):
            current = render(d['default'], row['page'], 300, engine)
            candidate = render(path, page, 300, engine)
            crop = [0, 0, current.shape[1], current.shape[0]]
            # Test the same bounded presentation used by the package generator.
            # Font and CID mapping assertions below independently catch aliasing.
            candidate, _ = candidate_arm(current, candidate, crop, [row])
            outside = ~member_mask(current.shape, crop, [row])
            self.assertEqual(int(np.count_nonzero((current != candidate) & outside)), 0, engine)
        with pikepdf.open(d['default']) as original, pikepdf.open(path) as proposed:
            a = original.pages[row['page']].Resources.Font.F1
            b = proposed.pages[page].Resources.Font.F1
            self.assertEqual(a.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes(),
                             b.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes())
            self.assertEqual(a.DescendantFonts[0].CIDToGIDMap.read_bytes(),
                             b.DescendantFonts[0].CIDToGIDMap.read_bytes())
            self.assertNotEqual(b.objgen, proposed.pages[page].Resources.Font.R2aProbe.objgen)

    def test_rejected_and_registered_fixture_keep_default_context(self):
        # The first decoded panel was a lone r in Lord; also exercise a real fixture.
        d, path, i, page = self.generate('financial', 1616)
        self.assert_context(d, path, i, page)
        fixtures = json.loads(Path('/tmp/scanweave-font04-product/crates/scanweave-io/tests/fixtures/glyph-sharing-regressions.json').read_text())['cases']
        case = next(c for c in fixtures if 'B1prime' not in c['source'])
        d, path, i, page = self.generate('financial', case['member'],
                                       dict(member=case['member'], canonical=case['canonical'], parameters=case['parameters']))
        self.assert_context(d, path, i, page)

    def test_term_reference_is_raw_scan_and_candidate_has_no_collage(self):
        m = self.term
        d, path, i, page = self.generate(m['document'], m['member'])
        self.assert_context(d, path, i, page)
        row = d['rows'][i]
        crop = bounds(row, d['rows'])
        x, y, xx, yy = crop
        for engine in ('pdfium', 'poppler'):
            # Exercise the generator's full-page crop path in both renderers.
            source = context_crop(Path(f"qualification/pdf_packaging/groups/{m['document']}-input.pdf"), row['page'], crop, engine)
            current = render(d['default'], row['page'], 300, engine)[y:yy, x:xx]
            candidate = context_crop(path, page, crop, engine)
            word = [r for r in d['rows'] if (r['page'], r['span_id']) == (row['page'], row['span_id'])]
            result = check_panel(dict(source=source, current=current, candidate=candidate), crop, [row], word)
            self.assertEqual(result['outside_target_changed_pixels'], 0)
            self.assertLessEqual(max(result['black_fraction'].values()), .5)
            self.assertEqual(result['missing_source_glyphs'], [])

    def test_mixed_36_changes_b_only_and_preserves_u_and_t(self):
        d, path, i, page = self.generate('mixed', 36)
        self.assertEqual(d['rows'][i]['character'], 'b')
        canonical = d['pairs'][36]['canonical']
        self.assertEqual(d['obs'][canonical]['label'], 'b')
        self.assert_context(d, path, i, page)
        word = [r for r in d['rows'] if (r['page'], r['span_id']) ==
                (d['rows'][i]['page'], d['rows'][i]['span_id'])]
        self.assertEqual(''.join(r['character'] for r in word), 'but')
        for engine in ('pdfium', 'poppler'):
            a = render(d['default'], word[0]['page'], 300, engine)
            b = render(path, page, 300, engine)
            for row in word[1:]:
                x, y, xx, yy = map(int, row['bbox'])
                np.testing.assert_array_equal(a[y:yy, x:xx], b[y:yy, x:xx])


if __name__ == '__main__':
    unittest.main()
