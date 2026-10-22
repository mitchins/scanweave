"""Read-only canonical-group and donor diagnostics, separate from font cohorts.

The caller supplies a frozen split and NEW result directory. Oracle labels and
pristine images are consulted only by explicitly named evaluator functions.
"""
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image

from .clustering import complete_groups, clustering_metrics
from .observations import load_observations, preprocess_samples, source_path
from .pair_data import evaluator_labels, validate_evaluator_join
from .registration import attach_registration_candidates, best_alignment, compare, deterministic_score, variants


def canonical_clusters(directory, output, maximum):
    rows, abstentions = load_observations(directory)
    labels = evaluator_labels(directory)
    validate_evaluator_join(directory, labels)
    attach_registration_candidates(rows)
    output.mkdir(parents=True, exist_ok=False)
    groups = []
    started = time.monotonic()
    for char in sorted({row.character for row in rows}):
        selected = [row for row in rows if row.character == char]
        matrix = np.zeros((len(selected), len(selected)))
        for first, row in enumerate(selected):
            for second in range(first):
                distance = -float(deterministic_score(compare(row, selected[second])[0]))
                matrix[first, second] = matrix[second, first] = distance
        np.savez_compressed(output/(str(ord(char))+'.npz'), distances=matrix)
        groups.extend(complete_groups([row.identifier for row in selected], matrix, maximum))
    lookup = {identifier: i for i, group in enumerate(groups) for identifier in group}
    truth = [labels[row.identifier]['font_sha256']+':'+row.character for row in rows]
    prediction = [lookup[row.identifier] for row in rows]
    result = {'canonical_template_clusters': clustering_metrics(truth, prediction),
              'abstentions': abstentions, 'groups': groups, 'seconds': time.monotonic()-started,
              'maximum_distance': maximum,
              'font_cohort_assignment': 'NOT ESTABLISHED by same-character groups'}
    (output/'clusters.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def diagnostic_iou(image, reference):
    """Shape-only after bounded registration; NOT exact-position PDF fidelity."""
    _, moving, _ = best_alignment(reference, variants(image))
    first, second = moving > .28, reference > .28
    return float((first & second).sum()/max(1, (first | second).sum()))


def recover_group(rows, labels, identifiers, matrix, positions, directory):
    """Leave target out. Select/fuse sources without consulting pristine shapes."""
    lookup = {row.identifier: row for row in rows}
    records = []
    for identifier in identifiers:
        donors = [value for value in identifiers if value != identifier]
        indices = [positions[value] for value in donors]
        medoid = donors[int(np.argmin(matrix[np.ix_(indices, indices)].sum(0)))]
        strongest = max(donors, key=lambda value: (lookup[value].evidence['quality'],
                                                  -lookup[value].evidence['components'], value))
        center = lookup[medoid].evidence['image']
        aligned = [best_alignment(center, lookup[value].evidence['variants'])[1] for value in donors]
        consensus = np.median(aligned, axis=0)
        # Oracle enters only now, after the source-only candidates are fixed.
        path = source_path(directory, 'oracle/'+identifier+'-pristine.png')
        with Image.open(path) as image:
            reference = preprocess_samples(np.asarray(image.convert('L'), np.float32))
        if reference is None:
            continue
        images = {'source': lookup[identifier].evidence['image'],
                  'quality_donor': lookup[strongest].evidence['image'],
                  'medoid': center, 'consensus': consensus}
        records.append({'id': identifier, 'severity': labels[identifier]['severity'],
                        'character': lookup[identifier].character, 'donor_count': len(donors),
                        'cross_face_contaminated': len({labels[value]['font_sha256'] for value in identifiers}) > 1,
                        **{name+'_iou': diagnostic_iou(candidate, reference['image'])
                           for name, candidate in images.items()}})
    return records


def recovery(directory, cluster_output):
    directory = Path(directory).resolve(strict=True)
    rows, _ = load_observations(directory)
    attach_registration_candidates(rows)
    labels = evaluator_labels(directory)
    validate_evaluator_join(directory, labels)
    inferred = json.loads((cluster_output/'clusters.json').read_text())['groups']
    oracle = {}
    for row in rows:
        oracle.setdefault((labels[row.identifier]['font_sha256'], row.character), []).append(row.identifier)
    records = []
    for arm, groups in [('inferred', inferred), ('oracle_cohort_control', list(oracle.values()))]:
        for group in groups:
            if len(group) < 3:
                continue
            char = next(row.character for row in rows if row.identifier == group[0])
            ordered = [row.identifier for row in rows if row.character == char]
            positions = {identifier: i for i, identifier in enumerate(ordered)}
            matrix = np.load(cluster_output/(str(ord(char))+'.npz'))['distances']
            records.extend(dict(record, arm=arm) for record in recover_group(
                rows, labels, group, matrix, positions, directory))
    (cluster_output/'recovery-records.json').write_text(json.dumps(records, indent=2)+'\n')
    return records
