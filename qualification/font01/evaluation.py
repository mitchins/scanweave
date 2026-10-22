"""Pair measurements with ties, abstention and non-probability scores explicit."""
import numpy as np


def validate_pairs(labels, scores):
    y, values = np.asarray(labels), np.asarray(scores, dtype=float)
    if y.dtype != bool or y.ndim != 1 or values.shape != y.shape or not len(y):
        raise ValueError('Expected equally sized, nonempty Boolean labels and scores')
    if not np.isfinite(values).all():
        raise ValueError('Scores must be finite')
    return y, values


def ranking_metrics(labels, scores):
    order = np.argsort(-scores, kind='stable')
    targets = labels[order]
    tp, fp = np.cumsum(targets), np.cumsum(~targets)
    ends = np.r_[np.flatnonzero(np.diff(scores[order])), len(scores)-1]
    recall = tp[ends] / max(1, labels.sum())
    fpr = fp[ends] / max(1, (~labels).sum())
    precision = tp[ends] / (tp[ends]+fp[ends])
    # AUC is undefined if a slice contains only one class; do not fabricate it.
    auc = None
    if labels.any() and (~labels).any():
        auc = float(np.trapezoid(np.r_[0, recall, 1], np.r_[0, fpr, 1]))
    ap = float(np.sum(np.diff(np.r_[0, recall])*precision)) if labels.any() else None
    return auc, ap


def calibration_error(labels, probabilities):
    if np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError('Calibration requires probabilities in0..1')
    result = 0.
    for index in range(10):
        lower, upper = index/10, (index+1)/10
        selected = (probabilities >= lower) & (probabilities < upper)
        if index == 9:
            selected |= probabilities == 1
        if selected.any():
            result += selected.mean()*abs(float(labels[selected].mean()-probabilities[selected].mean()))
    return float(result)


def pair_metrics(labels, scores, threshold, *, probabilities=False):
    labels, scores = validate_pairs(labels, scores)
    auc, ap = ranking_metrics(labels, scores)
    accepted = scores >= threshold
    true = int((accepted & labels).sum())
    false = int((accepted & ~labels).sum())
    return {'pairs': len(labels), 'positives': int(labels.sum()), 'roc_auc': auc, 'pr_auc': ap,
            'precision': true/int(accepted.sum()) if accepted.any() else None,
            'recall': true/int(labels.sum()) if labels.any() else None,
            'false_merge_rate': false/int((~labels).sum()) if (~labels).any() else None,
            'false_merges': false,
            'ece': calibration_error(labels, scores) if probabilities else None}


def threshold_at_fpr(labels, scores, limit=.005):
    labels, scores = validate_pairs(labels, scores)
    if not 0 <= limit < 1 or not (~labels).any():
        raise ValueError('Threshold selection needs negatives and a limit in[0,1)')
    negative = np.sort(scores[~labels])
    allowed = int(np.floor(limit*len(negative)))
    # Accept neither a large tied group nor an excess false merge at the boundary.
    return float(np.nextafter(negative[-allowed-1], np.inf))


def false_merge_at_recall(labels, scores, recall):
    labels, scores = validate_pairs(labels, scores)
    if not 0 < recall <= 1 or not labels.any():
        raise ValueError('Recall selection requires positives and a fraction in(0,1]')
    positive = np.sort(scores[labels])[::-1]
    index = int(np.ceil(recall*len(positive)))-1
    return pair_metrics(labels, scores, float(positive[index]))
