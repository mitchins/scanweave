"""Source-only registered glyph cohorts and robust canonical coverage fitting.

Research implementation; no converter imports this module. Coordinates are fixed
line-metric frames, never independently normalized ink bounding rectangles.
"""

from dataclasses import dataclass
import numpy as np
from scipy import ndimage, optimize


@dataclass(frozen=True)
class Limits:
    translation: float = 2.0
    scale: float = 0.02
    minimum_iou: float = 0.76
    area_ratio: float = 1.25
    extent_ratio: float = 1.18
    elongation_ratio: float = 1.5
    stroke_ratio: float = 1.3
    huber_delta: float = 0.12


def warp(image, parameters):
    """Move an observation in the common x-height32/baseline48 frame."""
    dx, dy, scale = parameters
    center = np.array([48.0, 32.0])
    inverse = np.eye(2) / scale
    return ndimage.affine_transform(
        image,
        inverse,
        offset=center - inverse @ (center + [dy, dx]),
        order=1,
        mode="constant",
        prefilter=False,
    )


def register(reference, image, limits=Limits()):
    """Bound nuisance geometry without anisotropic or nonlinear deformation."""
    fit = optimize.least_squares(
        lambda p: (warp(image, p) - reference).ravel(),
        [0.0, 0.0, 1.0],
        bounds=(
            [-limits.translation, -limits.translation, 1 - limits.scale],
            [limits.translation, limits.translation, 1 + limits.scale],
        ),
        loss="huber",
        f_scale=limits.huber_delta,
        max_nfev=35,
        diff_step=0.001,
        ftol=1e-5,
        xtol=1e-5,
        gtol=1e-5,
    )
    return fit.x, warp(image, fit.x)


def topology(mask):
    """Count 8-connected ink and enclosed 8-connected background components."""
    _, components = ndimage.label(mask, np.ones((3, 3)))
    labels, count = ndimage.label(~mask, np.ones((3, 3)))
    border = set(labels[0]) | set(labels[-1]) | set(labels[:, 0]) | set(labels[:, -1])
    return int(components), len(set(range(1, count + 1)) - border)


def geometry(image):
    """Describe proportions and stroke geometry without rescaling the glyph."""
    a = np.asarray(image, float)
    mask = a > 0.5
    ys, xs = np.nonzero(mask)
    if not len(xs) or a.sum() <= 0:
        return None
    yy, xx = np.indices(a.shape)
    mass = a.sum()
    centroid = np.array([(xx * a).sum() / mass, (yy * a).sum() / mass])
    coordinates = np.array([xx.ravel() - centroid[0], yy.ravel() - centroid[1]])
    covariance = (coordinates * a.ravel()) @ coordinates.T / mass
    values, axes = np.linalg.eigh(covariance)
    stroke = float(np.median(ndimage.distance_transform_edt(mask)[mask]))
    return dict(
        area=float(mass),
        width=float(xs.max() - xs.min() + 1),
        height=float(ys.max() - ys.min() + 1),
        centroid=centroid.tolist(),
        elongation=float(np.sqrt(max(values[-1], 0.01) / max(values[0], 0.01))),
        axis=axes[:, -1].tolist(),
        stroke=stroke,
        topology=topology(mask),
    )


def geometry_rejections(reference, candidate, limits=Limits()):
    """Structural vetoes remain independent of pixel-error acceptance."""
    a, b = geometry(reference), geometry(candidate)
    if a is None or b is None:
        return ["empty_ink"]
    reasons = []
    for key, maximum in [
        ("area", limits.area_ratio),
        ("width", limits.extent_ratio),
        ("height", limits.extent_ratio),
        ("elongation", limits.elongation_ratio),
        ("stroke", limits.stroke_ratio),
    ]:
        ratio = b[key] / max(a[key], 1e-8)
        if not 1 / maximum <= ratio <= maximum:
            reasons.append(key)
    if a["topology"] != b["topology"]:
        reasons.append("topology")
    if np.linalg.norm(np.array(a["centroid"]) - b["centroid"]) > 2:
        reasons.append("centroid")
    if min(a["elongation"], b["elongation"]) > 1.5:
        cosine = abs(np.dot(a["axis"], b["axis"]))
        if cosine < np.cos(np.deg2rad(15)):
            reasons.append("orientation")
    return reasons


def soft_iou(a, b):
    """Coverage overlap is a discovery feature, never a structural override."""
    return float(np.minimum(a, b).sum() / max(1e-8, np.maximum(a, b).sum()))


def compatible(reference, candidate, limits=Limits()):
    """Require direct registered evidence and structural agreement."""
    parameters, aligned = register(reference, candidate, limits)
    reasons = geometry_rejections(reference, aligned, limits)
    score = soft_iou(reference, aligned)
    if score < limits.minimum_iou:
        reasons.append("coverage")
    return not reasons, parameters, score, reasons


def symmetric_compatible(first, second, limits=Limits()):
    """Both bounded registrations must support a pair, not just the first fit."""
    forward = compatible(first, second, limits)
    reverse = compatible(second, first, limits)
    reasons = ["forward:" + reason for reason in forward[3]] + [
        "reverse:" + reason for reason in reverse[3]
    ]
    return forward[0] and reverse[0], forward[1], min(forward[2], reverse[2]), reasons


def complete_groups(images, characters, limits=Limits()):
    """Deterministic complete-link grouping, with explicit pairwise vetoes."""
    groups, pairs = [], {}
    for i, image in enumerate(images):
        choices = []
        for index, members in enumerate(groups):
            if characters[i] != characters[members[0]]:
                continue
            scores = []
            for j in members:
                key = (min(i, j), max(i, j))
                if key not in pairs:
                    pairs[key] = symmetric_compatible(images[j], image, limits)
                passed, _, score, _ = pairs[key]
                if not passed:
                    break
                scores.append(score)
            else:
                choices.append((min(scores), index))
        if choices:
            _, index = max(choices, key=lambda x: (x[0], -x[1]))
            groups[index].append(i)
        else:
            groups.append([i])
    return groups, pairs


def robust_template(aligned, delta=0.12, iterations=12):
    """Huber M-estimate; retain uncertainty instead of treating an average as truth."""
    observations = np.asarray(aligned, float)
    template = observations.mean(axis=0)
    for _ in range(iterations):
        residuals = observations - template
        weights = np.minimum(1.0, delta / np.maximum(np.abs(residuals), 1e-8))
        template = (weights * observations).sum(axis=0) / weights.sum(axis=0)
    uncertainty = np.median(np.abs(observations - template), axis=0)
    return template, uncertainty


def fit_group(images, members, limits=Limits()):
    """Fit one canonical source field and leave-one-out normal-variation envelope."""
    costs = [
        (
            sum(
                1 - soft_iou(images[i], register(images[i], images[j], limits)[1])
                for j in members
                if j != i
            ),
            i,
        )
        for i in members
    ]
    medoid = min(costs)[1]
    fitted = [register(images[medoid], images[i], limits) for i in members]
    aligned = np.asarray([image for _, image in fitted])
    template, uncertainty = robust_template(aligned, limits.huber_delta)
    heldout = []
    if len(members) >= 3:
        for k, image in enumerate(aligned):
            other, _ = robust_template(
                np.delete(aligned, k, axis=0), limits.huber_delta
            )
            heldout.append(
                float(np.square(other - image).sum() / max(1.0, image.sum()))
            )
    center = float(np.median(heldout)) if heldout else None
    mad = float(np.median(np.abs(np.array(heldout) - center))) if heldout else None
    return dict(
        members=members,
        medoid=medoid,
        parameters=[p.tolist() for p, _ in fitted],
        template=template,
        uncertainty=uncertainty,
        leave_one_out=heldout,
        noise_upper=None if center is None else center + 3 * 1.4826 * mad,
    )


def distance_template(aligned, upsample=4):
    """Fit robust signed contour distances rather than average ink intensities.

    The second bounded arm addresses coverage-fit edge broadening. Interpolation
    only locates observed half-coverage edges; the Huber distance fit combines
    those geometries before a small curvature regularizer is applied.
    """
    fields = []
    for image in aligned:
        high = ndimage.zoom(image, upsample, order=1, prefilter=False)
        mask = high > 0.5
        signed = (
            ndimage.distance_transform_edt(mask) - ndimage.distance_transform_edt(~mask)
        ) / upsample
        yy, xx = np.indices(image.shape)
        fields.append(
            ndimage.map_coordinates(
                signed, [yy * upsample, xx * upsample], order=1, mode="nearest"
            )
        )
    fields = np.asarray(fields)
    fitted = fields.mean(axis=0)
    for _ in range(12):
        weights = np.minimum(1.0, 0.5 / np.maximum(np.abs(fields - fitted), 1e-8))
        fitted = (weights * fields).sum(axis=0) / weights.sum(axis=0)
    fitted = ndimage.gaussian_filter(fitted, 0.35)
    return np.clip(0.5 + fitted / 1.2, 0, 1)


def affine_forward(parameters):
    """Bounded affine nuisance map; no shear or nonlinear contour deformation."""
    dx, dy, angle, sx, sy = parameters
    theta = np.deg2rad(angle)
    rotation = np.array(
        [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    )
    matrix = rotation @ np.diag([sx, sy])
    center = np.array([32.0, 48.0])
    result = np.eye(3)
    result[:2, :2] = matrix
    result[:2, 2] = center + [dx, dy] - matrix @ center
    return result


def affine_warp(image, parameters):
    """Sample the same line frame under the bounded nuisance transform."""
    inverse = np.linalg.inv(affine_forward(parameters))
    yy, xx = np.indices(image.shape)
    points = inverse @ np.array([xx.ravel(), yy.ravel(), np.ones(xx.size)])
    return ndimage.map_coordinates(
        image, [points[1], points[0]], order=1, mode="constant", prefilter=False
    ).reshape(image.shape)


def register_affine(reference, image):
    """Refinement justified by the benchmark's documented independent scan transforms."""
    fit = optimize.least_squares(
        lambda p: (affine_warp(image, p) - reference).ravel(),
        [0.0, 0.0, 0.0, 1.0, 1.0],
        bounds=([-2.0, -2.0, -1.0, 0.96, 0.96], [2.0, 2.0, 1.0, 1.04, 1.04]),
        loss="huber",
        f_scale=0.12,
        max_nfev=35,
        diff_step=0.001,
        ftol=1e-5,
        xtol=1e-5,
        gtol=1e-5,
    )
    return fit.x, affine_warp(image, fit.x)


def structural_distances(reference, candidate):
    """Weight, counter and projected-ink differences beyond component counts."""
    a, b = np.asarray(reference, float), np.asarray(candidate, float)
    ga, gb = geometry(a), geometry(b)
    if ga is None or gb is None:
        return None

    def descriptors(image):
        gy, gx = np.gradient(image)
        effective_stroke = 2 * image.sum() / max(1e-8, np.hypot(gx, gy).sum())
        yy, xx = np.indices(image.shape)
        mass = image.sum()
        cx, cy = (xx * image).sum() / mass, (yy * image).sum() / mass
        vx = ((xx - cx) ** 2 * image).sum() / mass
        vy = ((yy - cy) ** 2 * image).sum() / mass
        cross = ((xx - cx) * (yy - cy) * image).sum() / mass / max(1e-8, vx + vy)
        mask = image > 0.5
        holes = ndimage.binary_fill_holes(mask) & ~mask
        return effective_stroke, cross, holes

    sa, ca, ha = descriptors(a)
    sb, cb, hb = descriptors(b)
    scale = max(ga["height"], ga["width"], 1.0)
    profiles = []
    for axis in [0, 1]:
        first, second = a.sum(axis=axis) / a.sum(), b.sum(axis=axis) / b.sum()
        profiles.append(
            float(np.abs(np.cumsum(first) - np.cumsum(second)).sum() / scale)
        )
    counter_error = float(
        np.logical_xor(ha, hb).sum() / max(1, np.logical_or(ha, hb).sum())
    )
    return dict(
        stroke_log=abs(float(np.log(sb / sa))),
        cross_moment=abs(float(cb - ca)),
        horizontal_profile=profiles[0],
        vertical_profile=profiles[1],
        counter_difference=counter_error,
    )
