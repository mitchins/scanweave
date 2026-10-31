//! Frozen cover-2.0 numerical primitives. All reductions use pixel order.
//! Comparisons use the frozen strict inequalities, with no epsilon enlargement.
use std::collections::VecDeque;

pub const SIDE: usize = 64;
pub type Field = Vec<f64>;

/// SciPy order=1, mode=constant sampling: outside the closed image is zero.
pub fn sample(a: &[f64], w: usize, h: usize, x: f64, y: f64) -> f64 {
    if !x.is_finite()
        || !y.is_finite()
        || x < 0.
        || y < 0.
        || x > (w - 1) as f64
        || y > (h - 1) as f64
    {
        return 0.;
    }
    let ix = x.floor() as usize;
    let iy = y.floor() as usize;
    let fx = x - ix as f64;
    let fy = y - iy as f64;
    let jx = (ix + 1).min(w - 1);
    let jy = (iy + 1).min(h - 1);
    (a[iy * w + ix] * (1. - fx) + a[iy * w + jx] * fx) * (1. - fy)
        + (a[jy * w + ix] * (1. - fx) + a[jy * w + jx] * fx) * fy
}

pub fn warp(a: &[f64], p: [f64; 3]) -> Field {
    (0..SIDE * SIDE)
        .map(|i| {
            sample(
                a,
                SIDE,
                SIDE,
                32. + (i % SIDE) as f64 / p[2] - 32. / p[2] - p[0] / p[2],
                48. + (i / SIDE) as f64 / p[2] - 48. / p[2] - p[1] / p[2],
            )
        })
        .collect()
}

pub fn mse(a: &[f64], b: &[f64]) -> f64 {
    let mut error = 0.;
    let mut ink = 0.;
    for (&x, &y) in a.iter().zip(b) {
        error += (x - y).powi(2);
        ink += x.max(y);
    }
    error / ink.max(1.)
}

pub fn quantile(a: &[f64], q: f64) -> f64 {
    let mut v = a.to_vec();
    v.sort_by(f64::total_cmp);
    let p = (v.len() - 1) as f64 * q;
    let i = p.floor() as usize;
    let f = p - i as f64;
    v[i] * (1. - f) + v[(i + 1).min(v.len() - 1)] * f
}

/// SciPy's default morphology connectivity is a cross (4-connected).
pub fn erode(mask: &[bool], w: usize, h: usize) -> Vec<bool> {
    (0..w * h)
        .map(|i| {
            let x = i % w;
            let y = i / w;
            x > 0
                && y > 0
                && x + 1 < w
                && y + 1 < h
                && mask[i]
                && mask[i - 1]
                && mask[i + 1]
                && mask[i - w]
                && mask[i + w]
        })
        .collect()
}

pub fn labels(mask: &[bool], w: usize, h: usize, eight: bool) -> (Vec<usize>, usize) {
    let mut out = vec![0; mask.len()];
    let mut count = 0;
    for i in 0..mask.len() {
        if !mask[i] || out[i] != 0 {
            continue;
        }
        count += 1;
        out[i] = count;
        let mut queue = VecDeque::from([i]);
        while let Some(k) = queue.pop_front() {
            let x = k % w;
            let y = k / w;
            for dy in -1isize..=1 {
                for dx in -1isize..=1 {
                    if dx == 0 && dy == 0 || !eight && dx != 0 && dy != 0 {
                        continue;
                    }
                    let xx = x as isize + dx;
                    let yy = y as isize + dy;
                    if xx >= 0 && yy >= 0 && xx < w as isize && yy < h as isize {
                        let j = yy as usize * w + xx as usize;
                        if mask[j] && out[j] == 0 {
                            out[j] = count;
                            queue.push_back(j);
                        }
                    }
                }
            }
        }
    }
    (out, count)
}

fn holes(mask: &[bool], eight: bool) -> Vec<bool> {
    let bg: Vec<bool> = mask.iter().map(|v| !v).collect();
    let (l, n) = labels(&bg, SIDE, SIDE, eight);
    let mut border = vec![false; n + 1];
    border[0] = true;
    for y in 0..SIDE {
        border[l[y * SIDE]] = true;
        border[l[y * SIDE + SIDE - 1]] = true;
    }
    for x in 0..SIDE {
        border[l[x]] = true;
        border[l[(SIDE - 1) * SIDE + x]] = true;
    }
    l.iter().map(|&k| !border[k]).collect()
}

fn topology(a: &[f64], threshold: f64) -> (usize, usize) {
    let mask: Vec<bool> = a.iter().map(|&v| v > threshold).collect();
    (
        labels(&mask, SIDE, SIDE, true).1,
        labels(&holes(&mask, true), SIDE, SIDE, true).1,
    )
}

/// Exact Euclidean distance to false pixels, using separable squared distances.
pub fn edt(mask: &[bool], w: usize, h: usize) -> Vec<f64> {
    let mut a = vec![f64::INFINITY; mask.len()];
    for y in 0..h {
        let zeros: Vec<usize> = (0..w).filter(|&x| !mask[y * w + x]).collect();
        for x in 0..w {
            for &z in &zeros {
                a[y * w + x] = a[y * w + x].min((x as f64 - z as f64).powi(2));
            }
        }
    }
    let mut out = vec![f64::INFINITY; mask.len()];
    for x in 0..w {
        for y in 0..h {
            for z in 0..h {
                out[y * w + x] = out[y * w + x].min(a[z * w + x] + (y as f64 - z as f64).powi(2));
            }
            out[y * w + x] = out[y * w + x].sqrt();
        }
    }
    // ndimage's all-true case uses the virtual zero at (-1, 0).
    if mask.iter().all(|&v| v) {
        for y in 0..h {
            for x in 0..w {
                out[y * w + x] = ((y as f64 + 1.).powi(2) + (x as f64).powi(2)).sqrt();
            }
        }
    }
    out
}

struct Geometry {
    area: f64,
    width: f64,
    height: f64,
    cx: f64,
    cy: f64,
    elongation: f64,
    axis: [f64; 2],
    stroke: f64,
    cross: f64,
    effective_stroke: f64,
    holes: Vec<bool>,
}
fn geometry(a: &[f64]) -> Option<Geometry> {
    let mask: Vec<bool> = a.iter().map(|&v| v > 0.5).collect();
    let ink: Vec<usize> = (0..a.len()).filter(|&i| mask[i]).collect();
    let mass: f64 = a.iter().sum();
    if ink.is_empty() || mass <= 0. {
        return None;
    }
    let cx = a
        .iter()
        .enumerate()
        .map(|(i, &v)| (i % SIDE) as f64 * v)
        .sum::<f64>()
        / mass;
    let cy = a
        .iter()
        .enumerate()
        .map(|(i, &v)| (i / SIDE) as f64 * v)
        .sum::<f64>()
        / mass;
    let (mut vx, mut vy, mut cov, mut grad) = (0., 0., 0., 0.);
    for y in 0..SIDE {
        for x in 0..SIDE {
            let i = y * SIDE + x;
            vx += (x as f64 - cx).powi(2) * a[i];
            vy += (y as f64 - cy).powi(2) * a[i];
            cov += (x as f64 - cx) * (y as f64 - cy) * a[i];
            let gx = if x == 0 {
                a[i + 1] - a[i]
            } else if x == SIDE - 1 {
                a[i] - a[i - 1]
            } else {
                (a[i + 1] - a[i - 1]) / 2.
            };
            let gy = if y == 0 {
                a[i + SIDE] - a[i]
            } else if y == SIDE - 1 {
                a[i] - a[i - SIDE]
            } else {
                (a[i + SIDE] - a[i - SIDE]) / 2.
            };
            grad += gx.hypot(gy);
        }
    }
    vx /= mass;
    vy /= mass;
    cov /= mass;
    let d = ((vx - vy).powi(2) + 4. * cov * cov).sqrt();
    let lo = (vx + vy - d) / 2.;
    let hi = (vx + vy + d) / 2.;
    let theta = 0.5 * (2. * cov).atan2(vx - vy);
    let axis = [theta.cos(), theta.sin()];
    let dist = edt(&mask, SIDE, SIDE);
    let strokes: Vec<f64> = ink.iter().map(|&i| dist[i]).collect();
    Some(Geometry {
        area: mass,
        width: (ink.iter().map(|&i| i % SIDE).max()? - ink.iter().map(|&i| i % SIDE).min()? + 1)
            as f64,
        height: (ink.iter().map(|&i| i / SIDE).max()? - ink.iter().map(|&i| i / SIDE).min()? + 1)
            as f64,
        cx,
        cy,
        elongation: (hi.max(0.01) / lo.max(0.01)).sqrt(),
        axis,
        stroke: quantile(&strokes, 0.5),
        cross: cov / (vx + vy).max(1e-8),
        effective_stroke: 2. * mass / grad.max(1e-8),
        holes: holes(&mask, false),
    })
}

/// Return the same sorted, deduplicated reason names as the research hard checks.
pub fn hard_checks(a: &[f64], b: &[f64]) -> Vec<String> {
    let (Some(ga), Some(gb)) = (geometry(a), geometry(b)) else {
        return vec!["empty_ink".into()];
    };
    let mut reasons = Vec::new();
    for (name, x, y, limit) in [
        ("area", ga.area, gb.area, 1.25),
        ("width", ga.width, gb.width, 1.18),
        ("height", ga.height, gb.height, 1.18),
        ("elongation", ga.elongation, gb.elongation, 1.5),
        ("stroke", ga.stroke, gb.stroke, 1.3),
    ] {
        let ratio = y / x.max(1e-8);
        if ratio < 1. / limit || ratio > limit {
            reasons.push(name.to_string());
        }
    }
    if topology(a, 0.5) != topology(b, 0.5) {
        reasons.push("topology".into());
    }
    if (ga.cx - gb.cx).hypot(ga.cy - gb.cy) > 2. {
        reasons.push("centroid".into());
    }
    if ga.elongation.min(gb.elongation) > 1.5
        && (ga.axis[0] * gb.axis[0] + ga.axis[1] * gb.axis[1]).abs() < 15f64.to_radians().cos()
    {
        reasons.push("orientation".into());
    }
    if (gb.effective_stroke / ga.effective_stroke).ln().abs() > 1.3f64.ln() {
        reasons.push("stroke_log".into());
    }
    if (ga.cross - gb.cross).abs() > 0.08 {
        reasons.push("cross_moment".into());
    }
    let xor = ga
        .holes
        .iter()
        .zip(&gb.holes)
        .filter(|(x, y)| x != y)
        .count();
    let union = ga
        .holes
        .iter()
        .zip(&gb.holes)
        .filter(|(x, y)| **x || **y)
        .count();
    if xor as f64 / union.max(1) as f64 > 0.35 {
        reasons.push("counter_difference".into());
    }
    for t in [0.35, 0.65] {
        if topology(a, t) != topology(b, t) {
            reasons.push(format!("counter_band_{t}"));
        }
    }
    reasons.sort();
    reasons.dedup();
    reasons
}

pub fn weight_band(a: &[f64]) -> i32 {
    let mask: Vec<bool> = a.iter().map(|&v| v > 0.5).collect();
    let eroded = erode(&mask, SIDE, SIDE);
    let boundary = mask.iter().zip(eroded).filter(|(a, b)| **a != *b).count();
    let weight = if mask.iter().any(|&v| v) {
        a.iter().sum::<f64>() / (boundary.max(1) as f64)
    } else {
        0.
    };
    (weight.max(0.1).ln() / 1.3f64.ln()).floor() as i32
}

/// Calibrated owned-ink significance; unowned dirt cannot veto.
pub fn owned_component_fires(owned_area: usize, detached: bool, area: usize, mass: f64) -> bool {
    owned_area > 0
        && if detached {
            area >= 3 && mass >= 1.5
        } else {
            area >= 4 && mass >= 3.
        }
}

/// Return significant missing owned source components, at the native pixel frame.
pub fn owned_ink(
    source: &[f64],
    current: &[f64],
    candidate: &[f64],
    w: usize,
    h: usize,
) -> Vec<usize> {
    let mask: Vec<bool> = source.iter().map(|&v| v > 0.25).collect();
    let (l, n) = labels(&mask, w, h, false);
    let mut owned = vec![0; n + 1];
    for (i, &v) in current.iter().enumerate() {
        if v > 0.15 && l[i] > 0 {
            owned[l[i]] += 1;
        }
    }
    let body = (1..=n)
        .max_by_key(|&k| (owned[k], std::cmp::Reverse(k)))
        .unwrap_or(0);
    let cd = edt(
        &current.iter().map(|&v| v <= 0.15).collect::<Vec<_>>(),
        w,
        h,
    );
    let nd = edt(
        &candidate.iter().map(|&v| v <= 0.10).collect::<Vec<_>>(),
        w,
        h,
    );
    let mut fired = Vec::new();
    for k in 1..=n {
        let mut distance = f64::INFINITY;
        let mut area = 0;
        let mut mass = 0.;
        for i in 0..source.len() {
            if l[i] != k {
                continue;
            }
            distance = distance.min(cd[i]);
            if current[i] > 0.15 && nd[i] > 1. {
                area += 1;
                mass += source[i];
            }
        }
        if owned_component_fires(owned[k], k != body && distance <= 1.5, area, mass) {
            fired.push(k);
        }
    }
    fired
}

/// Orthogonal class-footprint and topology checks, before offering a canonical.
pub fn hygiene(candidate: &[f64], independent: &[&[f64]]) -> Vec<String> {
    if independent.is_empty() {
        return vec!["no_independent_class_footprint".into()];
    }
    let mut footprint: Vec<bool> = (0..SIDE * SIDE)
        .map(|i| {
            independent.iter().filter(|a| a[i] > 0.25).count() as f64 / independent.len() as f64
                >= 0.20
        })
        .collect();
    for _ in 0..2 {
        let prev = footprint.clone();
        for i in 0..footprint.len() {
            let x = i % SIDE;
            let y = i / SIDE;
            footprint[i] = prev[i]
                || x > 0 && prev[i - 1]
                || x + 1 < SIDE && prev[i + 1]
                || y > 0 && prev[i - SIDE]
                || y + 1 < SIDE && prev[i + SIDE];
        }
    }
    let unsupported: f64 = candidate
        .iter()
        .zip(&footprint)
        .filter(|(_, f)| !**f)
        .map(|(&v, _)| v)
        .sum();
    let total: f64 = candidate.iter().sum();
    let mut reasons = Vec::new();
    if unsupported > 4. && unsupported / total.max(1.) > 0.05 {
        reasons.push("outside_independent_class_footprint".into());
    }
    let (l, n) = labels(
        &candidate.iter().map(|&v| v > 0.25).collect::<Vec<_>>(),
        SIDE,
        SIDE,
        false,
    );
    for k in 1..=n {
        let mut mass = 0.;
        let mut missing = 0.;
        for i in 0..candidate.len() {
            if l[i] == k {
                mass += candidate[i];
                if !footprint[i] {
                    missing += candidate[i];
                }
            }
        }
        if missing >= 3. && missing / mass.max(1.) > 0.5 {
            reasons.push("unsupported_component".into());
            break;
        }
    }
    let top = topology(candidate, 0.5);
    if independent
        .iter()
        .filter(|a| topology(a, 0.5) == top)
        .count() as f64
        / (independent.len() as f64)
        < 0.10
    {
        reasons.push("class_unsupported_topology".into());
    }
    reasons
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sampling_edges() {
        let a = [1., 2., 3., 4.];
        assert_eq!(sample(&a, 2, 2, 0.5, 0.5), 2.5);
        assert_eq!(sample(&a, 2, 2, -0.01, 0.), 0.);
        assert_eq!(sample(&a, 2, 2, 1., 1.), 4.);
    }
    #[test]
    fn connectivity_and_distance() {
        let a = [true, false, false, true];
        assert_eq!(labels(&a, 2, 2, true).1, 1);
        assert_eq!(labels(&a, 2, 2, false).1, 2);
        assert_eq!(edt(&a, 2, 2), vec![1., 0., 0., 1.]);
        assert_eq!(
            erode(&[true; 9], 3, 3),
            vec![false, false, false, false, true, false, false, false, false]
        );
    }
    #[test]
    fn owned_marks_and_unowned_dirt() {
        let mut a = vec![0.; 24 * 24];
        for y in 10..20 {
            for x in 8..16 {
                a[y * 24 + x] = 1.;
            }
        }
        for y in 3..5 {
            for x in 12..14 {
                a[y * 24 + x] = 1.;
            }
        }
        let mut b = a.clone();
        for y in 3..5 {
            for x in 12..14 {
                b[y * 24 + x] = 0.;
            }
        }
        assert!(!owned_ink(&a, &a, &b, 24, 24).is_empty());
        assert!(owned_ink(&a, &b, &b, 24, 24).is_empty());
        assert!(owned_ink(&a, &a, &a, 24, 24).is_empty());
    }
}

pub mod fit;

pub mod group;

pub mod plan;

pub mod source;

pub mod font;

pub mod ownership;

pub mod transport;

/// Absolute fit-error ceiling calibrated on FONT-01 train; see FONT_04_REVIEW_R2B.md.
pub const ABSOLUTE_FIT_ERROR_CEILING: f64 = 0.08;

/// Minimum distinct source designs for a shared canonical (S2a diagnosis, FONT_04_REVIEW_R2C.md).
pub const MIN_WITNESS_QUORUM: usize = 3;
