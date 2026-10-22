"""Complete-link research groups; character identity and cohort identity differ."""
import numpy as np
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform


def complete_groups(identifiers, distances, maximum, characters=None):
    """Every within-group distance satisfies the gate; no single-link chaining.

    Character cannot-links apply only to canonical-template groups, not face
    cohorts. IDs determine tie order, so input row order does not decide groups.
    """
    count = len(identifiers)
    matrix = np.asarray(distances, dtype=float)
    if matrix.shape != (count, count) or len(set(identifiers)) != count:
        raise ValueError('Distances must cover unique observation IDs')
    if not np.isfinite(matrix).all() or np.any(matrix < 0) or not np.array_equal(matrix, matrix.T):
        raise ValueError('Distances must be finite, nonnegative and symmetric')
    if not np.isfinite(maximum) or maximum < 0:
        raise ValueError('Invalid complete-link threshold')
    if characters is not None and len(characters) != count:
        raise ValueError('Character identities must cover every observation')
    if not count:
        return []
    order = np.argsort(identifiers)
    ordered = matrix[np.ix_(order, order)].copy()
    np.fill_diagonal(ordered, 0)
    if characters is not None:
        chars = np.asarray(characters)[order]
        ordered[chars[:, None] != chars[None, :]] = max(float(ordered.max()), maximum)+1
    labels = np.ones(count, dtype=int)
    if count > 1:
        tree = hierarchy.linkage(squareform(ordered), method='complete')
        labels = hierarchy.fcluster(tree, maximum, criterion='distance')
    groups = {}
    for position, label in enumerate(labels):
        groups.setdefault(int(label), []).append(identifiers[int(order[position])])
    return sorted(sorted(group) for group in groups.values())


def clustering_metrics(truth, predicted):
    """Permutation-invariant ARI, purity and completeness; no font-name guessing."""
    if len(truth) != len(predicted) or not len(truth):
        raise ValueError('Cluster labels must cover the same nonempty observations')
    _, actual = np.unique(truth, return_inverse=True)
    _, inferred = np.unique(predicted, return_inverse=True)
    table = np.zeros((actual.max()+1, inferred.max()+1), dtype=np.int64)
    np.add.at(table, (actual, inferred), 1)
    pairs = lambda values: float((values*(values-1)/2).sum())
    observed = pairs(table)
    row_pairs, column_pairs = pairs(table.sum(1)), pairs(table.sum(0))
    total_pairs = len(truth)*(len(truth)-1)/2
    expected = row_pairs*column_pairs/total_pairs if total_pairs else 0
    denominator = .5*(row_pairs+column_pairs)-expected
    ari = (observed-expected)/denominator if denominator else 1.
    return {'observations': len(truth), 'actual_groups': int(table.shape[0]),
            'inferred_groups': int(table.shape[1]), 'adjusted_rand_index': float(ari),
            'purity': float(table.max(0).sum()/len(truth)),
            'completeness': float(table.max(1).sum()/len(truth)),
            'contaminated_groups': int(((table > 0).sum(0) > 1).sum()),
            'singleton_groups': int((table.sum(0) == 1).sum())}
