"""Explicit evaluator label joins and frozen, severity-balanced pair sampling."""
import json
from pathlib import Path
import time

import numpy as np

from .observations import load_observations, source_path
from .registration import attach_registration_candidates, compare


def evaluator_labels(directory):
    root = Path(directory).resolve(strict=True)
    rows = [json.loads(line) for line in source_path(root, 'oracle/labels.jsonl').read_text().splitlines()]
    labels = {row['id']: row for row in rows}
    if len(labels) != len(rows):
        raise ValueError('Duplicate evaluator labels')
    return labels


def validate_evaluator_join(directory, labels):
    root = Path(directory).resolve(strict=True)
    rows = [json.loads(line) for line in source_path(root, 'observations.jsonl').read_text().splitlines()]
    source = {row['id']: row for row in rows}
    if len(source) != len(rows) or set(source) != set(labels):
        raise ValueError('Evaluator labels must match the complete source ID set')
    if any(row['character'] != labels[identifier]['character'] for identifier, row in source.items()):
        raise ValueError('Evaluator character differs from source observation')


def pair_candidates(observations, labels):
    by_character = {}
    for index, row in enumerate(observations):
        by_character.setdefault(row.character, []).append(index)
    buckets = {(same, severity): [] for same in (False, True) for severity in range(5)}
    for indices in by_character.values():
        for position, first in enumerate(indices):
            for second in indices[position+1:]:
                a, b = labels[observations[first].identifier], labels[observations[second].identifier]
                same = a['font_sha256'] == b['font_sha256']
                severity = max(a['severity'], b['severity'])
                buckets[(same, severity)].append((first, second))
    return buckets


def sample_pairs(observations, labels, count, seed):
    if count < 10:
        raise ValueError('Pair budget must cover ten class/severity strata')
    rng = np.random.default_rng(seed)
    result = []
    for candidates in pair_candidates(observations, labels).values():
        chosen = rng.choice(len(candidates), size=min(count//10, len(candidates)), replace=False)
        result.extend(candidates[index] for index in chosen)
    rng.shuffle(result)
    return result


def pair_record(first, second, labels, transform):
    a, b = labels[first.identifier], labels[second.identifier]
    return {'a': first.identifier, 'b': second.identifier, 'character': first.character,
            'severity': max(a['severity'], b['severity']),
            'dpi_a': first.source['dpi'], 'dpi_b': second.source['dpi'],
            'same_family': a['family'] == b['family'], 'transform': transform}


def build_pairs(directory, count, seed):
    started = time.monotonic()
    # This loader is inference-only. The following join is explicitly evaluator/trainer code.
    observations, abstentions = load_observations(directory)
    labels = evaluator_labels(directory)
    validate_evaluator_join(directory, labels)
    attach_registration_candidates(observations)
    features, targets, metadata = [], [], []
    for first, second in sample_pairs(observations, labels, count, seed):
        a, b = observations[first], observations[second]
        values, transform = compare(a, b)
        features.append(values)
        targets.append(labels[a.identifier]['font_sha256'] == labels[b.identifier]['font_sha256'])
        metadata.append(pair_record(a, b, labels, transform))
    return (np.asarray(features), np.asarray(targets, dtype=bool), metadata,
            {'seconds': time.monotonic()-started, 'usable_observations': len(observations),
             'abstentions': abstentions})
