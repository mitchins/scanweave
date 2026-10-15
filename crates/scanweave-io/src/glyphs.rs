//! Glyph outline construction: traced contours → true compound TrueType outlines.
//! Holes become correctly-oriented contours (TrueType nonzero winding: outer
//! clockwise in font space = negative shoelace; holes positive). Cubics are
//! converted to quadratics via kurbo under the shared error budget.

use crate::trace::{Budget, TracedShape};
use kurbo::{BezPath, CubicBez, PathEl, Point, QuadBez};

#[derive(Debug, Clone)]
pub struct GlyphShape {
    pub shape_key: String,
    pub path: BezPath,
    pub num_contours: usize,
    pub num_points: usize,
    /// font-unit bbox [x0, y0, x1, y1] (all points incl. controls; for FontBBox)
    pub bbox_fu: [f64; 4],
    /// construction ink box in font units [0, cw*k, 0, ch*k]:
    /// the traced ink touches the crop edges, so SCALE maps this exactly
    pub ink_span_fu: [f64; 2],
    /// on-curve (anchor) font-unit bbox — TRANSLATION reference: the traced
    /// outline may sit sub-pixel inside the construction box on a given edge
    pub anchor_bbox_fu: [f64; 4],
    pub stages: crate::units::StageMetrics,
}

fn signed_area(points: &[[f64; 2]]) -> f64 {
    // shoelace over the anchor polyline (control points ignored for orientation)
    let n = points.len();
    let mut a = 0.0;
    for i in 0..n {
        let p = points[i];
        let q = points[(i + 1) % n];
        a += p[0] * q[1] - q[0] * p[1];
    }
    a / 2.0
}

/// Split a vtracer Spline point list into cubic segments:
/// points are 1 + 3n with consecutive cubic anchors/controls.
fn spline_to_cubics(points: &[[f64; 2]]) -> Vec<CubicBez> {
    let mut cubics = Vec::new();
    if points.len() < 4 {
        return cubics;
    }
    let mut i = 0;
    while i + 3 < points.len() {
        cubics.push(CubicBez::new(
            Point::new(points[i][0], points[i][1]),
            Point::new(points[i + 1][0], points[i + 1][1]),
            Point::new(points[i + 2][0], points[i + 2][1]),
            Point::new(points[i + 3][0], points[i + 3][1]),
        ));
        i += 3;
    }
    cubics
}

fn eval_cubic(c: &CubicBez, t: f64) -> [f64; 2] {
    let mt = 1.0 - t;
    let a = mt * mt * mt;
    let b = 3.0 * mt * mt * t;
    let d = 3.0 * mt * t * t;
    let e = t * t * t;
    [
        a * c.p0.x + b * c.p1.x + d * c.p2.x + e * c.p3.x,
        a * c.p0.y + b * c.p1.y + d * c.p2.y + e * c.p3.y,
    ]
}

fn eval_quad(q: &QuadBez, t: f64) -> [f64; 2] {
    let mt = 1.0 - t;
    [
        mt * mt * q.p0.x + 2.0 * mt * t * q.p1.x + t * t * q.p2.x,
        mt * mt * q.p0.y + 2.0 * mt * t * q.p1.y + t * t * q.p2.y,
    ]
}

fn sample_cubic(c: &CubicBez, n: usize) -> Vec<[f64; 2]> {
    (0..=n).map(|i| eval_cubic(c, i as f64 / n as f64)).collect()
}

fn sample_quad(q: &QuadBez, n: usize) -> Vec<[f64; 2]> {
    (0..=n).map(|i| eval_quad(q, i as f64 / n as f64)).collect()
}

fn poly_dist(a: &[[f64; 2]], b: &[[f64; 2]]) -> f64 {
    a.iter()
        .map(|p| {
            b.iter()
                .map(|q| (p[0] - q[0]).hypot(p[1] - q[1]))
                .fold(f64::INFINITY, f64::min)
        })
        .fold(0.0f64, f64::max)
}

pub fn build_glyph_shapes(
    traced: &[TracedShape],
    units_per_px: f64,
    budget: &Budget,
) -> Result<Vec<GlyphShape>, String> {
    let mut shapes = Vec::new();
    for t in traced {
        // transform: font units, y-up, baseline at ink bottom of the unit.
        // v = (H - y) * k where H = unit ink height in px; k = units_per_px.
        let h_px = t
            .layers
            .iter()
            .flat_map(|(o, hs)| std::iter::once(o).chain(hs.iter()))
            .flat_map(|c| c.iter())
            .map(|p| p[1])
            .fold(f64::MIN, f64::max);
        let tf = |p: &[f64; 2]| -> [f64; 2] { [p[0] * units_per_px, (h_px - p[1]) * units_per_px] };

        // transform contours FIRST, then build cubics from font-unit points,
        // preserving the per-layer (outer, holes) structure
        let transformed: Vec<(Vec<[f64; 2]>, Vec<Vec<[f64; 2]>>)> = t
            .layers
            .iter()
            .map(|(o, hs)| {
                (
                    o.iter().map(tf).collect(),
                    hs.iter()
                        .map(|h| h.iter().map(tf).collect())
                        .collect(),
                )
            })
            .collect();

        // per-contour cubics with orientation enforcement per layer:
        // TrueType nonzero winding (y-up): outer CW => negative; holes CCW => positive
        let mut contour_cubics: Vec<Vec<CubicBez>> = Vec::new();
        for (outer, holes) in &transformed {
            let mut one = outer.clone();
            if signed_area(&one) > 0.0 {
                one.reverse();
            }
            let cubics = spline_to_cubics(&one);
            if !cubics.is_empty() {
                contour_cubics.push(cubics);
            }
            for h in holes {
                let mut hp = h.clone();
                if signed_area(&hp) < 0.0 {
                    hp.reverse();
                }
                let cubics = spline_to_cubics(&hp);
                if !cubics.is_empty() {
                    contour_cubics.push(cubics);
                }
            }
        }

        // stage: cubic → quadratic under the budget (accuracy in font units)
        let acc_fu = budget.curve_max * units_per_px;
        let mut all_cubics = Vec::new();
        for c in &contour_cubics {
            all_cubics.extend(c.iter().copied());
        }
        let splines = kurbo::cubics_to_quadratic_splines(&all_cubics, acc_fu)
            .ok_or("cubics_to_quadratic_splines returned None (accuracy unattainable)")?;
        // each cubic maps to a spline of 1+ quads
        let quads_per_cubic: Vec<Vec<QuadBez>> = splines
            .iter()
            .map(|s| s.to_quads().collect())
            .collect();

        // stage metric: max deviation cubic vs its quad chain (font units → px)
        let mut curve_max_fu = 0.0f64;
        for (ci, cub) in all_cubics.iter().enumerate() {
            let sc = sample_cubic(cub, 24);
            let mut sq = Vec::new();
            for q in &quads_per_cubic[ci] {
                sq.extend(sample_quad(q, 12));
            }
            curve_max_fu = curve_max_fu.max(poly_dist(&sc, &sq));
        }

        // rebuild contours as quad chains and assemble the BezPath with winding order
        let mut path = BezPath::new();
        let mut consumed = 0usize;
        let mut num_points = 0usize;
        let mut num_contours = 0usize;
        for c in &contour_cubics {
            if c.is_empty() {
                continue;
            }
            let start = c[0].p0;
            path.move_to(start);
            num_points += 1;
            for cub in c {
                let _ = cub;
                for q in &quads_per_cubic[consumed] {
                    path.quad_to(q.p1, q.p2);
                    num_points += 2;
                }
                consumed += 1;
            }
            path.close_path();
            num_contours += 1;
        }

        // on-curve (anchor) bbox: spline anchors are p0 of each cubic + final p3
        let mut ax: Vec<f64> = Vec::new();
        let mut ay: Vec<f64> = Vec::new();
        for c in &contour_cubics {
            for cub in c {
                ax.push(cub.p0.x);
                ay.push(cub.p0.y);
            }
            if let Some(last) = c.last() {
                ax.push(last.p3.x);
                ay.push(last.p3.y);
            }
        }
        let anchor_bbox_fu = [
            ax.iter().cloned().fold(f64::INFINITY, f64::min),
            ay.iter().cloned().fold(f64::INFINITY, f64::min),
            ax.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
            ay.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
        ];
        let ink_span_fu = [t.crop_w_px as f64 * units_per_px, t.crop_h_px as f64 * units_per_px];

        // bbox in font units (already transformed)
        let xs: Vec<f64> = transformed
            .iter()
            .flat_map(|(o, hs)| std::iter::once(o).chain(hs.iter()))
            .flat_map(|c| c.iter())
            .map(|p| p[0])
            .collect();
        let ys: Vec<f64> = transformed
            .iter()
            .flat_map(|(o, hs)| std::iter::once(o).chain(hs.iter()))
            .flat_map(|c| c.iter())
            .map(|p| p[1])
            .collect();
        let bbox_fu = [
            xs.iter().cloned().fold(f64::INFINITY, f64::min),
            ys.iter().cloned().fold(f64::INFINITY, f64::min),
            xs.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
            ys.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
        ];

        // quantization bound: from_bezpath rounds to integer font units
        let quant_bound_px = 0.5 / units_per_px;

        shapes.push(GlyphShape {
            shape_key: t.shape_key.clone(),
            path,
            num_contours,
            num_points,
            bbox_fu,
            ink_span_fu,
            anchor_bbox_fu,
            stages: crate::units::StageMetrics {
                trace_max_px: t.stage.trace_max_px,
                trace_p95_px: t.stage.trace_p95_px,
                curve_max_px: curve_max_fu / units_per_px,
                quant_bound_px,
            },
        });
    }
    Ok(shapes)
}

// keep PathEl import used if needed later
#[allow(dead_code)]
fn _els(p: &BezPath) -> Vec<PathEl> {
    p.elements().to_vec()
}
