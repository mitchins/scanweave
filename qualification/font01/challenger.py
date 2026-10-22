"""Reproducible CPU FONT-01 challenger; no weights enter ordinary conversion.

python -m qualification.font01.challenger CORPUS BASELINE NEW_OUTPUT
Requires the separately pinned CPU research dependencies. BASELINE is the strict
run_baseline output, not an arbitrary label/model directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy import optimize, special
import torch
from torch import nn

from .context import context_vectors
from .evaluation import decision_ledger, pair_metrics, threshold_at_fpr
from .metric_encoder import Encoder, training_loss
from .observations import load_observations
from .pair_data import evaluator_labels, validate_evaluator_join
from .registration import FEATURES, deterministic_score
from .linear_metric import load_metric
from .run_baseline import verify_corpus

SEED = 10303
ENCODER_FILE = 'encoder.pt'
EMBEDDINGS_SUFFIX = '-embeddings.npy'


def source_tensor(corpus, split):
    rows, abstentions = load_observations(corpus/split)
    if abstentions:
        raise ValueError('Frozen challenger protocol requires the full observation set')
    return rows, torch.tensor(np.stack([row.evidence['image'] for row in rows])[:, None])


def embed(model, images):
    model.eval()
    with torch.no_grad():
        return torch.cat([model(batch) for batch in images.split(128)]).numpy()


def pair_inputs(baseline, split, rows):
    data = np.load(baseline/(split+'.npz'))
    pairs = json.loads((baseline/(split+'-pairs.json')).read_text())
    lookup = {row.identifier: i for i, row in enumerate(rows)}
    left = np.asarray([lookup[row['a']] for row in pairs])
    right = np.asarray([lookup[row['b']] for row in pairs])
    healthy = np.asarray([row['severity'] <= 1 for row in pairs])
    return data['x'], data['y'], pairs, left, right, healthy


def train_encoder(images, targets, characters, weights, validation_images, validation, output, epochs=30):
    model = Encoder()
    head = nn.Linear(48, int(targets.max())+1)
    optimizer = torch.optim.Adam([*model.parameters(), *head.parameters()], lr=.001, weight_decay=0.)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    _, truth, _, left, right, healthy = validation
    best, history, started = -1., [], time.monotonic()
    for epoch in range(epochs):
        model.train()
        losses = []
        for indices in torch.randperm(len(images)).split(64):
            z = model(images[indices])
            loss = training_loss(z, head(z), targets[indices], characters[indices], weights[indices])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        scheduler.step()
        if (epoch+1) % 5 == 0 or epoch+1 == epochs:
            vectors = embed(model, validation_images)
            scores = (vectors[left]*vectors[right]).sum(1)
            threshold = threshold_at_fpr(truth[healthy], scores[healthy])
            metrics = pair_metrics(truth[healthy], scores[healthy], threshold)
            record = {'epoch': epoch+1, 'threshold': threshold, 'healthy': metrics,
                      'loss': float(np.mean(losses)), 'seconds': time.monotonic()-started}
            history.append(record)
            if metrics['recall'] > best:
                best = metrics['recall']
                torch.save(model.state_dict(), output/ENCODER_FILE)
                (output/'selected.json').write_text(json.dumps(record, indent=2)+'\n')
    model.load_state_dict(torch.load(output/ENCODER_FILE, weights_only=True))
    model.eval()
    (output/'history.json').write_text(json.dumps(history, indent=2)+'\n')
    return model


def extended_features(rows, embeddings, pair_data):
    x, _, _, left, right, _ = pair_data
    vectors, dispersion, counts, _ = context_vectors([row.source for row in rows], embeddings)
    distance = 1-(embeddings[left]*embeddings[right]).sum(1)
    hybrid = np.column_stack((x, distance))
    context = np.column_stack((hybrid, 1-(vectors[left]*vectors[right]).sum(1),
                               np.maximum(dispersion[left], dispersion[right]),
                               np.minimum(counts[left], counts[right])))
    return hybrid, context


def fit_extended(x, y):
    """Research-only logistic arm with explicitly recorded variable feature size."""
    mean, scale = x.mean(0), x.std(0)
    scale[scale < 1e-8] = 1
    design = np.column_stack(((x-mean)/scale, np.ones(len(x))))

    def objective(weights):
        logits = design @ weights
        loss = np.mean(np.logaddexp(0, logits)-y*logits)+.001*np.dot(weights[:-1], weights[:-1])
        gradient = design.T @ (special.expit(logits)-y)/len(y)
        gradient[:-1] += .002*weights[:-1]
        return loss, gradient

    result = optimize.minimize(objective, np.zeros(design.shape[1]), jac=True,
                               method='L-BFGS-B', options={'maxiter': 300})
    if not result.success:
        raise RuntimeError('Extended research fit failed: '+str(result.message))
    return {'mean': mean.tolist(), 'scale': scale.tolist(), 'coefficients': result.x[:-1].tolist(),
            'intercept': float(result.x[-1]), 'qualified_for_product': False}


def predict_extended(model, x):
    return special.expit(((x-model['mean'])/model['scale']) @ np.asarray(model['coefficients'])+model['intercept'])


def validate_baseline(baseline, fixture_hash, frozen_path=None):
    frozen_path = frozen_path or Path(__file__).with_name('baseline-reproduction.json')
    frozen = json.loads(frozen_path.read_text())
    if frozen['fixture_manifest_sha256'] != fixture_hash:
        raise ValueError('Baseline and current corpus fixture identities differ')
    for row in frozen['records']:
        data = np.load(baseline/(row['split']+'.npz'))
        actual = hashlib.sha256(data['x'].tobytes()+data['y'].tobytes()).hexdigest()
        pairs = hashlib.sha256((baseline/(row['split']+'-pairs.json')).read_bytes()).hexdigest()
        if actual != row['array_sha256'] or pairs != row['pair_metadata_sha256']:
            raise ValueError('Challenger requires exact frozen baseline arrays and pairs')
    model_hash = hashlib.sha256((baseline/'linear-model.json').read_bytes()).hexdigest()
    if model_hash != frozen['linear_model_sha256']:
        raise ValueError('Challenger linear baseline model differs from frozen fit')


def baseline_identity(baseline):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(baseline.iterdir()) if path.is_file()}


def run(corpus, baseline, output):
    frozen = Path(__file__).with_name('fixture-manifest.json')
    fixture_hash = verify_corpus(corpus, frozen)
    validate_baseline(baseline, fixture_hash)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    output.mkdir(parents=True, exist_ok=False)
    baseline_hashes = baseline_identity(baseline)
    data = {}
    for split in ['train', 'validation']:
        rows, images = source_tensor(corpus, split)
        data[split] = (rows, images, pair_inputs(baseline, split, rows))
    train_rows, train_images, train_pairs = data['train']
    labels = evaluator_labels(corpus/'train')
    validate_evaluator_join(corpus/'train', labels)
    faces = sorted({row['font_sha256'] for row in labels.values()})
    chars = sorted({row.character for row in train_rows})
    targets = torch.tensor([faces.index(labels[row.identifier]['font_sha256']) for row in train_rows])
    characters = torch.tensor([chars.index(row.character) for row in train_rows])
    weights = torch.tensor([(1., 1., .7, .3, .1)[labels[row.identifier]['severity']] for row in train_rows])
    model = train_encoder(train_images, targets, characters, weights, data['validation'][1],
                          data['validation'][2], output)
    protocol = {'seed': SEED, 'epochs': 30, 'parameters': sum(p.numel() for p in model.parameters()),
                'torch': torch.__version__, 'fixture_sha256': fixture_hash,
                'baseline_files': baseline_hashes, 'qualified_for_product': False}
    (output/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    extra = {}
    for split, (rows, images, pairs) in data.items():
        embeddings = embed(model, images)
        np.save(output/(split+EMBEDDINGS_SUFFIX), embeddings)
        extra[split] = extended_features(rows, embeddings, pairs)
    extended = {name: fit_extended(extra['train'][index], train_pairs[1])
                for index, name in enumerate(['hybrid', 'context'])}
    linear = load_metric(baseline/'linear-model.json')
    thresholds = {}
    results = []
    for split in ['validation', 'test']:
        if split == 'test':
            verify_corpus(corpus, frozen)
            freeze = {'thresholds': thresholds, 'models': extended, 'baseline_files': baseline_hashes,
                      'encoder_sha256': hashlib.sha256((output/ENCODER_FILE).read_bytes()).hexdigest()}
            (output/'pretest-freeze.json').write_text(json.dumps(freeze, indent=2)+'\n')
            rows, images = source_tensor(corpus, split)
            pairs = pair_inputs(baseline, split, rows)
            data[split] = (rows, images, pairs)
            embeddings = embed(model, images)
            np.save(output/(split+EMBEDDINGS_SUFFIX), embeddings)
            extra[split] = extended_features(rows, embeddings, pairs)
        rows, images, pairs = data[split]
        x, y, metadata, left, right, healthy = pairs
        embeddings = np.load(output/(split+EMBEDDINGS_SUFFIX))
        scores = {'deterministic': deterministic_score(x), 'linear': linear.scores(x),
                  'CNN': (embeddings[left]*embeddings[right]).sum(1),
                  **{name: predict_extended(extended[name], extra[split][index])
                     for index, name in enumerate(['hybrid', 'context'])}}
        if split == 'validation':
            thresholds = {name: threshold_at_fpr(y[healthy], score[healthy]) for name, score in scores.items()}
        for name, score in scores.items():
            ledger = decision_ledger(metadata, score, thresholds[name])
            (output/(split+'-'+name+'-decisions.json')).write_text(json.dumps(ledger, indent=2)+'\n')
            results.append({'split': split, 'arm': name, 'threshold': thresholds[name],
                            'healthy': pair_metrics(y[healthy], score[healthy], thresholds[name],
                                                    probabilities=name not in ['CNN', 'deterministic']),
                            'all': pair_metrics(y, score, thresholds[name], probabilities=name not in ['CNN', 'deterministic'])})
    if baseline_identity(baseline) != baseline_hashes:
        raise ValueError('Baseline artifacts changed during challenger evaluation')
    verify_corpus(corpus, frozen)
    (output/'results.json').write_text(json.dumps(results, indent=2)+'\n')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.corpus, args.baseline, args.output)


if __name__ == '__main__':
    main()
