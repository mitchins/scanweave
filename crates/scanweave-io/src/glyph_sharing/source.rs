//! Frozen source normalization, physical line frame and native canonical traces.
use super::{edt, quantile, sample, Field, SIDE};
use crate::{document::DocumentPage, glyphs::GlyphShape, units::Unit};
use std::collections::BTreeMap;
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct Frame {
    pub xheight: f64,
    pub baseline: f64,
    pub cx: f64,
    pub scale: f64,
}
#[derive(Debug)]
pub struct Observation {
    pub page: usize,
    pub occurrence: usize,
    pub id: String,
    pub label: String,
    pub shape_key: String,
    pub field: Field,
    pub frame: Option<Frame>,
    pub source: Option<Unit>,
    pub source_error: Option<String>,
    pub canonical: Option<Canonical>,
}
#[derive(Debug)]
pub struct Canonical {
    pub shape: GlyphShape,
    pub coverage: Field,
    pub origin: [usize; 2],
    pub width: usize,
    pub height: usize,
}

pub fn local_source(unit: &Unit, paper: [u8; 3]) -> Result<Field, String> {
    let w = unit.crop_w + 4;
    let h = unit.crop_h + 4;
    let halo = unit.gray_halo.as_ref().ok_or("no grayscale halo")?;
    if halo.len() != w * h || unit.mask.len() != unit.crop_w * unit.crop_h {
        return Err("invalid owned source dimensions".into());
    }
    let mut owned = vec![false; w * h];
    for y in 0..unit.crop_h {
        for x in 0..unit.crop_w {
            owned[(y + 2) * w + x + 2] = unit.mask[y * unit.crop_w + x];
        }
    }
    let off: Vec<f64> = halo
        .iter()
        .zip(&owned)
        .filter(|(_, m)| !**m)
        .map(|(&v, _)| v as f64)
        .collect();
    let on: Vec<f64> = halo
        .iter()
        .zip(&owned)
        .filter(|(_, m)| **m)
        .map(|(&v, _)| v as f64)
        .collect();
    if off.is_empty() || on.is_empty() {
        return Err("empty owned source".into());
    }
    let paper_level = quantile(&off, 0.8);
    let ink = quantile(&on, 0.15);
    if paper_level - ink < 30. {
        return Err("insufficient_contrast".into());
    }
    let dist = edt(&owned.iter().map(|v| !v).collect::<Vec<_>>(), w, h);
    let color = paper[0] as f64 * 0.2126 + paper[1] as f64 * 0.7152 + paper[2] as f64 * 0.0722;
    let foreign: Vec<bool> = halo
        .iter()
        .zip(&owned)
        .map(|(&v, &m)| (v as f64 - color).abs() > 60. && !m)
        .collect();
    let fd = if foreign.iter().any(|&v| v) {
        edt(&foreign.iter().map(|v| !v).collect::<Vec<_>>(), w, h)
    } else {
        vec![100.; w * h]
    };
    Ok((0..w * h)
        .map(|i| {
            if dist[i] <= 1.5 && dist[i] < fd[i] {
                ((paper_level - halo[i] as f64) / (paper_level - ink)).clamp(0., 1.)
            } else {
                0.
            }
        })
        .collect())
}

pub fn frame(
    unit: &Unit,
    paper: [u8; 3],
    line: &[(&str, [f64; 4])],
) -> Result<(Field, Frame), String> {
    let field = local_source(unit, paper)?;
    let bbox = unit.bbox_px;
    let center = (bbox[1] + bbox[3]) / 2.;
    let height = bbox[3] - bbox[1];
    let mut lines: Vec<[f64; 4]> = line
        .iter()
        .filter(|(text, b)| {
            "ace".contains(*text)
                && b[3] - b[1] >= 4.
                && ((b[1] + b[3]) / 2. - center).abs() <= 0.65 * height.max(b[3] - b[1])
        })
        .map(|(_, b)| *b)
        .collect();
    if lines.is_empty() {
        lines.push(bbox);
    }
    let xh = quantile(&lines.iter().map(|b| b[3] - b[1]).collect::<Vec<_>>(), 0.5);
    let baseline = quantile(&lines.iter().map(|b| b[3]).collect::<Vec<_>>(), 0.5);
    if xh <= 0. {
        return Err("invalid source xheight".into());
    }
    let cx = (unit.ocr_bbox_px[0] + unit.ocr_bbox_px[2]) / 2.;
    let scale = 32. / xh;
    let canvas = (0..SIDE * SIDE)
        .map(|i| {
            sample(
                &field,
                unit.crop_w + 4,
                unit.crop_h + 4,
                cx + ((i % SIDE) as f64 - 32.) / scale - bbox[0] + 1.5,
                baseline + ((i / SIDE) as f64 - 48.) / scale - bbox[1] + 1.5,
            )
        })
        .collect();
    Ok((
        canvas,
        Frame {
            xheight: xh,
            baseline,
            cx,
            scale,
        },
    ))
}

pub fn trace(index: usize, label: &str, field: &[f64]) -> Result<Canonical, String> {
    let ink: Vec<usize> = (0..field.len()).filter(|&i| field[i] > 0.5).collect();
    if ink.is_empty() {
        return Err("empty_coverage".into());
    }
    let x = *ink
        .iter()
        .map(|i| i % SIDE)
        .collect::<Vec<_>>()
        .iter()
        .min()
        .unwrap();
    let y = ink.iter().map(|i| i / SIDE).min().unwrap();
    let w = ink.iter().map(|i| i % SIDE).max().unwrap() + 1 - x;
    let h = ink.iter().map(|i| i / SIDE).max().unwrap() + 1 - y;
    let cov: Vec<f64> = (0..w * h)
        .map(|i| field[(y + i / w) * SIDE + x + i % w])
        .collect();
    let key = format!("font04-e-{index}");
    let unit = Unit {
        shape_key: key.clone(),
        span_id: key.clone(),
        symbol_id: key,
        semantic_text: label.into(),
        bbox_px: [0., 0., w as f64, h as f64],
        ocr_bbox_px: [0., 0., w as f64, h as f64],
        crop_w: w,
        crop_h: h,
        mask: cov.iter().map(|&v| v > 0.5).collect(),
        gray_samples: Some(
            cov.iter()
                .map(|&v| ((1. - v) * 255.).round() as u8)
                .collect(),
        ),
        gray_halo: None,
    };
    let budget = crate::trace::Budget::from_m0_policy();
    let mut traced = crate::trace::trace_shape_clearscan_with_options(
        &unit,
        &budget,
        16.,
        None,
        Some(&cov),
        16_384,
    )?;
    traced.preserve_crop_frame = true;
    let mut shapes = crate::glyphs::build_glyph_shapes(&[traced], 16., &budget)?;
    let shape = shapes.remove(0);
    let coverage = crate::convert::reconstructed_glyph_coverage(&shape, w, h);
    let mut canvas = vec![0.; SIDE * SIDE];
    for yy in 0..h {
        canvas[(y + yy) * SIDE + x..(y + yy) * SIDE + x + w]
            .copy_from_slice(&coverage[yy * w..(yy + 1) * w]);
    }
    Ok(Canonical {
        shape,
        coverage: canvas,
        origin: [x, y],
        width: w,
        height: h,
    })
}

pub fn snapshot(pages: &[DocumentPage], donors: &[Vec<Unit>]) -> Vec<Observation> {
    let mut counts = BTreeMap::<&str, usize>::new();
    for page in pages {
        for o in &page.parts.occurrences {
            *counts.entry(&o.5).or_default() += 1;
        }
    }
    let mut result = Vec::new();
    for (pi, page) in pages.iter().enumerate() {
        let p = &page.parts;
        for (oi, o) in p.occurrences.iter().enumerate() {
            if counts[o.5.as_str()] < 10 {
                continue;
            }
            let source = donors[pi]
                .iter()
                .find(|u| u.symbol_id == o.4 && u.semantic_text == o.5)
                .cloned()
                .map(|mut u| {
                    u.retain_grayscale(&p.source_rgb, p.source_w as u32, p.source_h as u32);
                    u
                });
            let line = p.lines.iter().find(|line| line.spans.contains(&o.3));
            let line_units: Vec<(&str, [f64; 4])> = donors[pi]
                .iter()
                .filter(|u| line.is_some_and(|l| l.spans.contains(&u.span_id)))
                .map(|u| (u.semantic_text.as_str(), u.bbox_px))
                .collect();
            let prepared = source
                .as_ref()
                .ok_or_else(|| "no_safe_owned_witness".into())
                .and_then(|u| frame(u, p.paper, &line_units));
            let (field, frame, source_error) = match prepared {
                Ok((f, m)) => (f, Some(m), None),
                Err(e) => (vec![0.; 4096], None, Some(e)),
            };
            let canonical = if frame.is_some() {
                trace(result.len(), &o.5, &field).ok()
            } else {
                None
            };
            result.push(Observation {
                page: pi,
                occurrence: oi,
                id: o.4.clone(),
                label: o.5.clone(),
                shape_key: p.shapes[o.0].shape_key.clone(),
                field,
                frame,
                source,
                source_error,
                canonical,
            });
        }
    }
    result
}

pub fn fitted_bbox(frame: &Frame, canonical: &Canonical, p: [f64; 3]) -> [f64; 4] {
    let [x, y] = canonical.origin;
    let left = 32. + p[2] * (x as f64 - 0.5 - 32.) + p[0];
    let top = 48. + p[2] * (y as f64 - 0.5 - 48.) + p[1];
    [
        frame.cx + (left - 32.) / frame.scale,
        frame.baseline + (top - 48.) / frame.scale,
        frame.cx + (left + p[2] * canonical.width as f64 - 32.) / frame.scale,
        frame.baseline + (top + p[2] * canonical.height as f64 - 48.) / frame.scale,
    ]
}
