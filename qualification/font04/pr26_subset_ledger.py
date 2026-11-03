"""PR #26 subtractive-parity ledger (reviewer).

Compares the repaired q3 build against the qualified q3 build (e61c0dc) on every retained document:
  1. repaired accepted substitutions are a subset of qualified ones;
  2. retained substitutions keep member, canonical, fitted transform and fit error exactly;
  3. no new group or canonical;
  4. final emitted groups satisfy the 3-design quorum (design keys from the qualified cover log);
  5. documents with unchanged accepted sets are byte-identical;
  6. renders differ from qualified only inside removed members' boxes, and there equal default.
"""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
L = ROOT / 'qualification/font04/local'
LOGS = Path(sys.argv[1]) if len(sys.argv) > 1 else None
RUNS = L / os.environ.get('LEDGER_RUNS', 'PR2/runs')
OUT = ROOT / 'qualification/font04' / os.environ.get('LEDGER_OUT', 'pr26-subset-ledger.json')
MARGIN = 3


def documents():
    for i in range(9):
        d = (200, 300, 600)[i // 3]
        yield f'p2pp-{i}', d, L/f'P2pp/sheet-{i}-cover-2.0-ceiling-q3.pdf', L/f'P2pp/sheet-{i}-off.pdf'
        yield f'p2prime-{i}', d, L/f'S2/runs/p2prime-{i}-q3.pdf', L/f'P2prime/sheet-{i}-off.pdf'
        yield f'p2-{i}', d, L/f'S2/runs/p2-{i}-q3.pdf', L/f'P2/sheet-{i}-off.pdf'
    for s in ('train', 'validation', 'test'):
        for i in range(3):
            yield f'font01-{s}-{i}', (200, 300, 600)[i], L/f'S2/runs/font01-{s}-{i}-q3.pdf', L/f'S1/font01/{s}-{i}-off/output.pdf'
    for g in ('financial', 'mixed'):
        yield g, 300, L/f'S2/runs/{g}-q3.pdf', L/f'R2a/baseline/{g}-off.pdf'
    for g in ('forms', 'receipts', 'historical'):
        yield g, 300, LOGS/f'{g}.pdf', L/f'R2a/baseline/{g}-off.pdf'


def sharing(path):
    conv = json.loads(Path(str(path) + '.json').read_text())['conversion']
    boxes = {}
    for page, report in enumerate(conv.get('page_reports', [])):
        for o in report['reconstruction']['observations']:
            boxes[(page, o['symbol_id'])] = o['bbox_px']
    return conv.get('glyph_sharing') or {}, boxes


def cover_keys(name):
    """member index -> design key, from accepted cover candidates in the qualified debug log."""
    keys = {}
    log = LOGS / f'{name}.log'
    if not log.exists():
        return None
    for line in log.read_text().splitlines():
        m = re.match(r'COVERDBG label=\S+ canonical=(\d+) members=\[([^\]]*)\] keys=\d+ memberkeys=\[([^\]]*)\] ACCEPT', line)
        if m:
            for i, k in zip((int(x) for x in m[2].split(',')), re.findall(r'"([^"]+)"', m[3])):
                keys[i] = k
    return keys


def accepted(g):
    return {d['member']: d for d in g.get('decisions', []) if d['accepted'] and d['member'] != d['canonical']}, \
           {d['member']: d for d in g.get('decisions', []) if d['accepted']}


def main():
    ledger, totals = [], defaultdict(int)
    for name, dpi, qualified, default in documents():
        repaired = RUNS / f'{name}.pdf'
        gq, boxes = sharing(qualified)
        gr, _ = sharing(repaired)
        aq, allq = accepted(gq)
        ar, allr = accepted(gr)
        entry = dict(document=name, dpi=dpi, qualified_substitutions=len(aq), repaired_substitutions=len(ar),
                     qualified_owned_exceptions=len(gq.get('owned_exceptions') or []),
                     repaired_owned_exceptions=len(gr.get('owned_exceptions') or []))
        new = [m for m in ar if m not in aq]
        changed = [m for m in ar if m in aq and any(ar[m][k] != aq[m][k] for k in ('canonical', 'fitted_transform', 'error', 'id', 'page'))]
        groups_q = {d['canonical'] for d in allq.values()}
        groups_r = {d['canonical'] for d in allr.values()}
        removed = sorted(m for m in aq if m not in ar)
        entry.update(new_substitutions=len(new), changed_bindings=len(changed), new_groups=len(groups_r - groups_q),
                     removed_substitutions=len(removed),
                     removed_reasons=sorted({r for m in removed for r in next(d for d in gr['decisions'] if d['member'] == m)['reasons']}),
                     removed_detail=[dict(member=m, id=aq[m]['id'], page=aq[m]['page'], canonical=aq[m]['canonical']) for m in removed])
        keys = cover_keys(name)
        if keys is not None:
            members = defaultdict(list)
            for m, d in allr.items():
                members[d['canonical']].append(m)
            missing = [m for ms in members.values() for m in ms if m not in keys]
            low = [c for c, ms in members.items() if len({keys.get(m) for m in ms}) < 3]
            members_q = defaultdict(list)
            for m, d in allq.items():
                members_q[d['canonical']].append(m)
            entry.update(final_groups=len(members), final_quorum_violations=len(low), keys_missing=len(missing),
                         qualified_quorum_violations=sum(len({keys.get(m) for m in ms}) < 3 for ms in members_q.values()))
        else:
            entry.update(final_quorum_violations=None)
        same_set = set(ar) == set(aq) and not changed and not new
        entry['bytes_identical'] = qualified.read_bytes() == repaired.read_bytes()
        entry['bytes_rule_ok'] = (not same_set) or entry['bytes_identical']
        if not entry['bytes_identical']:
            import pikepdf
            from qualification.font04.metrics import render as rnd
            with pikepdf.open(qualified) as pdf:
                pages = len(pdf.pages)
            outside = inside = 0
            for page in range(pages):
                iq, ir, idf = (rnd(p, page, dpi, 'pdfium') for p in (qualified, repaired, default))
                h = min(iq.shape[0], ir.shape[0], idf.shape[0])
                w = min(iq.shape[1], ir.shape[1], idf.shape[1])
                iq, ir, idf = iq[:h, :w], ir[:h, :w], idf[:h, :w]
                mask = np.zeros((h, w), bool)
                changed = [m for m in set(allq) | set(allr) if (allq.get(m) or {}).get('canonical') != (allr.get(m) or {}).get('canonical')]
                src = {**allq, **allr}
                for m in changed:
                    b = boxes.get((src[m]['page'], src[m]['id']))
                    if src[m]['page'] == page and b:
                        x0, y0, x1, y1 = [int(round(v)) for v in b]
                        mask[max(0, y0 - MARGIN):y1 + MARGIN, max(0, x0 - MARGIN):x1 + MARGIN] = True
                outside += int(((iq != ir) & ~mask).sum())
                inside += int(((ir != idf) & mask).sum())
            entry['pixels_changed_outside_removed'] = outside
            entry['removed_regions_equal_default_pixels_differing'] = inside
            entry['render_pages_checked'] = pages
        ledger.append(entry)
        for k in ('qualified_substitutions', 'repaired_substitutions', 'new_substitutions', 'changed_bindings', 'new_groups',
                  'removed_substitutions', 'qualified_owned_exceptions', 'repaired_owned_exceptions'):
            totals[k] += entry[k]
        totals['final_quorum_violations'] += entry.get('final_quorum_violations') or 0
        totals['qualified_quorum_violations'] += entry.get('qualified_quorum_violations') or 0
        totals['bytes_rule_failures'] += not entry['bytes_rule_ok']
        totals['pixels_changed_outside_removed'] += entry.get('pixels_changed_outside_removed', 0)
        print(name, {k: entry.get(k) for k in ('qualified_substitutions', 'repaired_substitutions', 'removed_substitutions', 'new_substitutions',
                                               'changed_bindings', 'final_quorum_violations', 'bytes_identical', 'pixels_changed_outside_removed',
                                               'removed_regions_equal_default_pixels_differing', 'repaired_owned_exceptions')}, flush=True)
    OUT.write_text(json.dumps(dict(schema='pr26-subset-ledger-v1', margin_px=MARGIN, totals=dict(totals), documents=ledger), indent=1) + '\n')
    print(json.dumps(dict(totals), indent=1))


if __name__ == '__main__':
    main()
