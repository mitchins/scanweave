"""Audit the completed R2a package repair, including the now-open R2a v1 key.

This command reads product PDFs and both packages; it never regenerates product
output or decodes the v2 key. It writes only local audit data and the small receipt.
"""
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

from qualification.font04.metrics import render, sha
from qualification.font04.r2a_blind_review import LOCAL, ROOT
from qualification.font04.r2a_package_checks import validate

REPORTED = [77,120,133,155,348,370,424,469,478,479,491,540,543,560,785,829,898,938,960,1056,
            1067,1091,1120,1285,1324,1346,1391,1445,1447,1586]


def product_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for directory in ('baseline', 'final')
            for p in sorted((LOCAL/directory).glob('*.pdf'))}


def main():
    staging, public = LOCAL/'blind-private-staging-v2', LOCAL/'blind-review-v2'
    before = json.loads((LOCAL/'package-fix-product-hashes.json').read_text())
    after = product_hashes()
    assert before == after, 'Product PDF changed'
    accepted = json.loads((ROOT/'qualification/font04/r2a-corpus.json').read_text())['documents']
    for group, evidence in accepted.items():
        for suffix, field in [('off', 'default_pdf_sha256'), ('cover-2.0', 'sharing_pdf_sha256')]:
            hashes = {h for path, h in after.items() if path.endswith(f'/{group}-{suffix}.pdf')}
            assert hashes == {evidence[field]}, ('Accepted product hash mismatch', group, suffix)
    testlog = (LOCAL/'package-fix-tests.log').read_text()
    assert 'Ran 3 tests' in testlog and testlog.rstrip().endswith('OK'), 'Regressions have not passed'
    validation = validate(staging, LOCAL/'export')
    assert validation['pass_all'], validation
    key = json.loads((LOCAL/'blind-private/sealed-key.json').read_text())
    panels = json.loads((LOCAL/'blind-review/panels.json').read_text())
    new_metadata = {p['asset']: p for p in json.loads((staging/'panels.json').read_text())}
    assert len(new_metadata) == len(key)
    assert json.loads((staging/'selection.json').read_text()) == json.loads((LOCAL/'blind-private-staging/selection.json').read_text()), 'Review population changed'
    fonts = list((LOCAL/'blind-private-staging').glob('**/counterfactual.ttf'))
    for font in fonts:
        assert sha(font) == sha(staging/font.relative_to(LOCAL/'blind-private-staging')), 'Counterfactual font changed'
    for token, k in key.items():
        asset = k['metadata']['asset']
        assert asset in new_metadata
        for field, value in k['metadata'].items():
            assert new_metadata[asset][field] == value, ('Panel identity changed', asset, field)
        assert sha(LOCAL/'blind-review/assets'/f"{token}-{k['source']}.png") == sha(staging/'assets'/f"{asset}-source.png"), ('Raw source changed', asset)
    cache, evidence = {}, []
    for index in REPORTED:
        p = panels[index]
        k = key[p['id']]
        m = k['metadata']
        identity = m['document'], m['page'], m['renderer']
        if identity not in cache:
            cache[identity] = render(ROOT/f"qualification/pdf_packaging/groups/{m['document']}-input.pdf",
                                     m['page'], 300, m['renderer'])
        x,y,xx,yy = m['bounds']
        raw = cache[identity][y:yy,x:xx]
        with Image.open(LOCAL/'blind-review/assets'/f"{p['id']}-{k['source']}.png") as im:
            source = np.asarray(im.convert('L'))
        assert np.array_equal(raw, source), ('Source was not a raw scan crop', index)
        evidence.append(dict(index=index, panel=p['id'], asset=m['asset'], type=m['type'],
                             source_label=k['source'], candidate_label=k['candidate'],
                             source_exact_raw_scan=True))
    (staging/'decoded-v1-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    seal = json.loads((public/'seal-receipt.json').read_text())
    oldseal = json.loads((LOCAL/'blind-review/seal-receipt.json').read_text())
    assert oldseal == json.loads((ROOT/'qualification/font04/r2a-blind-review.json').read_text())['receipt']
    assert sha(LOCAL/'blind-review/blinded-review.pdf') == oldseal['review_sha256']
    assert sha(LOCAL/'blind-private/sealed-key.json') == oldseal['key_sha256']
    assert seal['key_sha256'] != oldseal['key_sha256']
    assert seal['review_sha256'] == sha(public/'blinded-review.pdf')
    assert seal['key_sha256'] == sha(LOCAL/'blind-private-v2/sealed-key.json')
    # Verify every public asset survived sealing byte-for-byte, without opening
    # the new key contents. Compare the multisets of asset digests across the boundary.
    a = Counter(sha(p) for p in (staging/'assets').glob('*.png'))
    b = Counter(sha(p) for p in (public/'assets').glob('*.png'))
    assert a == b
    result = dict(schema='font04-r2a-package-fix-v1', status='PASS; package repair only; P2 unopened',
                  package=str(public.relative_to(ROOT)), receipt=seal,
                  validation=validation,
                  regression_tests=dict(command='python -m unittest qualification.font04.test_r2a_package',
                                        tests=3, status='PASS', log_sha256=sha(LOCAL/'package-fix-tests.log')),
                  cause='pikepdf copy_foreign memoizes imports: mutating the imported probe font also replaced the default /F1 font on every copied page. Clone the font dictionary before installing the probe descendants.',
                  reported_reference_defects=dict(count=30, indices=REPORTED, source_exact_raw_scan=30,
                      decoded_arm='candidate', cause='Same font-resource alias; not source crop, mask or clipping.',
                      evidence=str((staging/'decoded-v1-evidence.json').relative_to(ROOT))),
                  mixed_member36=dict(target='b', word='but', canonical_label='b',
                      cause='Default /F1 was aliased to reduced probe font with Identity CIDToGIDMap; neighboring u and t used unrelated GIDs. Not a canonical lookup, bounds or intentional multi-glyph replacement.',
                      fixed='Original font and CIDToGIDMap preserved; u and t pixel-identical in both renderers.'),
                  poppler_render_fix='Render complete pages before cropping in every arm; Poppler region rendering changed antialiasing outside the target.',
                  region_render_pixels_corrected=sum(p.get('region_render_pixels_corrected', 0) for p in new_metadata.values()),
                  source_policy='Raw scan crop from the frozen image-only matched group input, at 300 dpi in the panel renderer. No isolated ownership or knocked-out source layer. All 30 reported references were already exact raw scan crops; blind arm inference had confused candidates with sources.',
                  source_arms_unchanged_from_raw_v1=len(key),
                  selection_unchanged=True, counterfactual_fonts_byte_identical=len(fonts),
                  presentation_policy='Default pixels outside target bounds plus 2 px; repeated-word targets are the union of their member windows. Restored pixel counts are recorded per panel; no transform or canonical changed.',
                  product_pdfs_unchanged=before==after, product_hashes_match_accepted_r2a=True, product_pdf_hashes=after,
                  public_assets_exact_staging=True, new_key_decoded=False,
                  old_seal_unchanged=oldseal,
                  scope='No product code, PDFs, method, thresholds, P2, PR or merge changes.')
    (ROOT/'qualification/font04/r2a-package-fix.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','validation','product_pdfs_unchanged')},indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['snapshot']:
        (LOCAL/'package-fix-product-hashes.json').write_text(json.dumps(product_hashes(),indent=2)+'\n')
    else:
        main()
