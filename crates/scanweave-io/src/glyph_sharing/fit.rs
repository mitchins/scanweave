//! Derived from SciPy TRF least-squares algorithm; BSD-3-Clause notice in
//! THIRD_PARTY_LICENSES/scipy.txt. No SciPy or Python runtime dependency.
//! Three-parameter bounded trust-region reflective least squares, Huber loss.
//! Algorithm: Coleman-Li scaling, exact dense trust-region subproblem, reflected
//! and gradient candidate steps. The frozen SciPy settings are used verbatim.
use super::{warp, Field};
type V = [f64; 3];
type M = [[f64; 3]; 3];
const LOWER: V = [-2., -2., 0.98];
const UPPER: V = [2., 2., 1.02];
fn dot(a: V, b: V) -> f64 {
    (0..3).map(|i| a[i] * b[i]).sum()
}
fn norm(a: V) -> f64 {
    dot(a, a).sqrt()
}
fn mul(a: M, b: V) -> V {
    std::array::from_fn(|i| dot(a[i], b))
}
fn add(a: V, b: V) -> V {
    std::array::from_fn(|i| a[i] + b[i])
}
fn scale(a: V, s: f64) -> V {
    a.map(|v| v * s)
}
fn quad(h: M, g: V, p: V) -> f64 {
    0.5 * dot(p, mul(h, p)) + dot(g, p)
}
fn cost(f: &[f64]) -> f64 {
    f.iter()
        .map(|&v| {
            if v.abs() <= 0.12 {
                0.5 * v * v
            } else {
                0.12 * v.abs() - 0.5 * 0.12 * 0.12
            }
        })
        .sum()
}
fn residual(a: &[f64], b: &[f64], p: V) -> Field {
    warp(b, p).iter().zip(a).map(|(b, a)| b - a).collect()
}

// Symmetric eigensystem of the 3x3 normal matrix. Fixed pivot order and serial
// reductions make it independent of thread scheduling. No decisions use epsilon.
fn eigen(mut a: M) -> (V, M) {
    let mut vectors = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];
    for _ in 0..32 {
        for (p, q) in [(0, 1), (0, 2), (1, 2)] {
            if a[p][q] == 0. {
                continue;
            }
            let tau = (a[q][q] - a[p][p]) / (2. * a[p][q]);
            let t = if tau >= 0. { 1. } else { -1. } / (tau.abs() + (1. + tau * tau).sqrt());
            let c = 1. / (1. + t * t).sqrt();
            let s = t * c;
            let apq = a[p][q];
            a[p][p] -= t * apq;
            a[q][q] += t * apq;
            a[p][q] = 0.;
            a[q][p] = 0.;
            for k in 0..3 {
                if k != p && k != q {
                    let x = a[k][p];
                    let y = a[k][q];
                    a[k][p] = c * x - s * y;
                    a[p][k] = a[k][p];
                    a[k][q] = s * x + c * y;
                    a[q][k] = a[k][q];
                }
                let x = vectors[k][p];
                let y = vectors[k][q];
                vectors[k][p] = c * x - s * y;
                vectors[k][q] = s * x + c * y;
            }
        }
    }
    let mut indices = [0, 1, 2];
    indices.sort_by(|&i, &j| a[j][j].total_cmp(&a[i][i]));
    (
        indices.map(|i| a[i][i].max(0.)),
        std::array::from_fn(|i| indices.map(|j| vectors[i][j])),
    )
}
fn trust(h: M, g: V, delta: f64, initial: f64) -> (V, f64) {
    let (e, v) = eigen(h);
    let z: V = std::array::from_fn(|j| (0..3).map(|i| v[i][j] * g[i]).sum());
    let full = e[2].sqrt() > f64::EPSILON * 4096. * e[0].sqrt();
    let phi = |alpha: f64| {
        let den = e.map(|x| x + alpha);
        let pn = norm(std::array::from_fn(|i| z[i] / den[i]));
        (
            pn - delta,
            -(0..3).map(|i| z[i] * z[i] / den[i].powi(3)).sum::<f64>() / pn,
        )
    };
    let point = |alpha: f64| {
        std::array::from_fn(|i| -(0..3).map(|j| v[i][j] * z[j] / (e[j] + alpha)).sum::<f64>())
    };
    if full {
        let p = point(0.);
        if norm(p) <= delta {
            return (p, 0.);
        }
    }
    let mut upper = norm(z) / delta;
    let mut lower = if full {
        let (p, d) = phi(0.);
        -p / d
    } else {
        0.
    };
    let mut alpha = initial;
    if !full && alpha == 0. {
        alpha = (0.001 * upper).max((lower * upper).sqrt());
    }
    for _ in 0..10 {
        if alpha < lower || alpha > upper {
            alpha = (0.001 * upper).max((lower * upper).sqrt());
        }
        let (p, d) = phi(alpha);
        if p < 0. {
            upper = alpha;
        }
        let ratio = p / d;
        lower = lower.max(alpha - ratio);
        alpha -= (p + delta) * ratio / delta;
        if p.abs() < 0.01 * delta {
            break;
        }
    }
    let p = point(alpha);
    (scale(p, delta / norm(p)), alpha)
}
fn bound(x: V, p: V) -> (f64, [bool; 3]) {
    let s: V = std::array::from_fn(|i| {
        if p[i] == 0. {
            f64::INFINITY
        } else {
            ((LOWER[i] - x[i]) / p[i]).max((UPPER[i] - x[i]) / p[i])
        }
    });
    let stride = s.iter().copied().fold(f64::INFINITY, f64::min);
    (stride, s.map(|v| v == stride))
}
fn minimize(h: M, g: V, d: V, origin: V, lo: f64, hi: f64) -> (f64, f64) {
    let a = 0.5 * dot(d, mul(h, d));
    let b = dot(d, add(mul(h, origin), g));
    let c = quad(h, g, origin);
    let mut candidates = vec![lo, hi];
    if a != 0. {
        let t = -0.5 * b / a;
        if t > lo && t < hi {
            candidates.push(t);
        }
    }
    candidates
        .into_iter()
        .map(|t| (t, a * t * t + b * t + c))
        .min_by(|a, b| a.1.total_cmp(&b.1))
        .unwrap()
}
fn select(x: V, h: M, g: V, p_h: V, d: V, delta: f64, theta: f64) -> (V, V, f64) {
    let p: V = std::array::from_fn(|i| p_h[i] * d[i]);
    let trial = add(x, p);
    if (0..3).all(|i| trial[i] >= LOWER[i] && trial[i] <= UPPER[i]) {
        return (p, p_h, -quad(h, g, p_h));
    }
    let (stride, hits) = bound(x, p);
    let r_h: V = std::array::from_fn(|i| if hits[i] { -p_h[i] } else { p_h[i] });
    let r: V = std::array::from_fn(|i| r_h[i] * d[i]);
    let p = scale(p, stride);
    let ph = scale(p_h, stride);
    let on = add(x, p);
    let aa = dot(r_h, r_h);
    let bb = dot(ph, r_h);
    let cc = dot(ph, ph) - delta * delta;
    let disc = (bb * bb - aa * cc).sqrt();
    let q = -(bb + if bb >= 0. { disc } else { -disc });
    let to_tr = (q / aa).max(cc / q);
    let (to_bound, _) = bound(on, r);
    let rstride = to_bound.min(to_tr);
    let (lo, hi) = if rstride > 0. {
        (
            (1. - theta) * stride / rstride,
            if rstride == to_bound {
                theta * to_bound
            } else {
                to_tr
            },
        )
    } else {
        (0., -1.)
    };
    let (reflected, rv) = if lo <= hi {
        let (t, v) = minimize(h, g, r_h, ph, lo, hi);
        (add(ph, scale(r_h, t)), v)
    } else {
        ([0.; 3], f64::INFINITY)
    };
    let ph = scale(ph, theta);
    let pv = quad(h, g, ph);
    let ag = scale(g, -1.);
    let original: V = std::array::from_fn(|i| ag[i] * d[i]);
    let (to_bound, _) = bound(x, original);
    let to_tr = delta / norm(ag);
    let hi = if to_bound < to_tr {
        theta * to_bound
    } else {
        to_tr
    };
    let (t, av) = minimize(h, g, ag, [0.; 3], 0., hi);
    let ah = scale(ag, t);
    let (chosen, value) = if pv < rv && pv < av {
        (ph, pv)
    } else if rv < pv && rv < av {
        (reflected, rv)
    } else {
        (ah, av)
    };
    (std::array::from_fn(|i| chosen[i] * d[i]), chosen, -value)
}

/// Frozen bounded fit. At most 35 objective evaluations; numerical Jacobians
/// use relative step .001 (sqrt(EPS) at zero), Huber .12, all tolerances 1e-5.
pub fn register(a: &[f64], b: &[f64]) -> ([f64; 3], Field) {
    let mut x = [0., 0., 1.];
    let mut f = residual(a, b, x);
    let mut value = cost(&f);
    let mut nfev = 1;
    let mut alpha = 0.;
    let mut delta = 0.;
    'outer: loop {
        let mut j = vec![[0.; 3]; f.len()];
        for k in 0..3 {
            let mut step = 0.001 * x[k];
            if step == 0. {
                step = f64::EPSILON.sqrt();
            }
            if x[k] + step > UPPER[k] || x[k] + step < LOWER[k] {
                if step.abs() <= ((UPPER[k] - x[k]).max(x[k] - LOWER[k])) {
                    step = -step;
                } else {
                    step = if UPPER[k] - x[k] >= x[k] - LOWER[k] {
                        UPPER[k] - x[k]
                    } else {
                        LOWER[k] - x[k]
                    };
                }
            }
            let mut xx = x;
            xx[k] += step;
            let actual = xx[k] - x[k];
            let ff = residual(a, b, xx);
            for i in 0..f.len() {
                j[i][k] = (ff[i] - f[i]) / actual;
            }
        }
        let mut g = [0.; 3];
        let mut normal = [[0.; 3]; 3];
        for i in 0..f.len() {
            let abs = f[i].abs();
            let rho1 = if abs <= 0.12 { 1. } else { 0.12 / abs };
            let root = if abs <= 0.12 { 1. } else { f64::EPSILON.sqrt() };
            let scaled_f = f[i] * rho1 / root;
            let row = j[i].map(|v| v * root);
            for k in 0..3 {
                g[k] += row[k] * scaled_f;
                for l in 0..3 {
                    normal[k][l] += row[k] * row[l];
                }
            }
        }
        let v: V = std::array::from_fn(|i| {
            if g[i] < 0. {
                UPPER[i] - x[i]
            } else if g[i] > 0. {
                x[i] - LOWER[i]
            } else {
                1.
            }
        });
        let dv: V = g.map(|v| {
            if v < 0. {
                -1.
            } else if v > 0. {
                1.
            } else {
                0.
            }
        });
        let gn = (0..3).map(|i| (g[i] * v[i]).abs()).fold(0., f64::max);
        if gn < 1e-5 || nfev == 35 {
            break;
        }
        if delta == 0. {
            delta = norm(std::array::from_fn(|i| x[i] / v[i].sqrt()));
            if delta == 0. {
                delta = 1.;
            }
        }
        let d = v.map(f64::sqrt);
        let gh: V = std::array::from_fn(|i| d[i] * g[i]);
        let h: M = std::array::from_fn(|i| {
            std::array::from_fn(|k| {
                normal[i][k] * d[i] * d[k] + if i == k { g[i] * dv[i] } else { 0. }
            })
        });
        let theta = (1. - gn).max(0.995);
        while nfev < 35 {
            let (ph, aa) = trust(h, gh, delta, alpha);
            alpha = aa;
            let (step, sh, pred) = select(x, h, gh, ph, d, delta, theta);
            let mut xx = add(x, step);
            for i in 0..3 {
                if xx[i] <= LOWER[i] {
                    xx[i] = LOWER[i].next_up();
                }
                if xx[i] >= UPPER[i] {
                    xx[i] = UPPER[i].next_down();
                }
            }
            let ff = residual(a, b, xx);
            nfev += 1;
            let vv = cost(&ff);
            let actual = value - vv;
            let sn = norm(sh);
            let ratio = if pred > 0. {
                actual / pred
            } else if actual == 0. && pred == 0. {
                1.
            } else {
                0.
            };
            let new_delta = if ratio < 0.25 {
                0.25 * sn
            } else if ratio > 0.75 && sn > 0.95 * delta {
                delta * 2.
            } else {
                delta
            };
            let terminate =
                actual < 1e-5 * value && ratio > 0.25 || norm(step) < 1e-5 * (1e-5 + norm(x));
            if actual > 0. {
                x = xx;
                f = ff;
                value = vv;
            }
            if terminate {
                break 'outer;
            }
            alpha *= delta / new_delta;
            delta = new_delta;
            if actual > 0. {
                break;
            }
        }
    }
    (x, warp(b, x))
}
