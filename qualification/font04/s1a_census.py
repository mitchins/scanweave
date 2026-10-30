"""FONT-04 S1a spatial join gate. Does not run the product or change P2.

The oracle crops are padded and overlap. An exact largest-IoU tie is ambiguous;
multi-character source occurrences require a multi-glyph mapping and cannot be
assigned one oracle glyph. Lower-confidence matches are reported separately.
"""
import json
from pathlib import Path
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'qualification/font04/local'
OUT = ROOT / 'qualification/font04/s1a-join.json'

def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])

def iou(a, b):
    intersection = area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])
    return intersection / (area(a) + area(b) - intersection) if intersection else 0.0

def dist(values):
    if not values:
        return None
    return dict(zip(('min', 'p05', 'p25', 'median', 'p75', 'p95', 'max'),
                    map(float, np.quantile(values, [0, .05, .25, .5, .75, .95, 1]))))

def main():
    oracle = [json.loads(s) for s in (BASE/'P2/p2/observations.jsonl').read_text().splitlines()]
    sheets = []
    all_records = []
    for n in range(9):
        rows = json.loads((BASE/f'S1/instrumented-{n}/source.json').read_text())['rows']
        targets = [x for x in oracle if x['page'] == n//3 and x['sheet'] == n%3]
        records = []
        for row in rows:
            candidates = sorted(((iou(row['bbox'], o['bbox']), o) for o in targets), key=lambda x: (-x[0], x[1]['id']))
            candidates = [(v, o) for v, o in candidates if v > 0]
            ties = len(candidates) > 1 and abs(candidates[0][0] - candidates[1][0]) < 1e-12
            status = ('unmatched' if not candidates else 'multi_character' if len(row['character']) != 1
                      else 'ambiguous_tie' if ties else 'single_best')
            record = dict(index=row['index'], occurrence=row['occurrence'], source_id=row['id'],
                          span_id=row['span_id'], character=row['character'], bbox=row['bbox'], status=status,
                          candidates=[dict(id=o['id'], character=o['character'], bbox=o['bbox'], iou=v) for v,o in candidates])
            if candidates:
                record['best_iou'] = candidates[0][0]
                record['best_character_agrees'] = row['character'] == candidates[0][1]['character']
                record['best_margin'] = candidates[0][0] - (candidates[1][0] if len(candidates)>1 else 0)
            records.append(record)
        counts = Counter(r['status'] for r in records)
        best = [r for r in records if 'best_iou' in r]
        singles = [r for r in records if r['status'] == 'single_best']
        sheets.append(dict(sheet_index=n, dpi=(200,300,600)[n//3], page=n//3, sheet=n%3,
                           source_occurrences=len(records), status_counts=dict(counts),
                           unambiguous_single_glyph_rate=len(singles)/len(records),
                           any_overlap_rate=len(best)/len(records),
                           best_iou_distribution=dist([r['best_iou'] for r in best]),
                           best_character_agreement_rate=sum(r['best_character_agrees'] for r in best)/len(best) if best else None,
                           single_best_character_agreement_rate=sum(r['best_character_agrees'] for r in singles)/len(singles) if singles else None,
                           single_best_iou_below_0_2=sum(r['best_iou'] < .2 for r in singles),
                           single_best_margin_below_0_05=sum(r['best_margin'] < .05 for r in singles),
                           records=records))
        all_records.extend(records)
    counts=Counter(r['status'] for r in all_records)
    rate=counts['single_best']/len(all_records)
    output=dict(method='Largest box IoU within the same page and sheet. Oracle boxes are padded, so overlaps alone do not imply a tie. Multi-character sources are retained as unresolved multi-glyph joins, not assigned an arbitrary single oracle. Exact ties are ambiguous. Single-best is a liberal upper bound on reliable single-glyph joins; weak overlaps and small margins are separately counted.',
                bbox_coordinate_check='Source boxes directly overlap native-DPI oracle boxes without rescaling; per-sheet IoUs are reported.',
                total_source_occurrences=len(all_records), status_counts=dict(counts),
                unambiguous_single_glyph_rate=rate, gate_98_percent_pass=rate>=.98, sheets=sheets)
    OUT.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='sheets'},indent=2))
    for s in sheets:
        print(s['sheet_index'],s['source_occurrences'],s['status_counts'],round(s['unambiguous_single_glyph_rate'],4),round(s['best_character_agreement_rate'],4),s['best_iou_distribution']['median'])
    if not output['gate_98_percent_pass']:
        print('STOP: join gate failed; no census or further analysis performed.')

if __name__ == '__main__':
    main()
