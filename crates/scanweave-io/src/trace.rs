//! Tracing: unit mask → VTracer compound contours (outer + holes as separate
//! path elements), with stage-wise error metrics under the m0-probe-1 budget.

use crate::units::Unit;
use visioncortex::CompoundPathElement;

pub struct Budget {
    pub trace_max: f64,
    pub curve_max: f64,
    pub quant_max: f64,
}

impl Budget {
    pub fn from_m0_policy() -> Self {
        // qualification/policy/m0-probe-1.toml values (parsed manually: policy is a
        // reviewed artifact, not runtime configuration)
        Budget {
            trace_max: 0.50,
            curve_max: 0.25,
            quant_max: 0.25,
        }
    }
}

pub struct TracedShape {
    pub shape_key: String,
    /// crop dims in px: the ink touches all four crop edges by construction,
    /// so in font units the ink spans exactly [0, cw*k] x [0, ch*k]
    pub crop_w_px: usize,
    pub crop_h_px: usize,
    /// dense sampled polylines per contour (crop-local, source-pixel space),
    /// outer contours and holes in paint order
    pub polylines: Vec<Vec<[f64; 2]>>,
    /// per-layer contours in traced image coordinates (y down):
    /// each layer = (outer, holes...) from vtracer Cutout hierarchy
    pub layers: Vec<(Vec<[f64; 2]>, Vec<Vec<[f64; 2]>>)>,
    pub stage: StageRaw,
}

pub struct StageRaw {
    pub trace_max_px: f64,
    pub trace_p95_px: f64,
}

/// supersampling factor for tracing (0.5px corner resolution in source space)
pub const SS: usize = 2;

fn vtracer_config() -> vtracer::Config {
    let mut cfg = vtracer::Config::default();
    cfg.color_mode = vtracer::ColorMode::Binary;
    cfg.hierarchical = vtracer::Hierarchical::Cutout;
    cfg.mode = visioncortex::PathSimplifyMode::Spline;
    cfg.filter_speckle = 0; // never drop small marks (VS-05 discipline)
    cfg.corner_threshold = 0; // no corner smoothing (measured: reduces deviation)
    cfg.length_threshold = 1.0; // minimal reduction (0 disables reduction upstream — measured identical to 4.0)
    cfg.max_iterations = 10;
    cfg.splice_threshold = 45;
    cfg.path_precision = None;
    cfg
}

/// Contours from one CompoundPath: element[0] outer, remaining elements holes.
/// Spline points are 1 + 3n (cubic chains) and are kept as control-point lists;
/// curve sampling for metrics happens in boundary_error.
fn compound_contours(path: &visioncortex::CompoundPath) -> Vec<Vec<[f64; 2]>> {
    let mut out = Vec::new();
    for el in path.iter() {
        match el {
            CompoundPathElement::Spline(s) => {
                let contour: Vec<[f64; 2]> =
                    s.points.iter().map(|p| [p.x, p.y]).collect();
                out.push(contour);
            }
            CompoundPathElement::PathF64(p) => {
                out.push(p.path.iter().map(|pt| [pt.x, pt.y]).collect());
            }
            CompoundPathElement::PathI32(p) => {
                out.push(p.path.iter().map(|pt| [pt.x as f64, pt.y as f64]).collect());
            }
        }
    }
    out
}

/// Sample the actual cubic curve (not control points) densely.
pub(crate) fn sample_spline(points: &[[f64; 2]], per_segment: usize) -> Vec<[f64; 2]> {
    let mut out = Vec::new();
    if points.len() < 4 {
        return points.to_vec();
    }
    let mut i = 0;
    while i + 3 < points.len() {
        let (p0, p1, p2, p3) = (points[i], points[i + 1], points[i + 2], points[i + 3]);
        for k in 0..per_segment {
            let t = k as f64 / per_segment as f64;
            let mt = 1.0 - t;
            out.push([
                mt*mt*mt*p0[0] + 3.0*mt*mt*t*p1[0] + 3.0*mt*t*t*p2[0] + t*t*t*p3[0],
                mt*mt*mt*p0[1] + 3.0*mt*mt*t*p1[1] + 3.0*mt*t*t*p2[1] + t*t*t*p3[1],
            ]);
        }
        i += 3;
    }
    out.push(*points.last().unwrap());
    out
}

/// Distance from each sampled contour point to the nearest mask-boundary pixel.
fn boundary_error(contours: &[Vec<[f64; 2]>], unit: &Unit) -> (f64, f64) {
    // mask boundary in PIXEL-EDGE coordinates: vtracer paths walk pixel corners,
    // so the reference contour is the set of grid corners adjacent to both ink
    // and non-ink pixels (marching-squares vertices).
    let (cw, ch) = (unit.crop_w, unit.crop_h);
    let at = |x: i64, y: i64| -> bool {
        if x < 0 || y < 0 || x >= cw as i64 || y >= ch as i64 {
            false
        } else {
            unit.mask[(y as usize) * cw + (x as usize)]
        }
    };
    let mut boundary = Vec::new();
    for y in -1..ch as i64 + 1 {
        for x in -1..cw as i64 + 1 {
            // corner (x,y) touches 4 pixels
            let quads = [at(x - 1, y - 1), at(x, y - 1), at(x - 1, y), at(x, y)];
            let ink = quads.iter().filter(|q| **q).count();
            if ink > 0 && ink < 4 {
                boundary.push([x as f64, y as f64]);
            }
        }
    }
    if boundary.is_empty() {
        return (0.0, 0.0);
    }
    let mut dists = Vec::new();
    for c in contours {
        let sampled = sample_spline(c, 12);
        for p in &sampled {
            let d = boundary
                .iter()
                .map(|q| (p[0] - q[0]).hypot(p[1] - q[1]))
                .fold(f64::INFINITY, f64::min);
            dists.push(d);
        }
    }
    dists.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let max = *dists.last().unwrap_or(&0.0);
    let p95 = dists[(dists.len() as f64 * 0.95) as usize % dists.len()];
    (max, p95)
}

pub fn trace_shape(unit: &Unit, _budget: &Budget, _units_per_px: f64) -> Result<TracedShape, String> {
    // trace a SSx-upscaled mask: finer corner grid in source space
    let (sw, sh) = (unit.crop_w * SS, unit.crop_h * SS);
    let mut pixels = vec![255u8; sw * sh * 4];
    for y in 0..sh {
        for x in 0..sw {
            if unit.mask[(y / SS) * unit.crop_w + (x / SS)] {
                let i = (y * sw + x) * 4;
                pixels[i] = 0;
                pixels[i + 1] = 0;
                pixels[i + 2] = 0;
                pixels[i + 3] = 255;
            }
        }
    }
    let mut img = visioncortex::ColorImage::new();
    img.pixels = pixels;
    (img.width, img.height) = (sw, sh);

    let svg = vtracer::convert(img, vtracer_config()).map_err(|e| e)?;
    if svg.paths.is_empty() {
        return Err("vtracer produced no paths".into());
    }
    // ALL path layers, preserving the Cutout hierarchy: layer = (outer, holes);
    // coordinates divided back to source-pixel space
    let inv = 1.0 / SS as f64;
    let mut layers = Vec::new();
    for sp in &svg.paths {
        let cc = compound_contours(&sp.path);
        if cc.is_empty() {
            continue;
        }
        let scale_c = |c: &Vec<[f64; 2]>| -> Vec<[f64; 2]> {
            c.iter().map(|p| [p[0] * inv, p[1] * inv]).collect()
        };
        layers.push((
            scale_c(&cc[0]),
            cc[1..].iter().map(|h| scale_c(h)).collect::<Vec<_>>(),
        ));    }
    if layers.is_empty() {
        return Err("vtracer produced no contours".into());
    }
    let flat: Vec<Vec<[f64; 2]>> = layers
        .iter()
        .flat_map(|(o, hs)| std::iter::once(o).chain(hs.iter()))
        .cloned()
        .collect();
    let (trace_max, trace_p95) = boundary_error(&flat, unit);

    let polylines: Vec<Vec<[f64; 2]>> = layers
        .iter()
        .flat_map(|(o, hs)| std::iter::once(o).chain(hs.iter()))
        .map(|c| sample_spline(c, 6))
        .collect();

    Ok(TracedShape {
        shape_key: unit.shape_key.clone(),
        crop_w_px: unit.crop_w,
        crop_h_px: unit.crop_h,
        polylines,
        layers,
        stage: StageRaw {
            trace_max_px: trace_max,
            trace_p95_px: trace_p95,
        },
    })
}
