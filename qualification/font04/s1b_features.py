"""S1b inference features from exported source masks, without oracle data."""
import numpy as np
from scipy import ndimage as ndi

FEATURES = ('slant', 'weight', 'profile', 'dot', 'flag', 'foot', 'hole')
CONFUSABLE = set('il1I|')
ROUND = set('0Oo')

def features(row):
    s = row['source']
    if not s or not s.get('mask'):
        return None
    a = np.asarray(s['mask'], dtype=bool).reshape(s['height'], s['width'])
    y, x = np.nonzero(a)
    if len(x) < 3:
        return None
    a = a[y.min():y.max()+1, x.min():x.max()+1]
    h, w = a.shape
    y, x = np.nonzero(a)
    dy = y - y.mean()
    slant = float(np.dot(x-x.mean(), dy) / max(1., np.dot(dy, dy)))
    dist = ndi.distance_transform_edt(np.pad(a, 1))[1:-1, 1:-1]
    # Local distance maxima approximate medial-axis stroke radii.
    ridge = a & (dist >= ndi.maximum_filter(dist, size=3))
    widths = 2 * dist[ridge] / h
    if not widths.size:
        return None
    weight = float(np.median(widths))
    profile = float(np.quantile(widths, .9) / max(np.quantile(widths, .1), 1e-6))
    labels, n = ndi.label(a)
    components = ndi.find_objects(labels)
    # Detached, small upper component relative to the largest component.
    sizes = np.bincount(labels.ravel(), minlength=n+1); sizes[0] = 0
    main = int(np.argmax(sizes))
    dot = float(any(i != main and sizes[i] >= 2 and sl and sl[0].stop <= h*.45
                    for i, sl in enumerate(components, 1)))
    # Relative protrusion to the left of the middle stem and breadth at the foot.
    middle = x[(y >= h*.35) & (y < h*.7)]
    stem_left = float(np.median(middle)) if middle.size else float(np.median(x))
    upper = x[y < h*.3]
    flag = float(max(0., stem_left - np.quantile(upper, .1)) / max(w, 1)) if upper.size else 0.
    bottom = x[y >= h*.8]
    foot = float((np.quantile(bottom, .9)-np.quantile(bottom, .1)) / max(w, 1)) if bottom.size else 0.
    hole = float(ndi.binary_fill_holes(a).sum() - a.sum()) / max(1, h*w)
    return dict(slant=slant, weight=weight, profile=profile, dot=dot, flag=flag, foot=foot, hole=hole)

def differences(a, b, label):
    if a is None or b is None:
        return None
    names = ['slant', 'weight', 'profile']
    if label in CONFUSABLE:
        names += ['dot', 'flag', 'foot']
    if label in ROUND:
        names += ['hole']
    return {k: abs(a[k]-b[k]) for k in names}
