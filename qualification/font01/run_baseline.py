"""Reproduce the deterministic and linear arms; all outputs are research only.

Run as python -m qualification.font01.run_baseline CORPUS NEW_OUTPUT.
The corpus must first pass benchmark --verify-manifest. Never use a new test
result to retune this frozen protocol. Oracle labels are evaluator inputs only.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .benchmark import verify_frozen_document
from .evaluation import pair_metrics, threshold_at_fpr
from .linear_metric import fit_metric
from .pair_data import build_pairs
from .registration import deterministic_score


def verify_corpus(corpus, frozen_path):
    frozen = json.loads(frozen_path.read_text())
    expected = {row['split']: row for row in frozen['split_records']}
    if set(expected) != {'train', 'validation', 'test'}:
        raise ValueError('Frozen manifest must specify exactly train/validation/test')
    for split, record in expected.items():
        verify_frozen_document(corpus/split/'manifest.json', record)
    return hashlib.sha256(frozen_path.read_bytes()).hexdigest()


def run(corpus, output, frozen_path=Path(__file__).with_name('fixture-manifest.json')):
    corpus_hash = verify_corpus(corpus, frozen_path)
    output.mkdir(parents=True, exist_ok=False)
    for name, count in [('train', 10000), ('validation', 6000), ('test', 6000)]:
        if name == 'test':
            verify_corpus(corpus, frozen_path)
            frozen = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in (output/'linear-model.json', output/'validation.json')}
            frozen['fixture_manifest_sha256'] = corpus_hash
            (output/'pretest-freeze.json').write_text(json.dumps(frozen, indent=2)+'\n')
        x, y, pairs, timing = build_pairs(corpus/name, count, 10302)
        np.savez_compressed(output/(name+'.npz'), x=x, y=y)
        (output/(name+'-pairs.json')).write_text(json.dumps(pairs, indent=2)+'\n')
        if name == 'train':
            model = fit_metric(x, y)
            model.save(output/'linear-model.json')
            continue
        healthy = np.asarray([pair['severity'] <= 1 for pair in pairs])
        arms = [('deterministic', deterministic_score(x), False),
                ('linear', model.scores(x), True)]
        if name == 'validation':
            thresholds = {arm: threshold_at_fpr(y[healthy], score[healthy])
                          for arm, score, _ in arms}
        results = []
        for arm, scores, probability in arms:
            results.append({'arm': arm, 'threshold': thresholds[arm],
                            'healthy': pair_metrics(y[healthy], scores[healthy], thresholds[arm],
                                                    probabilities=probability),
                            'all': pair_metrics(y, scores, thresholds[arm], probabilities=probability),
                            'qualified_for_product': False})
        (output/(name+'.json')).write_text(json.dumps({'arms': results, 'timing': timing}, indent=2)+'\n')
    verify_corpus(corpus, frozen_path)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.corpus, args.output)


if __name__ == '__main__':
    main()
