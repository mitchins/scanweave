"""Small versioned research metric; no model is enabled in PDF conversion."""
from dataclasses import dataclass
import json

import numpy as np
from scipy import optimize, special

from .registration import FEATURE_SCHEMA, FEATURES

MODEL_SCHEMA = 'font01-linear-v1'


@dataclass
class LinearMetric:
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    intercept: float

    def __post_init__(self):
        self.mean = np.asarray(self.mean, dtype=np.float64)
        self.scale = np.asarray(self.scale, dtype=np.float64)
        self.coefficients = np.asarray(self.coefficients, dtype=np.float64)
        arrays = (self.mean, self.scale, self.coefficients)
        if any(array.shape != (len(FEATURES),) or not np.isfinite(array).all() for array in arrays):
            raise ValueError('Malformed linear model parameters')
        if not np.isfinite(self.intercept) or np.any(self.scale <= 0):
            raise ValueError('Invalid linear model scale or intercept')

    def scores(self, features):
        values = np.asarray(features, dtype=np.float64)
        if values.ndim not in (1, 2) or values.shape[-1] != len(FEATURES):
            raise ValueError('Incompatible registered-feature tensor')
        if not np.isfinite(values).all():
            raise ValueError('Non-finite registered features')
        return special.expit(((values-self.mean)/self.scale) @ self.coefficients + self.intercept)

    def document(self):
        return {'schema': MODEL_SCHEMA, 'feature_schema': FEATURE_SCHEMA,
                'feature_names': list(FEATURES), 'mean': self.mean.tolist(),
                'scale': self.scale.tolist(), 'coefficients': self.coefficients.tolist(),
                'intercept': self.intercept, 'qualified_for_product': False,
                'score_kind': 'logistic_probability_under_training_pair_prior'}

    def save(self, path):
        path.write_text(json.dumps(self.document(), indent=2) + '\n')


def load_metric(path):
    data = json.loads(path.read_text())
    if data.get('schema') != MODEL_SCHEMA or data.get('feature_schema') != FEATURE_SCHEMA:
        raise ValueError('Incompatible linear model schema')
    if data.get('feature_names') != list(FEATURES):
        raise ValueError('Incompatible feature order')
    arrays = [np.asarray(data[key], dtype=np.float64) for key in ('mean', 'scale', 'coefficients')]
    if any(array.shape != (len(FEATURES),) or not np.isfinite(array).all() for array in arrays):
        raise ValueError('Malformed linear model parameters')
    intercept = float(data['intercept'])
    if not np.isfinite(intercept) or np.any(arrays[1] <= 0):
        raise ValueError('Invalid linear model scale or intercept')
    return LinearMetric(*arrays, intercept)


def fit_metric(features, labels):
    values, targets = np.asarray(features, dtype=float), np.asarray(labels, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(FEATURES) or targets.shape != (len(values),):
        raise ValueError('Incompatible training arrays')
    if not np.isfinite(values).all() or not np.isin(targets, [0., 1.]).all():
        raise ValueError('Training requires finite features and binary labels')
    if not len(targets) or len(np.unique(targets)) != 2:
        raise ValueError('Training requires both pair classes')
    mean, scale = values.mean(0), values.std(0)
    scale[scale < 1e-8] = 1
    design = np.column_stack(((values-mean)/scale, np.ones(len(values))))

    def objective(weights):
        logits = design @ weights
        loss = np.mean(np.logaddexp(0, logits)-targets*logits) + .001*np.dot(weights[:-1], weights[:-1])
        gradient = design.T @ (special.expit(logits)-targets) / len(targets)
        gradient[:-1] += .002*weights[:-1]
        return loss, gradient

    result = optimize.minimize(objective, np.zeros(design.shape[1]), jac=True,
                               method='L-BFGS-B', options={'maxiter': 300})
    if not result.success:
        raise RuntimeError('Linear metric optimization failed: ' + str(result.message))
    return LinearMetric(mean, scale, result.x[:-1], float(result.x[-1]))
