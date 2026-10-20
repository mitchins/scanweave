//! Geometric sanity checks for a refined glyph; rejected refinements retain
//! the existing observed outline. This does not classify source content.
use crate::glyphs::ContourLayer;
type P = [f64; 2];
fn polygon(c: &[P]) -> Vec<P> {
    if c.len() < 4 || !(c.len() - 1).is_multiple_of(3) {
        return Vec::new();
    }
    let mut path = kurbo::BezPath::new();
    path.move_to((c[0][0], c[0][1]));
    for i in (0..c.len() - 1).step_by(3) {
        path.curve_to(
            (c[i + 1][0], c[i + 1][1]),
            (c[i + 2][0], c[i + 2][1]),
            (c[i + 3][0], c[i + 3][1]),
        );
    }
    path.close_path();
    let mut points = Vec::new();
    kurbo::flatten(path.iter(), 0.03, |el| {
        if let kurbo::PathEl::MoveTo(p) | kurbo::PathEl::LineTo(p) = el {
            if points
                .last()
                .is_none_or(|q: &P| (p.x - q[0]).hypot(p.y - q[1]) > 1e-8)
            {
                points.push([p.x, p.y]);
            }
        }
    });
    if let Some(&first) = points.first() {
        if points.last() != Some(&first) {
            points.push(first);
        }
    }
    points
}
fn inside(poly: &[P], p: P) -> bool {
    let mut yes = false;
    for edge in poly.windows(2) {
        let (a, b) = (edge[0], edge[1]);
        if (a[1] > p[1]) != (b[1] > p[1])
            && p[0] < a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        {
            yes = !yes;
        }
    }
    yes
}
fn cross(a: P, b: P, c: P) -> f64 {
    (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
}
pub(crate) fn valid(layers: &[ContourLayer]) -> bool {
    let mut rings = Vec::new();
    let mut parents = Vec::new();
    for (outer, holes) in layers {
        let p = polygon(outer);
        if p.len() < 4 {
            return false;
        }
        let parent = rings.len();
        rings.push(p);
        parents.push(None);
        for h in holes {
            let p = polygon(h);
            if p.len() < 4 {
                return false;
            }
            rings.push(p);
            parents.push(Some(parent));
        }
    }
    for (i, p) in rings.iter().enumerate() {
        if p.iter().any(|v| !v[0].is_finite() || !v[1].is_finite()) {
            return false;
        }
        let area: f64 = p
            .windows(2)
            .map(|w| w[0][0] * w[1][1] - w[1][0] * w[0][1])
            .sum();
        if area.abs() < 1e-5 {
            return false;
        }
        if let Some(parent) = parents[i] {
            if !inside(&rings[parent], p[0]) {
                return false;
            }
        }
    }
    let mut edges = Vec::new();
    for (ring, p) in rings.iter().enumerate() {
        for (index, w) in p.windows(2).enumerate() {
            edges.push((w[0], w[1], ring, index));
        }
    }
    edges.sort_by(|a, b| a.0[0].min(a.1[0]).total_cmp(&b.0[0].min(b.1[0])));
    for i in 0..edges.len() {
        let (a, b, ring, index) = edges[i];
        let maxx = a[0].max(b[0]);
        for &(c, d, other, j) in &edges[i + 1..] {
            if c[0].min(d[0]) > maxx + 1e-8 {
                break;
            }
            if ring == other
                && (index.abs_diff(j) == 1 || index.abs_diff(j) == rings[ring].len() - 2)
            {
                continue;
            }
            if a[1].min(b[1]) > c[1].max(d[1]) + 1e-8 || c[1].min(d[1]) > a[1].max(b[1]) + 1e-8 {
                continue;
            }
            let ab_c = cross(a, b, c);
            let ab_d = cross(a, b, d);
            let cd_a = cross(c, d, a);
            let cd_b = cross(c, d, b);
            if ab_c * ab_d <= 1e-12 && cd_a * cd_b <= 1e-12 {
                return false;
            }
        }
    }
    true
}
