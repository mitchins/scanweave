"""Reviewer's own stratified selection. Writes shuffled IDs (public) and a stratum map (sealed until grading is hashed). Never reads candidate/current."""
import json, random
from pathlib import Path
S = Path(__file__).parent; L = Path('qualification/font04/local')
k = json.load(open(L/'B2prime-review-keys/key.json'))
m = {pid: v['metadata'] for pid, v in k.items()}
rng = random.Random(20261024)
sel = {}
def pick(pred, n, tag):
    ids = sorted(p for p, x in m.items() if pred(x) and p not in sel); rng.shuffle(ids)
    for p in ids[:n]: sel[p] = tag
new = lambda pt, r='pdfium': (lambda x: x.get('type') == 'accepted' and x.get('point') == pt and x.get('newly_admitted') and x['renderer'] == r)
pick(new('cover-2.0'), 80, 'new-cover-2.0')
pick(new('star-1.5'), 60, 'new-star-1.5')
pick(new('star-2.0'), 40, 'new-star-2.0')
pick(new('cover-2.0', 'poppler'), 40, 'new-cover-2.0-poppler')
# worst regressions from my independent rescore (cover-2.0, substituted)
rs = json.load(open(S.parent/'rescore_b2p.json'))
worst = sorted((r for r in rs if r['cover-2.0_sub']), key=lambda r: r['default']-r['cover-2.0'])[:25]
wm = {r['member'] for r in worst}
pick(lambda x: x.get('type') == 'accepted' and x.get('point') == 'cover-2.0' and x.get('member') in wm and x['renderer'] == 'pdfium', 25, 'worst-rescore-cover-2.0')
pick(lambda x: x.get('type') == 'rejected' and x['renderer'] == 'pdfium', 80, 'rejected')
pick(lambda x: x.get('type') == 'mandatory-regression-or-owned-attempt' and x['renderer'] == 'pdfium', 34, 'mandatory')
pick(lambda x: x.get('type') == 'repeated-word' and x.get('point') == 'cover-2.0' and x['renderer'] == 'pdfium', 20, 'word-cover-2.0')
ids = list(sel); rng.shuffle(ids)
json.dump(ids, open(S/'order.json', 'w'))
json.dump(sel, open(S/'strata.sealed.json', 'w'))
print(len(ids), 'selected;', len(wm), 'worst members,', sum(1 for v in sel.values() if v.startswith('worst')), 'found in panels')
