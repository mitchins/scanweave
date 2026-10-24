"""Pixel invariants for review assets; no product or inference changes."""
import json
import math

import numpy as np
from PIL import Image


def member_mask(shape, crop, rows, padding=2):
    mask = np.zeros(shape, dtype=bool)
    x, y, _, _ = crop
    for row in rows:
        a, b, c, d = row['bbox']
        left, top = max(0, math.floor(a)-padding-x), max(0, math.floor(b)-padding-y)
        right, bottom = min(shape[1], math.ceil(c)+padding-x), min(shape[0], math.ceil(d)+padding-y)
        mask[top:bottom, left:right] = True
    return mask


def candidate_arm(current, proposed, crop, targets):
    """Replace only the target patch in the rendered default-context page.

    Frozen counterfactual transforms can put an antialias fringe beyond the
    requested review window. The arm contract uses the target bounds plus 2 px;
    preserve the exact current pixels outside it. Never change the transform,
    canonical, product output, or metric inputs to satisfy this presentation rule.
    """
    mask = member_mask(current.shape, crop, targets)
    outside = (current != proposed) & ~mask
    result = current.copy()
    result[mask] = proposed[mask]
    return result, dict(restored_context_pixels=int(np.count_nonzero(outside)),
                        max_restored_delta=int(np.max(np.abs(current.astype(int)-proposed.astype(int))[outside]))
                        if np.any(outside) else 0)


def check_panel(arrays, crop, targets, word):
    """Check exact locality and real dark ink, rather than just nonwhite paper."""
    black = {name: float(np.mean(a < 128)) for name, a in arrays.items()}
    outside = int(np.count_nonzero((arrays['candidate'] != arrays['current']) &
                                  ~member_mask(arrays['current'].shape, crop, targets)))
    source = arrays['source']
    # Every nonempty OCR glyph box must contain ink darker than its local paper.
    cutoff = min(192, float(np.median(source))-20)
    missing = []
    x, y, _, _ = crop
    for row in word:
        a, b, c, d = row['bbox']
        box = source[max(0, math.floor(b)-y):min(source.shape[0], math.ceil(d)-y),
                     max(0, math.floor(a)-x):min(source.shape[1], math.ceil(c)-x)]
        if not np.any(box < cutoff):
            missing.append(row['index'])
    return dict(black_fraction=black, outside_target_changed_pixels=outside,
                missing_source_glyphs=missing, source_ink_cutoff=cutoff, source_glyph_boxes_checked=len(word))


def validate(staging, source_root):
    panels = json.loads((staging/'panels.json').read_text())
    snapshots = {g: json.loads((source_root/f'{g}-observations/source.json').read_text())['rows']
                 for g in {p['document'] for p in panels}}
    failures, results = [], []
    for p in panels:
        rows = snapshots[p['document']]
        ids = p.get('draws', [p.get('draw')])
        targets = [rows[i] for i in ids]
        first = targets[0]
        word = [r for r in rows if (r['page'], r['span_id']) == (first['page'], first['span_id'])]
        if 'bounds' in p:
            crop = p['bounds']
        else:
            from qualification.font04.r2a_blind_review import bounds
            crop = bounds(first, rows)
        arrays = {}
        for role in ('source', 'current', 'candidate'):
            with Image.open(staging/'assets'/f"{p['asset']}-{role}.png") as im:
                arrays[role] = np.asarray(im.convert('L')).copy()
        result = dict(asset=p['asset'], type=p['type'], **check_panel(arrays, crop, targets, word))
        results.append(result)
        if max(result['black_fraction'].values()) > .5 or result['outside_target_changed_pixels'] or result['missing_source_glyphs']:
            failures.append(result)
    report = dict(panels=len(panels), arms=3*len(panels),
                  max_black_fraction=max(max(r['black_fraction'].values()) for r in results),
                  outside_target_changed_pixels=sum(r['outside_target_changed_pixels'] for r in results),
                  missing_source_glyph_boxes=sum(len(r['missing_source_glyphs']) for r in results),
                  source_glyph_boxes_checked=sum(r['source_glyph_boxes_checked'] for r in results),
                  target_window_padding_px=2,
                  repeated_word_target='union of all word member bounds',
                  presentation_restored_context_pixels=sum(p.get('presentation', {}).get('restored_context_pixels', 0) for p in panels),
                  presentation_panels_with_restoration=sum(p.get('presentation', {}).get('restored_context_pixels', 0) > 0 for p in panels),
                  failures=failures, pass_all=not failures)
    (staging/'pixel-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report
