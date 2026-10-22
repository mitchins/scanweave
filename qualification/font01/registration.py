"""Bounded, bidirectional same-character registration and comparison evidence."""
import numpy as np
from scipy import ndimage, signal

from .observations import CANVAS

FEATURE_SCHEMA = 'font01-registered-features-v1'
FEATURES = ('coverage_l1', 'soft_iou_loss', 'chamfer', 'area_log_ratio',
            'aspect_log_ratio', 'stroke_log_ratio', 'holes_difference',
            'components_difference', 'registration_cost', 'ink_fraction_difference',
            'quality_min')


def variants(image):
    center = (np.asarray(image.shape) - 1) / 2
    result = []
    for angle in (-1.5, 0., 1.5):
        radians = np.deg2rad(angle)
        rotation = np.array([[np.cos(radians), -np.sin(radians)],
                             [np.sin(radians), np.cos(radians)]])
        for scale in (.97, 1., 1.03):
            inverse = rotation / scale
            moving = ndimage.affine_transform(image, inverse, offset=center-inverse@center,
                                              order=1, mode='constant', cval=0, prefilter=False)
            result.append((moving, angle, scale))
    return result


def best_alignment(image, moving_variants):
    best = None
    for moving, angle, scale in moving_variants:
        correlation = signal.fftconvolve(image, moving[::-1, ::-1], mode='full')
        center = CANVAS - 1
        window = correlation[center-2:center+3, center-2:center+3]
        dy, dx = np.unravel_index(np.argmax(window), window.shape)
        dy, dx = int(dy)-2, int(dx)-2
        aligned = ndimage.shift(moving, (dy, dx), order=0, prefilter=False, cval=0)
        cost = float(np.mean((image-aligned)**2))
        if best is None or cost < best[0]:
            best = (cost, aligned, {'angle': angle, 'scale': scale, 'dy': dy, 'dx': dx})
    if best is None:
        raise ValueError('Registration requires at least one bounded candidate')
    return best


def log_ratio(first, second):
    return abs(float(np.log(max(first, 1e-6) / max(second, 1e-6))))


def directed_features(first, second):
    image = first['image']
    cost, moving, transform = best_alignment(image, second['variants'])
    ma, mb = first['mask'], moving > .28
    union = float(np.maximum(image, moving).sum())
    intersection = float(np.minimum(image, moving).sum())
    chamfer = 1.
    if ma.any() and mb.any():
        chamfer = .5 * (float(first['distance'][mb].mean()) +
                        float(ndimage.distance_transform_edt(~mb)[ma].mean())) / CANVAS
    values = [float(np.mean(abs(image-moving))), 1-intersection/max(union, 1e-6), chamfer,
              log_ratio(first['area'], second['area']), log_ratio(first['aspect'], second['aspect']),
              log_ratio(first['stroke'], second['stroke']), abs(first['holes']-second['holes']),
              abs(first['components']-second['components']), cost,
              abs(first['ink_fraction']-second['ink_fraction']), min(first['quality'], second['quality'])]
    return np.asarray(values, np.float64), transform


def attach_registration_candidates(observations):
    for observation in observations:
        observation.evidence['variants'] = variants(observation.evidence['image'])


def compare(first, second):
    """A canonical comparison never changes or ignores character identity."""
    if first.character != second.character:
        raise ValueError('Canonical comparisons require identical character identities')
    forward, ft = directed_features(first.evidence, second.evidence)
    reverse, rt = directed_features(second.evidence, first.evidence)
    return .5 * (forward + reverse), {'b_to_a': ft, 'a_to_b': rt}


def deterministic_score(features):
    """Frozen pre-evaluation baseline; not a probability or qualified merge rule."""
    return -(features[..., 1] + 2*features[..., 2] + .1*features[..., 3] + .1*features[..., 4])
