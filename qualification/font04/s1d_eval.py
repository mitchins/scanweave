"""FONT-04 S1d evaluation (reviewer). Native cover-2.0-ceiling vs frozen cover-2.0 vs default.

Oracle labels are used for analysis only. Source snapshots and observations come from the traced
frozen cover-2.0 runs; they precede grouping, so they are shared by both sharing arms.
"""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from qualification.font04.s1a_census import iou
from qualification.font04.s1a_reviewer_census import shape_xor

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'qualification/font04/local'
RUNS = LOCAL / 'S1d/runs'
OUT = ROOT / 'qualification/font04/s1d-results.json'


def sidecar(path):
    return json.loads(Path(str(path) + '.json').read_text())['conversion']


def join(rows, targets):
    """Highest-IoU single-glyph oracle match; None when multi-character, tied or absent."""
    result = {}
    for row in rows:
        c = sorted(((iou(row['bbox'], o['bbox']), o['id']) for o in targets), reverse=True)
        c = [x for x in c if x[0] > 0]
        if len(row['character']) == 1 and c and (len(c) == 1 or c[0][0] - c[1][0] > 1e-12):
            result[row['id']] = c[0][1]
    return result


def classify(a, b):
    if a['character'] != b['character']:
        return 'different-character'
    if a['face'] == b['face']:
        return 'same-face'
    return 'same-family-different-style' if a['family'] == b['family'] else 'different-family'


def census(decisions, obs, joined, labels, faces, cache):
    counts, xor_rows = Counter(), []
    for d in decisions:
        if not d['accepted'] or d['canonical'] is None or d['member'] == d['canonical']:
            continue
        ia, ib = joined.get(obs[d['member']]['id']), joined.get(obs[d['canonical']]['id'])
        if ia is None or ib is None:
            counts['unresolved'] += 1
            continue
        a, b = labels[ia], labels[ib]
        cls = classify(a, b)
        x = shape_xor(cache, faces, a['face'], b['face'], a['character']) if cls in ('different-family', 'same-family-different-style') else None
        visible = cls == 'different-character' or (x is not None and x > .2)
        counts[cls] += 1
        counts['visible'] += visible
        counts['egregious'] += x is not None and x >= .4
        if visible:
            xor_rows.append(dict(oracle=ia, cls=cls, character=a['character'], member_face=a['face'], canonical_face=b['face'], shape_xor=x, error=d['error']))
    return counts, xor_rows


def economy(conv):
    g = conv['glyph_sharing']
    keys = ('substituted', 'retired_outlines', 'added_canonicals', 'net_outlines_retired', 'encoded_font_bytes_before', 'encoded_font_bytes_after')
    out = {k: g.get(k) for k in keys}
    out['fallback'] = g.get('fallback')
    out['pdf_bytes'] = conv['candidates'][0]['pdf_bytes'] if conv.get('candidates') else None
    return out


def main():
    cache, report = {}, dict(schema='font04-s1d-results-v1', produced_by='reviewer (Claude)', oracle_use='analysis only',
                             binary_sha256=None, synthetic={}, corpus={})
    p2faces = {f['name']: f['path'] for f in json.loads((ROOT/'qualification/font04/p2-preregistration-v1.1.json').read_text())['faces']}
    p2obs = [json.loads(s) for s in (LOCAL/'P2/p2/observations.jsonl').read_text().splitlines()]
    p2lab = {r['id']: r for r in map(json.loads, (LOCAL/'P2/p2/oracle/labels.jsonl').read_text().splitlines())}
    f01faces = {f['name']: f['path'] for s in json.loads((ROOT/'qualification/font01/fixture-manifest.json').read_text())['split_records'] for f in s['faces']}
    sets = [('P2', n, (200, 300, 600)[n//3], LOCAL/f'S1/instrumented-{n}', LOCAL/f'P2/sheet-{n}-cover-2.0.pdf',
             RUNS/f'p2-{n}-ceiling.pdf', LOCAL/f'P2/sheet-{n}-off.pdf',
             [o for o in p2obs if o['page'] == n//3 and o['sheet'] == n % 3], p2lab, p2faces) for n in range(9)]
    for split in ('train', 'validation', 'test'):
        base = ROOT/f'qualification/font01/local/corpus-font01-v1/{split}'
        obs = [json.loads(s) for s in (base/'observations.jsonl').read_text().splitlines()]
        lab = {r['id']: r for r in map(json.loads, (base/'oracle/labels.jsonl').read_text().splitlines())}
        for i in range(3):
            trace = LOCAL/f'S1/font01/{split}-{i}-cover-2.0'
            sets.append((f'FONT-01 {split}', i, (200, 300, 600)[i], trace, trace/'output.pdf', RUNS/f'font01-{split}-{i}-ceiling.pdf',
                         LOCAL/f'S1/font01/{split}-{i}-off/output.pdf', [o for o in obs if o['page'] == i], lab, f01faces))
    totals = {}
    for name, page, dpi, trace, frozen, ceiling, default, targets, labels, faces in sets:
        rows = json.loads((trace/'source.json').read_text())['rows']
        obs = json.loads((trace/'observations.json').read_text())
        joined = join(rows, targets)
        entry = dict(page=page, dpi=dpi, join_rate=len(joined)/len(rows))
        if name.startswith('FONT-01'):
            fresh = RUNS/f"font01-{name.split()[1]}-{page}-cover-2.0.pdf"
            entry['fresh_cover_2_0_matches_traced'] = fresh.read_bytes() == frozen.read_bytes()
        for arm, path in (('cover-2.0', frozen), ('cover-2.0-ceiling', ceiling)):
            conv = sidecar(path)
            counts, visible = census(conv['glyph_sharing']['decisions'], obs, joined, labels, faces, cache)
            entry[arm] = dict(census=dict(counts), economy=economy(conv), visible_remaining=visible)
            t = totals.setdefault(name, {}).setdefault(arm, Counter())
            t.update(counts)
            t['substituted'] += conv['glyph_sharing'].get('substituted') or 0
            t['net_outlines_retired'] += conv['glyph_sharing'].get('net_outlines_retired') or 0
            t['font_bytes_saved'] += (conv['glyph_sharing'].get('encoded_font_bytes_before') or 0) - (conv['glyph_sharing'].get('encoded_font_bytes_after') or 0)
        entry['default_pdf_bytes'] = default.stat().st_size
        report['synthetic'].setdefault(name, []).append(entry)
    report['synthetic_totals'] = {k: {a: dict(v) for a, v in arms.items()} for k, arms in totals.items()}
    for group in ('forms', 'receipts', 'mixed', 'historical', 'financial'):
        frozen = LOCAL/f'R2a/final/{group}-cover-2.0.pdf'
        if not frozen.exists():
            frozen = LOCAL/f'R2a/paired-final/{group}-cover-2.0.pdf'
        off = frozen.with_name(f'{group}-off.pdf')
        entry = {'default_pdf_bytes': off.stat().st_size if off.exists() else None}
        for arm, path in (('cover-2.0', frozen), ('cover-2.0-ceiling', RUNS/f'{group}-ceiling.pdf')):
            entry[arm] = economy(sidecar(path)) if path.exists() else None
        report['corpus'][group] = entry
    OUT.write_text(json.dumps(report, indent=1) + '\n')
    for k, arms in report['synthetic_totals'].items():
        print(k, {a: {x: v.get(x) for x in ('visible', 'egregious', 'different-character', 'same-face', 'different-family', 'substituted', 'net_outlines_retired', 'font_bytes_saved')} for a, v in arms.items()})
    for g, e in report['corpus'].items():
        print(g, e)


if __name__ == '__main__':
    main()
