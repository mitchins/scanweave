"""FONT-04 S2a reviewer evaluation: witness quorum (cover-2.0-ceiling-q3) vs cover-2.0-ceiling.

Oracle labels are used for analysis only. Census method is r2c_census (sidecar page reports,
highest-IoU join, class, font-outline xor) applied to every development set.
"""
import json
from collections import Counter
from pathlib import Path
from qualification.font04.s1d_eval import join, classify, shape_xor

ROOT = Path(__file__).resolve().parents[2]
L = ROOT / 'qualification/font04/local'
OUT = ROOT / 'qualification/font04/s2a-quorum.json'


def census(path, targets, labels, faces, cache):
    conv = json.loads(Path(str(path) + '.json').read_text())['conversion']
    rows = conv['page_reports'][0]['reconstruction']['observations']
    joined = join([{'id': r['symbol_id'], 'bbox': r['bbox_px'], 'character': r['text_hypothesis']} for r in rows], targets)
    g = conv['glyph_sharing']
    by = {d['member']: d for d in g['decisions']}
    counts = Counter()
    for d in g['decisions']:
        if not d['accepted'] or d['member'] == d['canonical']:
            continue
        can = by.get(d['canonical'])
        a, b = joined.get(d['id']), joined.get(can['id']) if can else None
        if a is None or b is None:
            counts['unresolved'] += 1
            continue
        x, y = labels[a], labels[b]
        cls = classify(x, y)
        counts[cls] += 1
        xor = shape_xor(cache, faces, x['face'], y['face'], x['character']) if cls in ('different-family', 'same-family-different-style') else None
        counts['visible'] += cls == 'different-character' or (xor is not None and xor > .2)
        counts['egregious'] += xor is not None and xor >= .4
    counts['substituted'] = g.get('substituted') or 0
    counts['net_outlines_retired'] = g.get('net_outlines_retired') or 0
    counts['font_bytes_saved'] = (g.get('encoded_font_bytes_before') or 0) - (g.get('encoded_font_bytes_after') or 0)
    return counts


def main():
    cache, report = {}, {}
    sets = []
    for name, base, prereg in (('P2prime', L/'P2prime', 'p2prime-preregistration.json'), ('P2', L/'P2', 'p2-preregistration-v1.1.json')):
        sub = base/('p2prime' if name == 'P2prime' else 'p2')
        obs = [json.loads(s) for s in (sub/'observations.jsonl').read_text().splitlines()]
        lab = {r['id']: r for r in map(json.loads, (sub/'oracle/labels.jsonl').read_text().splitlines())}
        faces = {f['name']: f['path'] for f in json.loads((ROOT/'qualification/font04'/prereg).read_text())['faces']}
        ceiling = (lambda i, b=base: b/f'sheet-{i}-cover-2.0-ceiling.pdf') if name == 'P2prime' else (lambda i: L/f'S1d/runs/p2-{i}-ceiling.pdf')
        prefix = 'p2prime' if name == 'P2prime' else 'p2'
        for i in range(9):
            sets.append((name, i, [o for o in obs if o['page'] == i//3 and o['sheet'] == i % 3], lab, faces,
                         ceiling(i), L/f'S2/runs/{prefix}-{i}-q3.pdf'))
    f01faces = {f['name']: f['path'] for s in json.loads((ROOT/'qualification/font01/fixture-manifest.json').read_text())['split_records'] for f in s['faces']}
    for split in ('train', 'validation', 'test'):
        base = ROOT/f'qualification/font01/local/corpus-font01-v1/{split}'
        obs = [json.loads(s) for s in (base/'observations.jsonl').read_text().splitlines()]
        lab = {r['id']: r for r in map(json.loads, (base/'oracle/labels.jsonl').read_text().splitlines())}
        for i in range(3):
            sets.append((f'FONT-01 {split}', i, [o for o in obs if o['page'] == i], lab, f01faces,
                         L/f'S1d/runs/font01-{split}-{i}-ceiling.pdf', L/f'S2/runs/font01-{split}-{i}-q3.pdf'))
    for name, i, targets, lab, faces, ceiling, q3 in sets:
        arms = report.setdefault(name, {'cover-2.0-ceiling': Counter(), 'cover-2.0-ceiling-q3': Counter()})
        arms['cover-2.0-ceiling'].update(census(ceiling, targets, lab, faces, cache))
        arms['cover-2.0-ceiling-q3'].update(census(q3, targets, lab, faces, cache))
    for doc in ('financial', 'mixed'):
        arms = report.setdefault(doc, {})
        for arm, path in (('cover-2.0-ceiling', L/f'S1d/runs/{doc}-ceiling.pdf'), ('cover-2.0-ceiling-q3', L/f'S2/runs/{doc}-q3.pdf')):
            g = json.loads(Path(str(path) + '.json').read_text())['conversion']['glyph_sharing']
            arms[arm] = Counter(substituted=g['substituted'], net_outlines_retired=g['net_outlines_retired'],
                                font_bytes_saved=g['encoded_font_bytes_before'] - g['encoded_font_bytes_after'],
                                pdf_bytes=path.stat().st_size)
    out = {k: {a: dict(c) for a, c in v.items()} for k, v in report.items()}
    OUT.write_text(json.dumps(dict(schema='font04-s2a-quorum-v1', produced_by='reviewer (Claude)', oracle_use='analysis only', results=out), indent=1) + '\n')
    for k, v in out.items():
        print(k)
        for a, c in v.items():
            print('  ', a, {x: c.get(x, 0) for x in ('substituted', 'net_outlines_retired', 'font_bytes_saved', 'same-face', 'different-family', 'same-family-different-style', 'different-character', 'visible', 'egregious')})


if __name__ == '__main__':
    main()
