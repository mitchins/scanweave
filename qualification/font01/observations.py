"""Source-only glyph evidence. No font labels, pristine images or OCR rewriting."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

CANVAS = 48
NORMALIZATION_SCHEMA = 'font01-coverage-v1'
ORACLE_FIELDS = {'face', 'family', 'font_sha256', 'master_id', 'severity',
                 'transform', 'point_size', 'baseline', 'nominal_height_px',
                 'split', 'document', 'line', 'word', 'metrics'}


@dataclass
class Observation:
    identifier: str
    character: str
    source: dict
    evidence: dict


def source_path(root, relative):
    """Resolve discovered inputs inside the authorized corpus destination."""
    destination = (root / relative).resolve(strict=True)
    if not destination.is_relative_to(root):
        raise ValueError('Corpus input resolves outside its authorized root: ' + str(relative))
    return destination


def coverage_from_samples(samples):
    if samples.ndim != 2 or not samples.size or max(samples.shape) > 4096:
        raise ValueError('Expected a nonempty grayscale glyph, at most4096 samples per axis')
    if not np.isfinite(samples).all() or samples.min() < 0 or samples.max() > 255:
        raise ValueError('Glyph samples must be finite grayscale values in0..255')
    paper = float(np.percentile(samples, 90))
    contrasts = paper - samples
    positive = contrasts[contrasts > 8]
    if len(positive) < 3:
        return None
    ink = float(np.percentile(positive, 90))
    return np.clip(contrasts / max(ink, 8), 0, 1), paper, ink


def normalized_coverage(coverage):
    mask = coverage > .28
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    x0, x1 = int(xs.min()), int(xs.max() + 1)
    y0, y1 = int(ys.min()), int(ys.max() + 1)
    box = coverage[y0:y1, x0:x1]
    scale = min(32 / box.shape[0], 40 / box.shape[1])
    shape = tuple(max(1, round(length * scale)) for length in box.shape)
    fitted = ndimage.zoom(box, (shape[0] / box.shape[0], shape[1] / box.shape[1]),
                          order=1, prefilter=False)
    result = np.zeros((CANVAS, CANVAS), np.float32)
    y, x = (CANVAS - fitted.shape[0]) // 2, (CANVAS - fitted.shape[1]) // 2
    result[y:y + fitted.shape[0], x:x + fitted.shape[1]] = fitted
    return result, mask, [x0, y0, x1, y1]


def topology(binary):
    _, components = ndimage.label(binary)
    background, count = ndimage.label(~binary)
    border = set(np.concatenate((background[0], background[-1], background[:, 0], background[:, -1])))
    holes = sum(i not in border for i in range(1, count + 1))
    return int(components), int(holes)


def preprocess_samples(samples):
    """Normalize observed coverage uniformly; record, do not hide, crop geometry.

    This is a comparison frame, not document placement or a repaired glyph frame.
    A missing stroke can change its observed extent; that remains a limitation.
    """
    estimated = coverage_from_samples(np.asarray(samples, dtype=np.float32))
    if estimated is None:
        return None
    coverage, paper, ink = estimated
    normalized = normalized_coverage(coverage)
    if normalized is None:
        return None
    image, source_mask, box = normalized
    binary = image > .28
    distances = ndimage.distance_transform_edt(binary)
    components, holes = topology(binary)
    return {'image': image, 'mask': binary,
            'distance': ndimage.distance_transform_edt(~binary),
            'area': float(image.sum()), 'aspect': (box[2] - box[0]) / (box[3] - box[1]),
            'stroke': float(np.median(distances[binary])), 'holes': holes,
            'components': components, 'quality': min(1., ink / 128),
            'ink_fraction': float(source_mask.mean()), 'source_box': box,
            'paper_level': paper, 'ink_contrast': ink}


def load_observations(directory):
    """Return usable observations and explicit abstentions; never open oracle/."""
    root = Path(directory).resolve(strict=True)
    records = source_path(root, 'observations.jsonl').read_text().splitlines()
    result, abstentions, identifiers = [], [], set()
    for line in records:
        record = json.loads(line)
        if ORACLE_FIELDS.intersection(record):
            raise ValueError('Oracle fields are not permitted in inference records')
        identifier, character = record['id'], record['character']
        if identifier in identifiers or not character:
            raise ValueError('Duplicate observation ID or empty character identity')
        identifiers.add(identifier)
        image_path = source_path(root, record['image'])
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != record['image_sha256']:
            raise ValueError('Observation image hash mismatch: ' + identifier)
        with Image.open(image_path) as image:
            if max(image.size) > 4096:
                raise ValueError('Observation image is too large: ' + identifier)
            evidence = preprocess_samples(np.asarray(image.convert('L'), dtype=np.float32))
        if evidence is None:
            abstentions.append({'id': identifier, 'reason': 'insufficient_source_ink'})
        else:
            result.append(Observation(identifier, character, record, evidence))
    return result, abstentions
