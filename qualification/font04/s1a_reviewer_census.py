"""FONT-04 S1a substitution census (reviewer-produced). Analysis only; oracle labels never feed inference.

Joins the product's own glyph-sharing decisions (output.pdf.json) to the P2 oracle through the
S1a spatial join (s1a-join.json, single_best records only), classifies each member/canonical pair,
and measures font-level shape distance for cross-face substitutions.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'qualification/font04/local'
OUT = ROOT / 'qualification/font04/s1a-census.json'


def glyph(cache, faces, face, ch):
    if (face, ch) not in cache:
        im = Image.new('L', (400, 400), 0)
        ImageDraw.Draw(im).text((100, 50), ch, font=ImageFont.truetype(faces[face], 200), fill=255)
        a = np.asarray(im) > 127
        ys, xs = np.nonzero(a)
        cache[face, ch] = a[ys.min():ys.max()+1, xs.min():xs.max()+1]
    return cache[face, ch]


def shape_xor(cache, faces, f1, f2, ch):
    """Height-normalised, centred XOR/union between two faces' outlines of one character."""
    a, b = glyph(cache, faces, f1, ch), glyph(cache, faces, f2, ch)
    h = a.shape[0]
    b = np.asarray(Image.fromarray(b.astype(np.uint8)*255).resize((max(1, round(b.shape[1]*h/b.shape[0])), h))) > 127
    w = max(a.shape[1], b.shape[1]) + 4
    A, B = np.zeros((h, w), bool), np.zeros((h, w), bool)
    A[:, (w-a.shape[1])//2:(w-a.shape[1])//2+a.shape[1]] = a
    B[:, (w-b.shape[1])//2:(w-b.shape[1])//2+b.shape[1]] = b
    return float((A ^ B).sum() / max(1, (A | B).sum()))


def auc(pos, neg):
    pos, neg = np.asarray(pos)[:, None], np.asarray(neg)[None, :]
    return float((pos > neg).mean() + .5*(pos == neg).mean())


def main():
    join = json.loads((ROOT/'qualification/font04/s1a-join.json').read_text())
    oracle = {r['id']: r for r in map(json.loads, (LOCAL/'P2/p2/oracle/labels.jsonl').read_text().splitlines())}
    faces = {f['name']: f['path'] for f in json.loads((ROOT/'qualification/font04/p2-preregistration-v1.1.json').read_text())['faces']}
    totals, rows, cache = Counter(), [], {}
    for n in range(9):
        jrec = {r['source_id']: r for r in join['sheets'][n]['records']}
        obs = json.loads((LOCAL/f'S1/instrumented-{n}/observations.json').read_text())
        sharing = json.loads((LOCAL/f'S1/instrumented-{n}/output.pdf.json').read_text())['conversion']['glyph_sharing']

        def label(i):
            if i is None:
                return None
            r = jrec[obs[i]['id']]
            return oracle[r['candidates'][0]['id']] if r['status'] == 'single_best' else None
        for d in sharing['decisions']:
            a, b = label(d['member']), label(d['canonical'])
            if d['canonical'] is None:
                cls = 'no-canonical'
            elif a is None or b is None:
                cls = 'unresolved-join'
            elif d['member'] == d['canonical']:
                cls = 'self'
            elif a['character'] != b['character']:
                cls = 'different-character'
            elif a['face'] == b['face']:
                cls = 'same-face'
            elif a['family'] == b['family']:
                cls = 'same-family-different-style'
            else:
                cls = 'different-family'
            totals[f"{cls}|{'accepted' if d['accepted'] else 'rejected'}"] += 1
            if cls in ('no-canonical', 'unresolved-join', 'self'):
                continue
            row = dict(sheet=n, dpi=(200, 300, 600)[n//3], cls=cls, accepted=d['accepted'], reasons=d['reasons'],
                       member_face=a['face'], canonical_face=b['face'], member_character=a['character'],
                       canonical_character=b['character'], severity=a['severity'], fit_error=d['error'],
                       noise_floor=d['noise_floor'], member_oracle=a['id'], canonical_oracle=b['id'])
            if cls in ('different-family', 'same-family-different-style'):
                row['shape_xor'] = shape_xor(cache, faces, a['face'], b['face'], a['character'])
            rows.append(row)
    acc = [r for r in rows if r['accepted']]
    same_face_ratio = [r['fit_error']/r['noise_floor'] for r in acc if r['cls'] == 'same-face']
    result = dict(
        schema='font04-s1a-census-v1', produced_by='reviewer (Claude)', oracle_use='analysis only',
        decision_totals=dict(sorted(totals.items())),
        accepted_by_dpi_class={f'{k[0]}|{k[1]}': v for k, v in sorted(Counter((r['dpi'], r['cls']) for r in acc).items())},
        accepted_cross_face_pairs=[[f'{k[0]} <- {k[1]}', v] for k, v in Counter((r['member_face'], r['canonical_face']) for r in acc if r['cls'] != 'same-face').most_common()],
        accepted_different_character=[{k: r[k] for k in ('sheet', 'dpi', 'member_character', 'member_face', 'canonical_character', 'canonical_face', 'fit_error')} for r in acc if r['cls'] == 'different-character'],
        accepted_shape_xor_quantiles={c: np.quantile([r['shape_xor'] for r in acc if r['cls'] == c], [.1, .25, .5, .75, .9]).round(4).tolist() for c in ('different-family', 'same-family-different-style')},
        fit_error_over_floor_quantiles={c: np.quantile([r['fit_error']/r['noise_floor'] for r in acc if r['cls'] == c], [.1, .5, .9]).round(4).tolist() for c in ('same-face', 'different-family')},
        fit_error_auc_visible_vs_same_face={str(t): auc([r['fit_error']/r['noise_floor'] for r in acc if r.get('shape_xor', 0) > t or r['cls'] == 'different-character'], same_face_ratio) for t in (.2, .3)},
        rejected_same_face_reasons=Counter(x for r in rows if not r['accepted'] and r['cls'] == 'same-face' for x in r['reasons']).most_common(),
        rows=rows)
    OUT.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'accepted_cross_face_pairs')}, indent=1))


if __name__ == '__main__':
    main()
