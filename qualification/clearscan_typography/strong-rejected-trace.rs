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

#[derive(Clone)]
pub struct TracedShape {
    pub shape_key: String,
    /// crop dims in px: the ink touches all four crop edges by construction,
    /// so in font units the ink spans exactly [0, cw*k] x [0, ch*k]
    pub crop_w_px: usize,
    pub crop_h_px: usize,
    pub preserve_crop_frame: bool,
    pub contour_fit: Option<ContourFit>,
    /// dense sampled polylines per contour (crop-local, source-pixel space),
    /// outer contours and holes in paint order
    pub polylines: Vec<Vec<[f64; 2]>>,
    /// per-layer contours in traced image coordinates (y down):
    /// each layer = (outer, holes...) from vtracer Cutout hierarchy
    pub layers: Vec<crate::glyphs::ContourLayer>,
    pub stage: StageRaw,
}

#[derive(Clone, Debug, serde::Serialize)]
pub struct ContourFit {
    pub method: String,
    pub corner_degrees: i32,
    pub segment_length: f64,
    pub inset_px: f64,
    pub paper_luma: f64,
    pub ink_luma: f64,
    pub baseline_gray_mse: f64,
    pub selected_gray_mse: f64,
    pub baseline_control_points: usize,
    pub selected_control_points: usize,
}

#[derive(Clone)]
pub struct StageRaw {
    pub trace_max_px: f64,
    pub trace_p95_px: f64,
}

/// supersampling factor for tracing (0.5px corner resolution in source space)
pub const SS: usize = 2;

fn vtracer_config() -> vtracer::Config {
    vtracer::Config {
        color_mode: vtracer::ColorMode::Binary,
        hierarchical: vtracer::Hierarchical::Cutout,
        mode: visioncortex::PathSimplifyMode::Spline,
        filter_speckle: 0, // never drop small marks (VS-05 discipline)
        corner_threshold: 0, // no corner smoothing (measured: reduces deviation)
        // minimal reduction (0 disables reduction upstream — measured identical to 4.0)
        length_threshold: 1.0,
        max_iterations: 10,
        splice_threshold: 45,
        ..Default::default()
    }
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
    trace_shape_config(unit, vtracer_config())
}

fn trace_shape_config(unit: &Unit, config: vtracer::Config) -> Result<TracedShape, String> {
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

    let svg = vtracer::convert(img, config)?;
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
            cc[1..].iter().map(scale_c).collect::<Vec<_>>(),
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
        preserve_crop_frame: false,
        contour_fit: None,
        polylines,
        layers,
        stage: StageRaw {
            trace_max_px: trace_max,
            trace_p95_px: trace_p95,
        },
    })
}

/// Choose bounded smooth curves against the original grayscale impression.
/// The binary mask supplies topology and ownership, not the sole fitting target.
/// Faithful never calls this function. Candidate selection has no source-font
/// or OCR-shape dependency and preserves the canonical identity and crop frame.
pub(crate) fn trace_shape_clearscan(unit: &Unit, budget: &Budget, k: f64) -> Result<TracedShape, String> {
    let baseline = trace_shape(unit, budget, k)?;
    let Some(gray) = unit.gray_samples.as_deref().filter(|g| g.len() == unit.mask.len() && !g.is_empty() && g.len() <= 16_384) else { return Ok(baseline); };
    let mut levels = gray.to_vec(); levels.sort_unstable();
    let paper = levels[levels.len() * 9 / 10] as f64;
    let ink = levels[levels.len() / 20] as f64;
    if paper - ink < 48.0 { return Ok(baseline); }
    let target: Vec<f64> = gray.iter().map(|&v| ((paper-v as f64)/(paper-ink)).clamp(0.0,1.0)).collect();
    let score = |t: &TracedShape| -> Option<f64> {
        let shape = crate::glyphs::build_glyph_shapes(std::slice::from_ref(t), k, budget).ok()?.pop()?;
        // This is the existing trace gate, applied before selecting a candidate
        // so improved coverage fit cannot unexpectedly discard an occurrence.
        if crate::convert::reconstructed_glyph_ink_iou(&shape, unit.crop_w, unit.crop_h, &unit.mask) < 0.90 { return None; }
        let coverage = crate::convert::reconstructed_glyph_coverage(&shape, unit.crop_w, unit.crop_h);
        Some(coverage.iter().zip(&target).map(|(c,t)| (c-t).powi(2)).sum::<f64>() / target.len() as f64)
    };
    let Some(mut best_score) = score(&baseline) else { return Ok(baseline); };
    let baseline_score = best_score;
    let baseline_points = baseline.layers.iter().map(|(o,h)|o.len()+h.iter().map(Vec::len).sum::<usize>()).sum();
    let mut choice = ("observed_corners",0,1.0,0.0);
    let mut best = baseline.clone();
    let topology = best.layers.iter().map(|(_,holes)| holes.len()).sum::<usize>();
    let components = best.layers.len();
    let mut candidates = vec![(baseline.clone(),"observed_corners",0,1.0)];
    candidates.push((fair_coverage_contour(&baseline), "bounded_edge_fairing",0,1.0));
    for (corner, length) in [(60, 2.0), (90, 3.0), (120, 4.0)] {
        let mut config = vtracer_config(); config.corner_threshold = corner; config.length_threshold = length;
        let Ok(candidate) = trace_shape_config(unit, config) else { continue; };
        if candidate.layers.len() == components && candidate.layers.iter().map(|(_,h)|h.len()).sum::<usize>() == topology { candidates.push((candidate,"spline_smoothing",corner,length)); }
    }
    for (candidate,method,corner,length) in candidates {
        if let Some(loss) = score(&candidate) { if loss < best_score * 0.98 { best_score = loss; best = candidate.clone(); choice=(method,corner,length,0.0); } }
        for inset in [-0.15, -0.075, 0.075, 0.15] {
            let adjusted = offset_coverage_contour(&candidate, inset);
            if let Some(loss) = score(&adjusted) { if loss < best_score * 0.98 { best_score = loss; best = adjusted; choice=(method,corner,length,inset); } }
        }
    }
    let flat: Vec<_> = best.layers.iter().flat_map(|(o,h)|std::iter::once(o).chain(h)).cloned().collect();
    let (max,p95)=boundary_error(&flat, unit);best.stage=StageRaw{trace_max_px:max,trace_p95_px:p95};
    best.contour_fit = Some(ContourFit {
        method: choice.0.into(), corner_degrees:choice.1, segment_length:choice.2, inset_px:choice.3,
        paper_luma:paper,ink_luma:ink,baseline_gray_mse:baseline_score,selected_gray_mse:best_score,
        baseline_control_points:baseline_points,
        selected_control_points:best.layers.iter().map(|(o,h)|o.len()+h.iter().map(Vec::len).sum::<usize>()).sum(),
    });
    Ok(best)
}

/// A bounded normal displacement of existing cubic contours. The original
/// source crop is the fixed construction frame, so stroke fitting never
/// rescales an inset outline back into the observed ink box.
fn offset_coverage_contour(source: &TracedShape, inset: f64) -> TracedShape {
    let mut out=source.clone();
    let mut min_x=f64::INFINITY;let mut max_y=f64::NEG_INFINITY;
    if !source.preserve_crop_frame {
        for c in source.layers.iter().flat_map(|(o,h)|std::iter::once(o).chain(h)) {
            for (i,p) in c.iter().enumerate() {if i%3==0 {min_x=min_x.min(p[0]);max_y=max_y.max(p[1]);}}
        }
    } else {min_x=0.0;max_y=source.crop_h_px as f64;}
    for (outer, holes) in &mut out.layers {
        for (is_hole, c) in std::iter::once((false,outer)).chain(holes.iter_mut().map(|h|(true,h))) {
            for p in c.iter_mut() {p[0]-=min_x;p[1]+=source.crop_h_px as f64-max_y;}
            let before=c.clone();let n=(c.len()-1)/3;
            let signed: f64=sample_spline(&before,4).windows(2).map(|w|w[0][0]*w[1][1]-w[1][0]*w[0][1]).sum();
            let sign=if signed>=0.0 {1.0} else {-1.0} * if is_hole {-1.0} else {1.0};
            let normals:Vec<[f64;2]>=(0..n).map(|i| {
                let prev=before[if i==0 {3*n-1} else {3*i-1}];let next=before[3*i+1];let dx=next[0]-prev[0];let dy=next[1]-prev[1];let len=dx.hypot(dy).max(1e-9);[sign*dy/len,-sign*dx/len]
            }).collect();
            for i in 0..n {for (j,normal) in [(3*i,normals[i]),(3*i+1,normals[i]),(3*i+2,normals[(i+1)%n])] {c[j][0]-=inset*normal[0];c[j][1]-=inset*normal[1];}}
            c[3*n]=c[0];
        }
    }
    out.preserve_crop_frame=true;
    out.polylines=out.layers.iter().flat_map(|(o,h)|std::iter::once(o).chain(h)).map(|c|sample_spline(c,6)).collect();out
}

/// Remove subpixel staircase turns while retaining corners supported across
/// a 1.5px neighborhood. The displacement is capped at 0.6 source pixels;
/// coverage fitting decides whether this fairer geometry is actually useful.
fn fair_coverage_contour(source: &TracedShape) -> TracedShape {
    let mut out=offset_coverage_contour(source,0.0);
    for c in out.layers.iter_mut().flat_map(|(o,h)|std::iter::once(o).chain(h)) {
        let raw=sample_spline(c,6);let mut poly=Vec::new();
        for p in raw {if poly.last().is_none_or(|q:&[f64;2]|(p[0]-q[0]).hypot(p[1]-q[1])>1e-8) {poly.push(p);}}
        if poly.len()<4 {continue;}
        if (poly[0][0]-poly.last().unwrap()[0]).hypot(poly[0][1]-poly.last().unwrap()[1])<1e-8 {poly.pop();}
        let mut lengths=vec![0.0];let n=poly.len();
        for i in 0..n {lengths.push(lengths[i]+(poly[(i+1)%n][0]-poly[i][0]).hypot(poly[(i+1)%n][1]-poly[i][1]));}
        let total=lengths[n];let count=(total/0.5).ceil().max(8.0) as usize;let mut p=Vec::new();let mut e=0;
        for i in 0..count {let d=total*i as f64/count as f64;while e+1<n&&lengths[e+1]<d {e+=1;}let t=(d-lengths[e])/(lengths[e+1]-lengths[e]).max(1e-9);p.push([poly[e][0]+t*(poly[(e+1)%n][0]-poly[e][0]),poly[e][1]+t*(poly[(e+1)%n][1]-poly[e][1])]);}
        let corners:Vec<bool>=(0..count).map(|i| {
            let a=p[(i+count-3)%count];let b=p[i];let d=p[(i+3)%count];let u=[b[0]-a[0],b[1]-a[1]];let v=[d[0]-b[0],d[1]-b[1]];
            (u[0]*v[0]+u[1]*v[1])/(u[0].hypot(u[1])*v[0].hypot(v[1])).max(1e-9)<0.5
        }).collect();
        let original=p.clone();
        for _ in 0..8 {
            let prev=p.clone();
            for i in 0..count {if corners[i] {continue;}let a=prev[(i+count-1)%count];let b=prev[(i+1)%count];let q=[0.5*prev[i][0]+0.25*(a[0]+b[0]),0.5*prev[i][1]+0.25*(a[1]+b[1])];let dx=q[0]-original[i][0];let dy=q[1]-original[i][1];let f=(0.6/dx.hypot(dy).max(1e-9)).min(1.0);p[i]=[original[i][0]+f*dx,original[i][1]+f*dy];}
        }
        *c=vec![p[0]];
        for i in 0..count {let j=(i+1)%count;let prev=p[(i+count-1)%count];let next=p[(i+2)%count];let a=p[i];let b=p[j];
            c.push(if corners[i] {[a[0]+(b[0]-a[0])/3.0,a[1]+(b[1]-a[1])/3.0]} else {[a[0]+(b[0]-prev[0])/6.0,a[1]+(b[1]-prev[1])/6.0]});
            c.push(if corners[j] {[b[0]-(b[0]-a[0])/3.0,b[1]-(b[1]-a[1])/3.0]} else {[b[0]-(next[0]-a[0])/6.0,b[1]-(next[1]-a[1])/6.0]});c.push(b);
        }
        let mut path=kurbo::BezPath::new();path.move_to((c[0][0],c[0][1]));
        for i in (0..c.len()-1).step_by(3) {path.curve_to((c[i+1][0],c[i+1][1]),(c[i+2][0],c[i+2][1]),(c[i+3][0],c[i+3][1]));}path.close_path();
        let simplified=kurbo::simplify::simplify_bezpath(path.iter(),0.12,&Default::default());
        let mut fitted=Vec::new();
        for el in simplified.iter() {match el {
            kurbo::PathEl::MoveTo(p)=>fitted.push([p.x,p.y]),
            kurbo::PathEl::CurveTo(a,b,p)=>{fitted.push([a.x,a.y]);fitted.push([b.x,b.y]);fitted.push([p.x,p.y]);},
            kurbo::PathEl::LineTo(p)=>{if let Some(a)=fitted.last().copied() {fitted.push([a[0]+(p.x-a[0])/3.0,a[1]+(p.y-a[1])/3.0]);fitted.push([a[0]+2.0*(p.x-a[0])/3.0,a[1]+2.0*(p.y-a[1])/3.0]);fitted.push([p.x,p.y]);}},
            _=>{},
        }}
        if fitted.len()>=4 && (fitted.len()-1)%3==0 {*c=fitted;}
    }
    out
}
