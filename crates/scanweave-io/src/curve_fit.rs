//! Subpixel coverage contours in the original observation's pixel-edge frame.
//! Binary ownership bounds the evidence footprint; edge locations come from
//! normalized grayscale samples, not from an enlarged thresholded bitmap.
use crate::{glyphs::ContourLayer, units::Unit};
use std::collections::BTreeMap;
type P = [f64; 2];
type Key = (i64, i64);
fn key(p: P) -> Key {
    ((p[0] * 1e7).round() as i64, (p[1] * 1e7).round() as i64)
}
fn area(p: &[P]) -> f64 {
    p.iter()
        .zip(p.iter().cycle().skip(1))
        .map(|(a, b)| a[0] * b[1] - a[1] * b[0])
        .sum::<f64>()
        * 0.5
}
fn contains(poly: &[P], p: P) -> bool {
    let mut inside = false;
    for (a, b) in poly.iter().zip(poly.iter().cycle().skip(1)) {
        if (a[1] > p[1]) != (b[1] > p[1])
            && p[0] < a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        {
            inside = !inside;
        }
    }
    inside
}
fn spline(poly: &[P]) -> Vec<P> {
    fit_ring(poly, 0.15)
}
pub(crate) fn layers(unit: &Unit, paper: f64, ink: f64, level: f64) -> Option<Vec<ContourLayer>> {
    let gray = unit.gray_samples.as_deref()?;
    let w = unit.crop_w as isize;
    let h = unit.crop_h as isize;
    if gray.len() != unit.mask.len() || w < 2 || h < 2 {
        return None;
    }
    let sample = |x: isize, y: isize| -> f64 {
        // Only observations adjacent to owned ink can create an outline. This
        // excludes neighboring punctuation/artwork in the grayscale halo.
        let nearby = (-1..=1).any(|dy| {
            (-1..=1).any(|dx| {
                let xx = x + dx;
                let yy = y + dy;
                xx >= 0 && yy >= 0 && xx < w && yy < h && unit.mask[(yy * w + xx) as usize]
            })
        });
        if !nearby {
            return 0.0;
        }
        let value = if x >= 0 && y >= 0 && x < w && y < h {
            gray[(y * w + x) as usize]
        } else if let Some(halo) = unit.gray_halo.as_deref() {
            halo[((y + 2) * (w + 4) + x + 2) as usize]
        } else {
            255
        };
        ((paper - value as f64) / (paper - ink)).clamp(0.0, 1.0)
    };
    let mut segments: Vec<(P, P)> = Vec::new();
    for y in -1..h {
        for x in -1..w {
            let p = [
                [x as f64 + 0.5, y as f64 + 0.5],
                [x as f64 + 1.5, y as f64 + 0.5],
                [x as f64 + 1.5, y as f64 + 1.5],
                [x as f64 + 0.5, y as f64 + 1.5],
            ];
            let v = [
                sample(x, y),
                sample(x + 1, y),
                sample(x + 1, y + 1),
                sample(x, y + 1),
            ];
            let mut hits: Vec<(usize, P)> = Vec::new();
            for e in 0..4 {
                let n = (e + 1) % 4;
                if (v[e] >= level) != (v[n] >= level) {
                    let t = (level - v[e]) / (v[n] - v[e]);
                    hits.push((
                        e,
                        [
                            p[e][0] + t * (p[n][0] - p[e][0]),
                            p[e][1] + t * (p[n][1] - p[e][1]),
                        ],
                    ));
                }
            }
            if hits.len() == 2 {
                segments.push((hits[0].1, hits[1].1));
            } else if hits.len() == 4 {
                let center = v.iter().sum::<f64>() >= 4.0 * level;
                let northwest = v[0] >= level;
                let pairs = if center == northwest {
                    [(0, 1), (2, 3)]
                } else {
                    [(3, 0), (1, 2)]
                };
                for (a, b) in pairs {
                    segments.push((hits[a].1, hits[b].1));
                }
            }
        }
    }
    let mut vertices: BTreeMap<Key, Vec<usize>> = BTreeMap::new();
    for (i, (a, b)) in segments.iter().enumerate() {
        vertices.entry(key(*a)).or_default().push(i);
        vertices.entry(key(*b)).or_default().push(i);
    }
    if vertices.values().any(|v| v.len() != 2) {
        return None;
    }
    let mut used = vec![false; segments.len()];
    let mut rings = Vec::new();
    for start in 0..segments.len() {
        if used[start] {
            continue;
        }
        let first = segments[start].0;
        let mut current = first;
        let mut edge = start;
        let mut ring = Vec::new();
        for _ in 0..=segments.len() {
            if used[edge] {
                break;
            }
            used[edge] = true;
            ring.push(current);
            let (a, b) = segments[edge];
            current = if key(a) == key(current) { b } else { a };
            if key(current) == key(first) {
                break;
            }
            edge = *vertices.get(&key(current))?.iter().find(|&&i| !used[i])?;
        }
        if key(current) != key(first) || ring.len() < 3 {
            return None;
        }
        if area(&ring).abs() > 0.1 {
            rings.push(ring);
        }
    }
    let depths: Vec<usize> = rings
        .iter()
        .enumerate()
        .map(|(i, r)| {
            rings
                .iter()
                .enumerate()
                .filter(|(j, p)| *j != i && contains(p, r[0]))
                .count()
        })
        .collect();
    let mut output = Vec::new();
    for (i, r) in rings.iter().enumerate() {
        if depths[i] % 2 != 0 {
            continue;
        }
        let holes = rings
            .iter()
            .enumerate()
            .filter(|(j, h)| {
                depths[*j] == depths[i] + 1 && contains(r, h[0]) && area(h).abs() >= 0.8
            })
            .map(|(_, h)| spline(h))
            .collect();
        output.push((spline(r), holes));
    }
    (!output.is_empty()).then_some(output)
}

fn sub(a: P, b: P) -> P {
    [a[0] - b[0], a[1] - b[1]]
}
fn add(a: P, b: P) -> P {
    [a[0] + b[0], a[1] + b[1]]
}
fn mul(a: P, k: f64) -> P {
    [a[0] * k, a[1] * k]
}
fn dot(a: P, b: P) -> f64 {
    a[0] * b[0] + a[1] * b[1]
}
fn unit(a: P) -> P {
    mul(a, 1.0 / dot(a, a).sqrt().max(1e-12))
}
fn eval(c: &[P; 4], t: f64) -> P {
    let u = 1. - t;
    add(
        add(mul(c[0], u * u * u), mul(c[1], 3. * u * u * t)),
        add(mul(c[2], 3. * u * t * t), mul(c[3], t * t * t)),
    )
}
fn generate(p: &[P], u: &[f64], left: P, right: P) -> [P; 4] {
    let end = *p.last().unwrap();
    let (mut aa, mut ab, mut bb, mut ax, mut bx) = (0., 0., 0., 0., 0.);
    for (&pt, &t) in p.iter().zip(u) {
        let v = 1. - t;
        let b0 = v * v * v;
        let b1 = 3. * v * v * t;
        let b2 = 3. * v * t * t;
        let b3 = t * t * t;
        let a = mul(left, b1);
        let b = mul(right, b2);
        let residual = sub(pt, add(mul(p[0], b0 + b1), mul(end, b2 + b3)));
        aa += dot(a, a);
        ab += dot(a, b);
        bb += dot(b, b);
        ax += dot(a, residual);
        bx += dot(b, residual);
    }
    let det = aa * bb - ab * ab;
    let chord = dot(sub(end, p[0]), sub(end, p[0])).sqrt();
    let (mut l, mut r) = if det.abs() > 1e-12 {
        ((ax * bb - bx * ab) / det, (aa * bx - ab * ax) / det)
    } else {
        (chord / 3., chord / 3.)
    };
    if l < chord * 1e-4 || r < chord * 1e-4 || l > chord * 2. || r > chord * 2. {
        l = chord / 3.;
        r = l;
    }
    [p[0], add(p[0], mul(left, l)), add(end, mul(right, r)), end]
}
fn fit_open(p: &[P], left: P, right: P, accuracy: f64, depth: usize, out: &mut Vec<[P; 4]>) {
    if p.len() < 2 {
        return;
    }
    let mut u = vec![0.];
    for w in p.windows(2) {
        u.push(u.last().unwrap() + dot(sub(w[1], w[0]), sub(w[1], w[0])).sqrt());
    }
    let len = *u.last().unwrap();
    if len < 1e-9 {
        return;
    }
    for t in &mut u {
        *t /= len;
    }
    let mut c = generate(p, &u, left, right);
    let mut split = p.len() / 2;
    for iteration in 0..5 {
        let mut error = 0.;
        for i in 1..p.len() - 1 {
            let d = sub(eval(&c, u[i]), p[i]);
            let e = dot(d, d);
            if e > error {
                error = e;
                split = i;
            }
        }
        if error <= accuracy * accuracy || p.len() == 2 || depth >= 16 {
            out.push(c);
            return;
        }
        if iteration == 4 {
            break;
        }
        let mut next = u.clone();
        for i in 1..p.len() - 1 {
            let t = u[i];
            let v = 1. - t;
            let q = eval(&c, t);
            let d = mul(
                add(
                    add(
                        mul(sub(c[1], c[0]), v * v),
                        mul(sub(c[2], c[1]), 2. * v * t),
                    ),
                    mul(sub(c[3], c[2]), t * t),
                ),
                3.,
            );
            let dd = mul(
                add(
                    mul(add(sub(c[2], mul(c[1], 2.)), c[0]), v),
                    mul(add(sub(c[3], mul(c[2], 2.)), c[1]), t),
                ),
                6.,
            );
            let delta = sub(q, p[i]);
            let denom = dot(d, d) + dot(delta, dd);
            if denom.abs() > 1e-9 {
                next[i] = (t - dot(delta, d) / denom).clamp(0., 1.);
            }
        }
        if next.windows(2).any(|w| w[1] <= w[0]) {
            break;
        }
        u = next;
        c = generate(p, &u, left, right);
    }
    split = split.clamp(1, p.len() - 2);
    let tangent = unit(sub(p[split - 1], p[split + 1]));
    fit_open(&p[..=split], left, tangent, accuracy, depth + 1, out);
    fit_open(
        &p[split..],
        mul(tangent, -1.),
        right,
        accuracy,
        depth + 1,
        out,
    );
}
/// Fit closed contours at source-pixel accuracy. Corners are detected over a
/// physical neighborhood, not at individual marching-square staircase turns.
pub(crate) fn fit_ring(poly: &[P], accuracy: f64) -> Vec<P> {
    if poly.len() < 3 {
        return Vec::new();
    }
    let mut original = poly.to_vec();
    if dot(
        sub(original[0], *original.last().unwrap()),
        sub(original[0], *original.last().unwrap()),
    ) < 1e-12
    {
        original.pop();
    }
    let n = original.len();
    let mut arc = vec![0.];
    for i in 0..n {
        arc.push(
            arc[i]
                + dot(
                    sub(original[(i + 1) % n], original[i]),
                    sub(original[(i + 1) % n], original[i]),
                )
                .sqrt(),
        );
    }
    let length = arc[n];
    if length < 1e-6 {
        return Vec::new();
    }
    let count = (length / 0.35).ceil().max(12.) as usize;
    let mut p = Vec::new();
    let mut edge = 0;
    for i in 0..count {
        let d = length * i as f64 / count as f64;
        while edge + 1 < n && arc[edge + 1] < d {
            edge += 1;
        }
        let t = (d - arc[edge]) / (arc[edge + 1] - arc[edge]).max(1e-12);
        p.push(add(
            original[edge],
            mul(sub(original[(edge + 1) % n], original[edge]), t),
        ));
    }
    let radius = ((1.3 * count as f64 / length).round() as usize)
        .max(1)
        .min(count / 4);
    let turn: Vec<f64> = (0..count)
        .map(|i| {
            let a = unit(sub(p[i], p[(i + count - radius) % count]));
            let b = unit(sub(p[(i + radius) % count], p[i]));
            dot(a, b).clamp(-1., 1.).acos()
        })
        .collect();
    let mut corners: Vec<usize> = (0..count)
        .filter(|&i| {
            turn[i] > 65f64.to_radians()
                && (1..=radius).all(|j| {
                    turn[i] > turn[(i + count - j) % count] && turn[i] >= turn[(i + j) % count]
                })
        })
        .collect();
    if corners.len() < 2 {
        corners = vec![0, count / 2];
    }
    let mut curves = Vec::new();
    for j in 0..corners.len() {
        let a = corners[j];
        let b = if j + 1 < corners.len() {
            corners[j + 1]
        } else {
            corners[0] + count
        };
        let points: Vec<_> = (a..=b).map(|i| p[i % count]).collect();
        let k = 3.min(points.len() - 1);
        let left = if turn[a] < 65f64.to_radians() {
            unit(sub(p[(a + 2) % count], p[(a + count - 2) % count]))
        } else {
            unit(sub(points[k], points[0]))
        };
        let end = b % count;
        let right = if turn[end] < 65f64.to_radians() {
            unit(sub(p[(end + count - 2) % count], p[(end + 2) % count]))
        } else {
            unit(sub(points[points.len() - 1 - k], *points.last().unwrap()))
        };
        fit_open(&points, left, right, accuracy, 0, &mut curves);
    }
    let Some(first) = curves.first() else {
        return Vec::new();
    };
    let mut out = vec![first[0]];
    for c in curves {
        out.extend_from_slice(&c[1..]);
    }
    if let Some(last) = out.last_mut() {
        *last = p[corners[0]];
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn circle_is_compact_closed_and_has_shared_tangents() {
        let poly: Vec<_> = (0..256)
            .map(|i| {
                let a = std::f64::consts::TAU * i as f64 / 256.;
                [24. + 18. * a.cos(), 24. + 18. * a.sin()]
            })
            .collect();
        let c = fit_ring(&poly, 0.15);
        assert_eq!(c.first(), c.last());
        assert_eq!((c.len() - 1) % 3, 0);
        assert!(c.len() < 70, "{}", c.len());
        let n = (c.len() - 1) / 3;
        for i in 0..n {
            let at = i * 3;
            let incoming = unit(sub(c[at], c[if i == 0 { 3 * n - 1 } else { at - 1 }]));
            let outgoing = unit(sub(c[at + 1], c[at]));
            assert!(dot(incoming, outgoing) > 0.999);
        }
    }
    #[test]
    fn square_keeps_sharp_terminals() {
        let c = fit_ring(&[[0., 0.], [20., 0.], [20., 16.], [0., 16.]], 0.15);
        assert_eq!(c.first(), c.last());
        for corner in [[0., 0.], [20., 0.], [20., 16.], [0., 16.]] {
            assert!(crate::trace::sample_spline(&c, 12)
                .iter()
                .any(|p| dot(sub(*p, corner), sub(*p, corner)) < 0.1));
        }
    }
    #[test]
    fn grayscale_annulus_keeps_counter_and_subpixel_edges() {
        let (w, h) = (48, 48);
        let mut gray = Vec::new();
        for y in 0..h {
            for x in 0..w {
                let mut coverage = 0;
                for sy in 0..8 {
                    for sx in 0..8 {
                        let xx = x as f64 + (sx as f64 + 0.5) / 8. - 24.;
                        let yy = y as f64 + (sy as f64 + 0.5) / 8. - 24.;
                        let outer = xx * xx / 324. + yy * yy / 400.;
                        let inner = xx * xx / 100. + yy * yy / 144.;
                        coverage += usize::from(outer < 1. && inner > 1.);
                    }
                }
                gray.push((255. * (1. - coverage as f64 / 64.)).round() as u8);
            }
        }
        let u = Unit {
            shape_key: "annulus".into(),
            span_id: "s".into(),
            symbol_id: "s".into(),
            semantic_text: "0".into(),
            bbox_px: [0., 0., 48., 48.],
            ocr_bbox_px: [0., 0., 48., 48.],
            crop_w: w,
            crop_h: h,
            mask: gray.iter().map(|v| *v < 195).collect(),
            gray_samples: Some(gray),
            gray_halo: None,
        };
        let l = layers(&u, 255., 0., 0.5).unwrap();
        assert_eq!(l.len(), 1);
        assert_eq!(l[0].1.len(), 1);
        assert!(crate::contour_topology::valid(&l));
        assert!(l[0].0.len() < 100);
        assert!(l[0].0.iter().any(|p| (p[0] - p[0].round()).abs() > 0.05));
    }
}
