"""Source-only field prototype; does not change groups, trace outlines, or emit PDFs.

Input is an existing R2a instrumented export. No oracle data is loaded. This
exploratory program is not a native implementation or a review package.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from qualification.font04.geometry import register


def prototype(rows, group):
    ids = group['members']
    fields = {i: np.asarray(rows[i]['field'], dtype=float).reshape(64, 64) for i in ids}
    # Source-to-source registration is required: planner fits register a traced
    # candidate to a source, and are not interchangeable with these transforms.
    scores = {}
    for i in ids:
        errors = []
        for j in ids:
            if i != j:
                _, aligned = register(fields[i], fields[j])
                errors.append(float(np.mean((fields[i] - aligned) ** 2)))
        scores[i] = float(np.median(errors)) if errors else 0.0
    witness = min(ids, key=lambda i: (scores[i], i))
    aligned = [fields[witness] if i == witness else register(fields[witness], fields[i])[1] for i in ids]
    # k is fixed here before examining results. Fewer than three falls back to A.
    consensus = np.median(np.stack(aligned), axis=0) if len(ids) >= 3 else fields[witness]
    return {'canonical': group['canonical'], 'members': ids, 'witness': witness,
            'scores': scores, 'consensus_used': len(ids) >= 3,
            'consensus_mse_to_witness': float(np.mean((consensus-fields[witness])**2))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('export', type=Path)
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    rows = json.loads((args.export / 'observations.json').read_text())
    groups = json.loads((args.export / 'plan.json').read_text())['groups']
    print(json.dumps({'status': 'exploratory-unvalidated', 'k': 3,
                      'group_count': len(groups),
                      'groups': [prototype(rows, g) for g in groups[:args.limit]]}, indent=2))


if __name__ == '__main__':
    main()
