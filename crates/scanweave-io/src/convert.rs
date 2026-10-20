//! One-page conversion (M1-A).
//!
//! Pipeline: segmentation → explicit ownership plan (many-to-many) → region
//! planning (non-text contact → raster) → tracing + vector candidates →
//! assembly with raster patches + invisible owners → report.

use crate::encoding::{allocate_cids, EncodingKey, MetricsKey, WritingMode};
use crate::fontbuild::build_font;
use crate::glyphs::{build_glyph_shapes, GlyphShape};
use crate::mask::{segment, Segmentation};
use crate::ownership::{build_plan, OwnershipPlan};
use crate::page_pdf::{ImageEncodingOptions, Owner, Patch};
use crate::plan::{plan_regions, FallbackReason, RegionDisposition, RegionKind};
use crate::trace::{trace_shape, Budget, TracedShape};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize)]
pub struct Policy {
    pub preset: String,
    pub mode: String,
    pub dpi: f64,
    pub upem: u16,
    pub min_ink_iou: f64,
    pub contact_margin_px: f64,
    /// Product profile: `faithful` (default) or `clearscan`.
    pub profile: String,
    /// Visual glyph dictionary mode: `off` (default) or `visual`.
    pub glyph_dictionary: String,
    /// Lossless PDF image serialization controls; default is exact reuse plus
    /// grayscale storage for channel-equal source samples.
    pub image_encoding: ImageEncodingOptions,
}

impl Default for Policy {
    fn default() -> Policy {
        Policy {
            preset: "faithful".into(),
            mode: "reconstruct".into(),
            dpi: 300.0,
            upem: 2048,
            min_ink_iou: 0.98,
            contact_margin_px: 4.0,
            profile: "faithful".into(),
            glyph_dictionary: "off".into(),
            image_encoding: ImageEncodingOptions::default(),
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct RegionRecord {
    pub id: usize,
    pub kind: RegionKind,
    pub units: usize,
    pub bbox_px: [f64; 4],
    pub disposition: RegionDisposition,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct Coverage {
    pub text_ink_px_total: u64,
    pub text_ink_px_vector: u64,
    pub text_ink_px_raster: u64,
    pub other_ink_px: u64,
    pub unowned_ink_px: u64,
    pub multiply_owned_ink_px: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct OccurrenceRecord {
    pub page_id: String,
    pub span_id: String,
    pub symbol_id: String,
    pub semantic_text: String,
    pub owner: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct PatchRecord {
    pub compact_background: bool,
    pub bbox_px: [f64; 4],
    pub w: u32,
    pub h: u32,
    /// sha256 of the embedded RGB bytes (fidelity audits compare this against
    /// the source crop so a paper-only patch cannot masquerade as a restore)
    pub rgb_sha256: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct GlyphStat {
    pub gid: usize,
    pub stages: crate::units::StageMetrics,
    pub symbol_id: String,
    pub contours: usize,
    pub points: usize,
    pub budget_ok: bool,
}

/// Analytical fidelity accounting for a page (SPEC §5.6: min_ink_iou is a
/// policy threshold the conversion must enforce, not a report decoration).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct Fidelity {
    /// per-unit analytical ink IoU of the vectorized glyphs (outline vs the
    /// source ink mask, both on the unit's crop grid)
    pub vector_ink_iou_min: Option<f64>,
    pub vector_ink_iou_mean: Option<f64>,
    /// Source-mask threshold applied to unchanged vector occurrences. Repaired
    /// ClearScan occurrences have their own donor evidence decision.
    pub preservation_ink_iou_min: Option<f64>,
    /// raster ink is byte-exact from the source by construction (IoU 1.0)
    pub raster_ink_px: u64,
    /// units degraded to raster because their trace fell below min_ink_iou
    pub units_below_policy: usize,
    /// the policy threshold this page was checked against
    pub min_ink_iou: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct Report {
    pub segmentation_method: String,
    pub stage_timings_ms: BTreeMap<String, u128>,
    pub fidelity: Fidelity,
    pub reconstruction: crate::visual_dict::Reconstruction,
    pub glyph_stats: Vec<GlyphStat>,
    /// candidates actually serialized and measured (name, pdf bytes); auto mode
    /// selects the smallest that passes the semantic requirements
    pub candidates: Vec<(String, usize)>,
    /// which candidate the reported pdf_bytes is ("reconstruct" | "raster_baseline")
    pub selected: String,
    pub patches: Vec<PatchRecord>,
    pub occurrences: Vec<OccurrenceRecord>,
    pub page_id: String,
    pub policy: Policy,
    pub supplied_chars: usize,
    pub components_total: usize,
    pub components_owned: usize,
    pub components_artwork: usize,
    pub visual_units: usize,
    pub semantic_spans: usize,
    pub regions: Vec<RegionRecord>,
    pub coverage: Coverage,
    /// Source pixels removed because an emitted vector occurrence owns them.
    pub raster_ink_pixels_suppressed: usize,
    /// Bright antialias/fringe and donor-supported dropout samples removed.
    pub antialias_fringe_pixels_suppressed: usize,
    pub fallback_reasons: BTreeMap<String, usize>,
    pub font_glyphs: usize,
    pub font_bytes: usize,
    pub pdf_bytes: usize,
    pub raster_bytes: usize,
    pub semantic_owner: BTreeMap<String, String>,
    pub ownership_invariants: BTreeMap<String, bool>,
    pub elapsed_ms: u128,
}

fn clearscan_source_dpi(raster_to_page_pt: [f64; 6], page_id: &str) -> Result<f64, String> {
    let sx = raster_to_page_pt[0];
    let sy = raster_to_page_pt[3];
    if !sx.is_finite() || !sy.is_finite() || sx <= 0.0 || sy >= 0.0 {
        return Err(format!(
            "page {page_id} has invalid scale for ClearScan DPI inference"
        ));
    }
    let dpi_x = 72.0 / sx;
    let dpi_y = 72.0 / -sy;
    if !dpi_x.is_finite() || !dpi_y.is_finite() || dpi_x <= 0.0 || dpi_y <= 0.0 {
        return Err(format!(
            "page {page_id} has non-finite ClearScan DPI inferred from its affine"
        ));
    }
    // Use the lower axis when scans are anisotropic, keeping the image
    // reduction bounded by the least-sampled direction.
    Ok(dpi_x.min(dpi_y))
}

/// A caller/preset/source protection polygon: the pixels inside must survive
/// exactly (SPEC §4.4), so units touching it cannot be vectorized.
#[derive(Debug, Clone)]
pub struct ProtectedInput {
    pub id: String,
    pub polygon: Vec<[f64; 2]>,
    pub reason: String,
}

#[derive(Debug, Clone)]
pub struct SymbolInput {
    pub id: String,
    pub range: (usize, usize),
    pub polygon: Vec<[f64; 2]>,
}

#[derive(Debug, Clone)]
pub struct SpanInput {
    pub id: String,
    pub text: String,
    /// OCR-authoritative whitespace after this span (e.g. " " or "\n")
    pub separator_after: String,
    pub polygon: Vec<[f64; 2]>,
    pub symbols: Vec<SymbolInput>,
}

#[derive(Debug, Clone)]
pub struct Input {
    pub rgb: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub page_id: String,
    pub spans: Vec<SpanInput>,
    /// caller-provided protection polygons (SPEC §4.4); their pixels are never
    /// vectorized — the regions they touch fall back to raster
    pub protected_regions: Vec<ProtectedInput>,
    /// authoritative raster→page-points affine [a b c d e f] from the normalized
    /// OCR page (a 600 dpi scan must not be laid out at the bundle's 300 dpi
    /// default); axis-aligned only (b == c == 0)
    pub raster_to_page_pt: [f64; 6],
    /// the canonical pixel hash the OCR page declares for this raster; the
    /// conversion verifies it before working on the pixels (SPEC §4.2)
    pub pixel_sha256: Option<String>,
}

pub struct Output {
    pub pdf_bytes: Vec<u8>,
    pub b0_bytes: Vec<u8>,
    pub report: Report,
    pub font_bytes: Vec<u8>,
}

/// Build a page [`Input`] from a canonical raster and its normalized OCR page.
/// (Shared by the single-page CLI and the document/bundle path.)
pub fn input_from_ocr_page(
    rgb: &[u8],
    width: u32,
    height: u32,
    page_id: &str,
    page: &scanweave_core::ocr_page::OcrPage,
) -> Input {
    let spans = page
        .spans
        .iter()
        .map(|s| SpanInput {
            id: s.id.clone(),
            text: s.text.clone(),
            separator_after: s.separator_after.clone(),
            polygon: s.polygon.clone(),
            symbols: s
                .symbols
                .iter()
                .map(|sym| SymbolInput {
                    id: sym.id.clone(),
                    range: (sym.text_range_utf8[0], sym.text_range_utf8[1]),
                    polygon: sym.polygon.clone(),
                })
                .collect(),
        })
        .collect();
    Input {
        rgb: rgb.to_vec(),
        width,
        height,
        page_id: page_id.to_string(),
        spans,
        protected_regions: page
            .protected_regions
            .iter()
            .map(|p| ProtectedInput {
                id: p.id.clone(),
                polygon: p.polygon.clone(),
                reason: p.reason.clone(),
            })
            .collect(),
        raster_to_page_pt: page.page.raster_to_page_pt,
        pixel_sha256: Some(page.raster.pixel_sha256.clone()),
    }
}

fn to_ocr_page(input: &Input) -> scanweave_core::ocr_page::OcrPage {
    use scanweave_core::ocr_page::*;
    let pt = |px: f64| px * 72.0 / 300.0;
    OcrPage {
        schema_version: SchemaVersion::V1,
        page_id: input.page_id.clone(),
        raster: RasterBinding {
            asset_path: "input.png".into(),
            file_sha256: scanweave_core::hash_hex(&input.rgb),
            pixel_sha256: scanweave_core::hash_hex(&input.rgb),
            width_px: input.width,
            height_px: input.height,
            canonical_format: scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
            colour_tag: scanweave_core::pixel_hash::ColourTag::Srgb,
            icc_sha256: None,
            orientation_policy: OrientationPolicy::AppliedOnce,
            decoder_id: "m1a".into(),
            dpi_x: Some(300.0),
            dpi_y: Some(300.0),
        },
        page: PageGeometry {
            width_pt: pt(input.width as f64),
            height_pt: pt(input.height as f64),
            raster_to_page_pt: [
                72.0 / 300.0,
                0.0,
                0.0,
                -72.0 / 300.0,
                0.0,
                pt(input.height as f64),
            ],
        },
        source_geometry: None,
        producer: Producer {
            name: "m1a".into(),
            version: "1".into(),
            models: vec![],
            languages: vec![],
        },
        granularity: Granularity::Symbol,
        reading_order_status: ReadingOrderStatus::Supplied,
        reading_order: input.spans.iter().map(|s| s.id.clone()).collect(),
        protected_regions: input
            .protected_regions
            .iter()
            .map(|p| ProtectedRegion {
                id: p.id.clone(),
                polygon: p.polygon.clone(),
                reason: p.reason.clone(),
                origin: ProtectedOrigin::Caller,
            })
            .collect(),
        spans: input
            .spans
            .iter()
            .map(|s| Span {
                id: s.id.clone(),
                text: s.text.clone(),
                separator_after: s.separator_after.clone(),
                polygon: s.polygon.clone(),
                direction: Direction::Ltr,
                role: Role::Body,
                language: None,
                confidence: Confidence {
                    value: None,
                    scale: ConfidenceScale::Unknown,
                    calibrated: false,
                },
                provenance: Provenance::Ocr,
                baseline: None,
                parent_span_id: None,
                symbols: s
                    .symbols
                    .iter()
                    .map(|sym| Symbol {
                        id: sym.id.clone(),
                        text_range_utf8: [sym.range.0, sym.range.1],
                        polygon: sym.polygon.clone(),
                        confidence: Confidence {
                            value: None,
                            scale: ConfidenceScale::Unknown,
                            calibrated: false,
                        },
                    })
                    .collect(),
            })
            .collect(),
    }
}

/// Extract document-local donor observations without running tracing or
/// altering the page. Protected, suspect, and non-single-symbol units are
/// excluded; the caller supplies these only to sibling-page reconstruction.
pub(crate) fn collect_document_donors(input: &Input) -> Vec<crate::units::Unit> {
    let seg = segment(&input.rgb, input.width, input.height);
    let ocr = to_ocr_page(input);
    let (plan, _) = build_plan(&seg, input.width, input.height, &ocr);
    let protected_boxes: Vec<[f64; 4]> = input
        .protected_regions
        .iter()
        .map(|p| {
            let mut bb = span_bbox(&p.polygon);
            bb[0] = bb[0].clamp(0.0, input.width as f64);
            bb[1] = bb[1].clamp(0.0, input.height as f64);
            bb[2] = bb[2].clamp(0.0, input.width as f64);
            bb[3] = bb[3].clamp(0.0, input.height as f64);
            bb
        })
        .collect();
    let regions = plan_regions(&plan, &protected_boxes);
    let mut eligible = std::collections::BTreeSet::new();
    for region in regions {
        if !matches!(region.disposition, RegionDisposition::Vector) {
            continue;
        }
        eligible.extend(region.units);
    }
    plan.owned
        .into_iter()
        .enumerate()
        .filter_map(|(i, owned)| {
            (eligible.contains(&i)
                && !owned.suspect
                && owned.unit.semantic_text.chars().count() == 1)
                .then_some(owned.unit)
        })
        .collect()
}

/// Analytical ink IoU between a traced glyph outline and the unit's source ink
/// mask: the outline is rasterized over the crop grid (scanline fill at pixel
/// centres) and compared with the mask. Empty/empty = 1, empty/nonempty = 0.
pub(crate) fn glyph_ink_iou(g: &GlyphShape, crop_w: usize, crop_h: usize, mask: &[bool]) -> f64 {
    glyph_ink_iou_contract(g, crop_w, crop_h, mask, false)
}

pub(crate) fn reconstructed_glyph_ink_iou(
    g: &GlyphShape,
    crop_w: usize,
    crop_h: usize,
    mask: &[bool],
) -> f64 {
    glyph_ink_iou_contract(g, crop_w, crop_h, mask, true)
}

fn glyph_ink_iou_contract(
    g: &GlyphShape,
    crop_w: usize,
    crop_h: usize,
    mask: &[bool],
    clearscan: bool,
) -> f64 {
    if crop_w == 0 || crop_h == 0 {
        return 1.0;
    }
    let cover = glyph_coverage_contract(g, crop_w, crop_h, clearscan, 4);
    const SUB: usize = 4;
    // Foreground at at least half a pixel of covered area.
    let fill: Vec<bool> = cover
        .iter()
        .map(|c| {
            *c >= if clearscan {
                0.5
            } else {
                SUB.div_ceil(2) as f64
            }
        })
        .collect();
    let mut inter = 0usize;
    let mut uni = 0usize;
    for (i, m) in mask.iter().enumerate() {
        if i >= fill.len() {
            break;
        }
        if *m || fill[i] {
            uni += 1;
            if *m && fill[i] {
                inter += 1;
            }
        }
    }
    if uni == 0 {
        1.0
    } else {
        inter as f64 / uni as f64
    }
}

pub(crate) fn reconstructed_glyph_coverage(g: &GlyphShape, w: usize, h: usize) -> Vec<f64> {
    glyph_coverage_contract(g, w, h, true, 4)
}

fn glyph_coverage_contract(
    g: &GlyphShape,
    crop_w: usize,
    crop_h: usize,
    clearscan: bool,
    sub_rows: usize,
) -> Vec<f64> {
    if crop_w == 0 || crop_h == 0 {
        return Vec::new();
    }
    // flatten the path to line segments in crop-pixel coordinates. The path is
    // expressed in the glyph's construction frame: the crop maps to
    // [anchor_bbox_fu[0], +ink_span_fu[0]] x [anchor_bbox_fu[1], +ink_span_fu[1]]
    // (the same frame page_pdf uses to place the run: tx = x0 - anchor*sx/upem).
    let kx = (g.ink_span_fu[0] / crop_w as f64).max(f64::EPSILON);
    let ky = if clearscan {
        (g.ink_span_fu[1] / crop_h as f64).max(f64::EPSILON)
    } else {
        kx
    };
    let to_x = |x: f64| (x - if clearscan { g.anchor_bbox_fu[0] } else { 0.0 }) / kx;
    let to_y =
        |y: f64| crop_h as f64 - (y - if clearscan { g.anchor_bbox_fu[1] } else { 0.0 }) / ky;
    let mut polys: Vec<Vec<[f64; 2]>> = Vec::new();
    let mut cur: Vec<[f64; 2]> = Vec::new();
    let mut start = [0.0f64, 0.0f64];
    let mut last = [0.0f64, 0.0f64];
    let flatten =
        |p0: [f64; 2], p1: [f64; 2], p2: [f64; 2], p3: [f64; 2], cur: &mut Vec<[f64; 2]>| {
            const N: usize = 12;
            for i in 1..=N {
                let t = i as f64 / N as f64;
                let u = 1.0 - t;
                let x = u * u * u * p0[0]
                    + 3.0 * u * u * t * p1[0]
                    + 3.0 * u * t * t * p2[0]
                    + t * t * t * p3[0];
                let y = u * u * u * p0[1]
                    + 3.0 * u * u * t * p1[1]
                    + 3.0 * u * t * t * p2[1]
                    + t * t * t * p3[1];
                cur.push([x, y]);
            }
        };
    for el in g.path.iter() {
        match el {
            kurbo::PathEl::MoveTo(p) => {
                if cur.len() > 1 {
                    polys.push(std::mem::take(&mut cur));
                } else {
                    cur.clear();
                }
                start = [to_x(p.x), to_y(p.y)];
                last = start;
                cur.push(start);
            }
            kurbo::PathEl::LineTo(p) => {
                last = [to_x(p.x), to_y(p.y)];
                cur.push(last);
            }
            kurbo::PathEl::QuadTo(c, p) => {
                // raise the quad to a cubic and flatten
                let (cx, cy, px, py) = (to_x(c.x), to_y(c.y), to_x(p.x), to_y(p.y));
                let c1 = [
                    last[0] + 2.0 / 3.0 * (cx - last[0]),
                    last[1] + 2.0 / 3.0 * (cy - last[1]),
                ];
                let c2 = [px + 2.0 / 3.0 * (cx - px), py + 2.0 / 3.0 * (cy - py)];
                flatten(last, c1, c2, [px, py], &mut cur);
                last = [px, py];
            }
            kurbo::PathEl::CurveTo(c1, c2, p) => {
                let flip = to_y;
                flatten(
                    last,
                    [to_x(c1.x), flip(c1.y)],
                    [to_x(c2.x), flip(c2.y)],
                    [to_x(p.x), flip(p.y)],
                    &mut cur,
                );
                last = [to_x(p.x), flip(p.y)];
            }
            kurbo::PathEl::ClosePath => {
                if cur.len() > 1 {
                    cur.push(start);
                    polys.push(std::mem::take(&mut cur));
                } else {
                    cur.clear();
                }
                last = start;
            }
        }
    }
    if cur.len() > 1 {
        polys.push(cur);
    }
    // scanline fill (even-odd) with sub-pixel coverage sampling: the fidelity
    // measure must match the SPEC's mask definition as the qualification
    // harness applies it (render, threshold at the paper/ink midpoint), so a
    // pixel counts as foreground when its covered fraction reaches 0.5
    let mut cover = vec![0.0f64; crop_w * crop_h];
    for row in 0..crop_h {
        for sub in 0..sub_rows {
            let py = row as f64 + (sub as f64 + 0.5) / sub_rows as f64;
            let mut xs: Vec<f64> = Vec::new();
            for poly in &polys {
                for w in poly.windows(2) {
                    let (a, b) = (w[0], w[1]);
                    let (y0, y1) = (a[1], b[1]); // crop-local px
                    if (y0 <= py && y1 > py) || (y1 <= py && y0 > py) {
                        let t = (py - y0) / (y1 - y0);
                        xs.push(a[0] + t * (b[0] - a[0]));
                    }
                }
            }
            if xs.len() < 2 {
                continue;
            }
            xs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            let mut i = 0;
            while i + 1 < xs.len() {
                let (x0, x1) = (xs[i], xs[i + 1]);
                // the sub-row's covered columns, weighted by the overlap length
                let c0 = x0;
                let c1 = x1;
                let col_lo = (c0.floor() as isize).max(0);
                let col_hi = ((c1.ceil() as isize).min(crop_w as isize)).max(col_lo);
                for c in col_lo..col_hi {
                    let col = c as usize;
                    let lo = (col as f64).max(c0);
                    let hi = ((col + 1) as f64).min(c1);
                    let frac = (hi - lo).max(0.0);
                    if frac > 0.0 {
                        let idx = row * crop_w + col;
                        // Accumulate actual covered area. Counting every tiny
                        // edge overlap as a whole sample dilated continuous
                        // contours and made this gate disagree with PDF renders.
                        cover[idx] += if clearscan {
                            frac / sub_rows as f64
                        } else if frac >= 0.5 {
                            2.0
                        } else {
                            1.0
                        };
                    }
                }
                i += 2;
            }
        }
    }
    cover
}

fn span_bbox(poly: &[[f64; 2]]) -> [f64; 4] {
    let mut bb = [f64::MAX, f64::MAX, f64::MIN, f64::MIN];
    for [x, y] in poly {
        bb[0] = bb[0].min(*x);
        bb[1] = bb[1].min(*y);
        bb[2] = bb[2].max(*x);
        bb[3] = bb[3].max(*y);
    }
    if bb[0] > bb[2] {
        bb = [0.0, 0.0, 0.0, 0.0];
    }
    bb
}

pub fn convert(input: &Input, policy: &Policy) -> Result<Output, String> {
    let (parts, report) = convert_parts(input, policy)?;
    // single-page PDF + the B0 searchable-raster baseline candidate (the
    // document-level equivalent lives in crate::document)
    let (shapes, encodings) = (&parts.shapes, parts.encodings.clone());
    let font_bytes = build_font(shapes, &encodings, policy.upem)?;
    let pdf_bytes = crate::page_pdf::assemble_with_options(
        &parts.shapes,
        &encodings,
        &parts.occurrences,
        &parts.span_texts,
        parts.page_w_pt,
        parts.page_h_pt,
        parts.paper,
        parts.ink,
        font_bytes.clone(),
        Vec::new(),
        &[],
        &parts.patches,
        &parts.owners,
        &parts.owner_cids,
        &parts.lines,
        &parts.to_pt,
        policy.image_encoding,
    )?;
    let b0 = baseline_one_page(&parts, policy)?;

    let candidates: Vec<(String, usize)> = vec![
        ("reconstruct".to_string(), pdf_bytes.len()),
        ("raster_baseline".to_string(), b0.len()),
    ];
    // the fidelity policy is a hard gate (SPEC §4.2 / policy note): the raster
    // baseline reproduces the source pixels exactly, the reconstruction does
    // not if its vector units measure below min_ink_iou
    let preservation_ok = policy.profile == "clearscan"
        || report
            .fidelity
            .preservation_ink_iou_min
            .is_none_or(|m| m >= policy.min_ink_iou);
    let restoration_ok =
        policy.profile != "clearscan" || report.reconstruction.restoration_qualified;
    let recon_fidelity_ok = preservation_ok && restoration_ok;
    let selected = if policy.mode == "auto" {
        if recon_fidelity_ok && pdf_bytes.len() <= b0.len() {
            "reconstruct"
        } else {
            "raster_baseline"
        }
        .to_string()
    } else if !recon_fidelity_ok {
        return Err(format!(
            "fidelity policy violated: page {} measures vector ink IoU {} below min_ink_iou {} \
             (use --mode auto to emit the searchable raster baseline, or lower the policy explicitly)",
            input.page_id,
            report.fidelity.preservation_ink_iou_min.unwrap_or(0.0),
            policy.min_ink_iou
        ));
    } else {
        "reconstruct".to_string()
    };
    // the emitted candidate; the B0 is still returned separately for the harness
    let pdf_bytes = if selected == "raster_baseline" {
        b0.clone()
    } else {
        pdf_bytes
    };
    let mut report = report;
    report.candidates = candidates;
    report.selected = selected;
    report.pdf_bytes = pdf_bytes.len();
    report.font_bytes = font_bytes.len();
    let raster_bytes: usize = parts.patches.iter().map(|p| p.rgb.len()).sum();
    report.raster_bytes = raster_bytes;
    Ok(Output {
        pdf_bytes,
        b0_bytes: b0,
        report,
        font_bytes,
    })
}

/// The page's assembly parts + its report facts. `convert` wraps this with the
/// single-page PDF/B0 assembly; the document builder uses it directly.
pub fn convert_parts(
    input: &Input,
    policy: &Policy,
) -> Result<(crate::page_pdf::PageParts, Report), String> {
    convert_parts_with_document_donors(input, policy, &[])
}

pub(crate) fn convert_parts_with_document_donors(
    input: &Input,
    policy: &Policy,
    document_donors: &[crate::units::Unit],
) -> Result<(crate::page_pdf::PageParts, Report), String> {
    // The OCR page affine is authoritative for the source raster resolution.
    // In particular, bundled 600 DPI pages must not inherit the CLI's 300 DPI
    // default for background reduction and pixel-sized restoration footprints.
    let mut effective_policy = policy.clone();
    if policy.profile == "clearscan" {
        effective_policy.dpi = clearscan_source_dpi(input.raster_to_page_pt, &input.page_id)?;
    }
    let policy = &effective_policy;
    let start = std::time::Instant::now();
    let mut stage_timings_ms = BTreeMap::new();
    let w = input.width;
    let h = input.height;

    // SPEC §4.2: the OCR page declares a canonical pixel hash for this raster;
    // refuse to work on pixels that do not match the declared binding
    if let Some(declared) = &input.pixel_sha256 {
        let computed = scanweave_core::pixel_hash::pixel_hash(
            scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
            w as u64,
            h as u64,
            scanweave_core::pixel_hash::ColourTag::Srgb,
            None,
            &input.rgb,
        )
        .map_err(|e| e.to_string())?;
        if &computed != declared {
            return Err(format!(
                "pixel binding mismatch for page {}: OCR page declares {declared}, raster computes {computed}",
                input.page_id
            ));
        }
    }

    // segmentation + ownership -------------------------------------------------
    let seg: Segmentation = segment(&input.rgb, w, h);
    let ocr = to_ocr_page(input);
    let (mut plan, _) = build_plan(&seg, w, h, &ocr);
    if policy.profile == "clearscan" {
        // Non-canonical local vectors (notably disconnected kana) need the
        // same original grayscale evidence as selected document witnesses.
        for owned in &mut plan.owned {
            owned.unit.retain_grayscale(&input.rgb, w, h);
        }
    }
    stage_timings_ms.insert("segmentation_ownership".into(), start.elapsed().as_millis());
    let evidence_started = std::time::Instant::now();
    let visual_ok = plan.visual_invariant_ok();
    let semantic_ok = plan.semantic_invariant_ok(&ocr);

    // SPEC §4.4: caller-provided protection polygons (their pixel boxes, clamped
    // to the raster) are a distinct input to the visual planner
    let protected_boxes: Vec<[f64; 4]> = input
        .protected_regions
        .iter()
        .map(|p| {
            let mut bb = span_bbox(&p.polygon);
            bb[0] = bb[0].clamp(0.0, w as f64);
            bb[1] = bb[1].clamp(0.0, h as f64);
            bb[2] = bb[2].clamp(0.0, w as f64);
            bb[3] = bb[3].clamp(0.0, h as f64);
            bb
        })
        .filter(|bb| bb[2] > bb[0] && bb[3] > bb[1])
        .collect();

    // regions (protection / non-text contact → raster) -------------------------
    let mut regions = plan_regions(&plan, &protected_boxes);

    let mut coverage = Coverage::default();
    let mut fallback_reasons: BTreeMap<String, usize> = BTreeMap::new();
    for r in &regions {
        let is_vector = matches!(r.disposition, RegionDisposition::Vector);
        for &ui in &r.units {
            let ink = plan.owned[ui].unit.mask.iter().filter(|b| **b).count() as u64;
            coverage.text_ink_px_total += ink;
            if is_vector {
                coverage.text_ink_px_vector += ink;
            } else {
                coverage.text_ink_px_raster += ink;
            }
        }
        if let RegionDisposition::Raster { reason } = &r.disposition {
            *fallback_reasons.entry(format!("{reason:?}")).or_insert(0) += 1;
        }
    }
    for (au, _) in &plan.artwork_units {
        coverage.other_ink_px += au.mask.iter().filter(|b| **b).count() as u64;
    }
    // honest page-level ink census: count how many owners claim each foreground
    // pixel (units raster+vector and artwork, via their crop masks). unowned =
    // fg ink claimed by nobody; multiply_owned = claimed more than once.
    {
        let mut claim: Vec<u8> = vec![0u8; (w as usize) * (h as usize)];
        let mut stamp = |bbox: [f64; 4], mask: &[bool]| {
            let (x0, y0) = (bbox[0].floor() as usize, bbox[1].floor() as usize);
            let mw = (bbox[2].ceil() as usize).saturating_sub(x0);
            for (i, on) in mask.iter().enumerate() {
                if !*on {
                    continue;
                }
                let (cx, cy) = (i % mw, i / mw);
                let (px, py) = (x0 + cx, y0 + cy);
                if px < w as usize && py < h as usize {
                    claim[py * w as usize + px] = claim[py * w as usize + px].saturating_add(1);
                }
            }
        };
        for r in &regions {
            for &ui in &r.units {
                stamp(plan.owned[ui].unit.bbox_px, &plan.owned[ui].unit.mask);
            }
        }
        for (au, _) in &plan.artwork_units {
            stamp(au.bbox_px, &au.mask);
        }
        for (i, fg) in seg.fg.iter().enumerate() {
            if !*fg {
                continue;
            }
            match claim[i] {
                0 => coverage.unowned_ink_px += 1,
                1 => {}
                _ => coverage.multiply_owned_ink_px += 1,
            }
        }
    }

    // tracing (vector regions only); failures → raster -------------------------
    let em_px = plan
        .owned
        .iter()
        .map(|u| u.unit.crop_h as f64)
        .fold(0.0f64, f64::max);
    let upem = policy.upem as f64;
    // A reconstructed ink box is not an em square. Reserve font-space
    // headroom instead of filling the entire em with the tallest observed
    // ink. Page placement uses ink_span_fu and exactly cancels this scale.
    // Besides giving continuous curves an appropriate construction frame,
    // this avoids the small-em text-bitmap path's origin/coverage artifacts.
    // Faithful keeps its established font coordinates.
    let outline_em = if policy.profile == "clearscan" {
        upem * 0.5
    } else {
        upem
    };
    let units_per_px = if em_px > 0.0 {
        outline_em / em_px
    } else {
        outline_em
    };
    let budget = Budget::from_m0_policy();
    // Add eligible observations from sibling pages only for dictionary
    // evidence. They are removed immediately afterward and never participate
    // in page ownership, placement, coverage, or Unicode reporting.
    let local_units = plan.owned.len();
    let source_masks: std::collections::HashMap<_, _> = plan
        .owned
        .iter()
        .map(|owned| {
            (
                owned.unit.symbol_id.clone(),
                (
                    owned.unit.crop_w,
                    owned.unit.crop_h,
                    owned.unit.mask.clone(),
                ),
            )
        })
        .collect();
    for donor in document_donors {
        let mut donor = donor.clone();
        donor.symbol_id = format!("__doc_donor:{}", donor.symbol_id);
        donor.span_id = format!("__doc_donor:{}", donor.span_id);
        plan.owned.push(crate::ownership::OwnedUnit {
            unit: donor,
            components: Vec::new(),
            slots: Vec::new(),
            suspect: false,
        });
    }
    let mut reconstruction =
        crate::visual_dict::reconstruct(&mut plan, policy, &input.rgb, input.width, input.height);
    plan.owned.truncate(local_units);
    reconstruction
        .observations
        .retain(|o| !o.symbol_id.starts_with("__doc_donor:"));
    reconstruction
        .occurrences
        .retain(|o| !o.symbol_id.starts_with("__doc_donor:"));

    stage_timings_ms.insert(
        "planning_matching_reconstruction".into(),
        evidence_started.elapsed().as_millis(),
    );
    let tracing_started = std::time::Instant::now();
    let mut traced: Vec<TracedShape> = Vec::new();
    let mut missing: std::collections::HashSet<(String,)> = std::collections::HashSet::new();
    for symbol_id in &reconstruction.rejected_symbols {
        missing.insert((symbol_id.clone(),));
    }
    {
        let mut seen: Vec<String> = Vec::new();
        for r in regions.iter() {
            if !matches!(r.disposition, RegionDisposition::Vector) {
                continue;
            }
            for &ui in &r.units {
                let u = &plan.owned[ui].unit;
                if seen.contains(&u.shape_key) {
                    continue;
                }
                let prototype = reconstruction
                    .prototype_units
                    .get(&u.shape_key)
                    .unwrap_or(u);
                match if policy.profile == "clearscan" {
                    {
                        let preserved_source = plan.owned.iter().map(|o| &o.unit).find(|other| {
                            other.shape_key == u.shape_key
                                && !reconstruction.repaired_symbols.contains(&other.symbol_id)
                                && !reconstruction.reused_symbols.contains(&other.symbol_id)
                        });
                        crate::trace::trace_shape_clearscan(
                            prototype,
                            &budget,
                            units_per_px,
                            preserved_source.map(|source| (source, policy.min_ink_iou)),
                        )
                    }
                } else {
                    trace_shape(prototype, &budget, units_per_px)
                } {
                    Ok(t) => {
                        seen.push(u.shape_key.clone());
                        traced.push(t);
                    }
                    Err(_) => {
                        missing.insert((u.symbol_id.clone(),));
                    }
                }
            }
        }
    }
    let mut shapes: Vec<GlyphShape> = build_glyph_shapes(&traced, units_per_px, &budget)?;
    for shape in &shapes {
        if let Some(unit) = reconstruction.prototype_units.get(&shape.shape_key) {
            reconstruction
                .canonical_geometry
                .push(crate::visual_dict::CanonicalGeometry {
                    contour_fit: traced
                        .iter()
                        .find(|t| t.shape_key == shape.shape_key)
                        .and_then(|t| t.contour_fit.clone()),
                    prototype_id: format!("prototype:{}", shape.shape_key),
                    witness_symbol_id: unit.symbol_id.clone(),
                    witness_bbox_px: unit.bbox_px,
                    width: unit.crop_w,
                    height: unit.crop_h,
                    mask: unit.mask.clone(),
                    grayscale: unit.gray_samples.clone(),
                    path_svg: shape.path.to_svg(),
                    anchor_bbox_fu: shape.anchor_bbox_fu,
                    ink_span_fu: shape.ink_span_fu,
                });
        }
    }
    // Restoration has a separate gate: the selected observed prototype must
    // survive the actual tracing step with high overlap to its refined donor.
    for occurrence in reconstruction
        .occurrences
        .iter_mut()
        .filter(|o| o.repaired || o.reused)
    {
        let prototype_key = occurrence
            .prototype_id
            .as_deref()
            .unwrap_or("")
            .strip_prefix("prototype:")
            .unwrap_or("");
        let donor = reconstruction.prototype_units.get(prototype_key);
        let traced_iou = donor.and_then(|donor| {
            shapes
                .iter()
                .find(|s| s.shape_key == prototype_key)
                .map(|g| reconstructed_glyph_ink_iou(g, donor.crop_w, donor.crop_h, &donor.mask))
        });
        occurrence.prototype_trace_iou = traced_iou;
        let source_iou = source_masks
            .get(&occurrence.symbol_id)
            .and_then(|(w, h, mask)| {
                shapes
                    .iter()
                    .find(|g| g.shape_key == prototype_key)
                    .map(|g| reconstructed_glyph_ink_iou(g, *w, *h, mask))
            });
        occurrence.source_mask_iou = source_iou;
        // A healthy occurrence should not be replaced by a visibly different
        // document prototype. ClearScan allows modest raster variation, but
        // rejects a reuse whose traced canonical outline poorly matches this
        // witness. Damaged occurrences use their donor-supported repair gate.
        let reuse_source_floor = if policy.profile == "clearscan" {
            0.80
        } else {
            0.98
        };
        let source_gate_failed =
            occurrence.reused && source_iou.is_none_or(|iou| iou < reuse_source_floor);
        let invalid_geometry = occurrence
            .replacement_bbox_px
            .is_some_and(|b| !b.iter().all(|v| v.is_finite()) || b[2] <= b[0] || b[3] <= b[1]);
        let insufficient_donor = policy.profile == "clearscan"
            && donor.is_some_and(|u| {
                u.crop_h < 4
                    || u.mask.iter().filter(|&&b| b).count() < 6
                    || (u.crop_h as f64) < (u.ocr_bbox_px[3] - u.ocr_bbox_px[1]) * 0.3
            });
        if traced_iou.is_none_or(|iou| iou < 0.90)
            || source_gate_failed
            || invalid_geometry
            || insufficient_donor
        {
            occurrence.repaired = false;
            occurrence.reused = false;
            occurrence.restoration_evidence_passed = false;
            occurrence.decision = if invalid_geometry {
                "rejected_invalid_replacement_geometry".into()
            } else if insufficient_donor {
                "rejected_insufficient_donor_extent".into()
            } else if source_gate_failed {
                "rejected_unchanged_source_fidelity".into()
            } else {
                "rejected_traced_prototype_fidelity".into()
            };
            missing.insert((occurrence.symbol_id.clone(),));
        }
    }
    reconstruction.restoration_qualified = reconstruction
        .occurrences
        .iter()
        .filter(|o| o.repaired || o.reused)
        .all(|o| {
            o.restoration_evidence_passed
                && o.prototype_trace_iou.is_some_and(|v| v >= 0.90)
                && (policy.profile == "clearscan"
                    || !o.reused
                    || o.source_mask_iou.is_some_and(|v| v >= 0.98))
        });
    if !missing.is_empty() {
        for r in regions.iter_mut() {
            if !matches!(r.disposition, RegionDisposition::Vector) {
                continue;
            }
            if r.units
                .iter()
                .any(|ui| missing.contains(&(plan.owned[*ui].unit.symbol_id.clone(),)))
            {
                r.disposition = RegionDisposition::Raster {
                    reason: FallbackReason::UnsupportedContent,
                };
                *fallback_reasons
                    .entry(format!("{:?}", FallbackReason::UnsupportedContent))
                    .or_insert(0) += 1;
                for &ui in &r.units {
                    let ink = plan.owned[ui].unit.mask.iter().filter(|b| **b).count() as u64;
                    coverage.text_ink_px_vector -= ink;
                    coverage.text_ink_px_raster += ink;
                }
            }
        }
    }

    // policy fidelity gate (min_ink_iou): the traced outline must reproduce the
    // unit's source ink mask to the policy's threshold. Raster regions are
    // byte-exact from the source by construction; only vectorized units carry
    // this risk, so this is where the advertised 0.98 is actually enforced.
    // measured per unit (symbol id → IoU), for every unit that was a vector
    // candidate at measurement time; the post-degradation survivors are derived
    // from the final regions below
    let mut measured: Vec<(String, f64)> = Vec::new();
    {
        for r in regions.iter() {
            if !matches!(r.disposition, RegionDisposition::Vector) {
                continue;
            }
            for &ui in &r.units {
                let u = &plan.owned[ui].unit;
                let Some(g) = shapes.iter().find(|s| s.shape_key == u.shape_key) else {
                    continue;
                };
                let iou = if policy.profile == "clearscan" {
                    reconstructed_glyph_ink_iou(g, u.crop_w, u.crop_h, &u.mask)
                } else {
                    glyph_ink_iou(g, u.crop_w, u.crop_h, &u.mask)
                };
                measured.push((u.symbol_id.clone(), iou));
            }
        }
    }
    for occurrence in &mut reconstruction.occurrences {
        occurrence.source_mask_iou = measured
            .iter()
            .find(|(symbol, _)| symbol == &occurrence.symbol_id)
            .map(|(_, iou)| *iou)
            .or(occurrence.source_mask_iou);
    }
    let mut units_below_policy = 0usize;
    if !measured.is_empty() {
        // regions whose WORST unit falls below the threshold degrade to raster
        let mut worst_by_region: std::collections::BTreeMap<usize, f64> =
            std::collections::BTreeMap::new();
        for r in &regions {
            if !matches!(r.disposition, RegionDisposition::Vector) {
                continue;
            }
            let worst = r
                .units
                .iter()
                .filter_map(|&ui| {
                    let sid = plan.owned[ui].unit.symbol_id.clone();
                    if reconstruction.repaired_symbols.contains(&sid)
                        || reconstruction.reused_symbols.contains(&sid)
                    {
                        return None;
                    }
                    let u = &plan.owned[ui].unit;
                    if policy.profile == "clearscan"
                        && (u.crop_h < 4
                            || u.mask.iter().filter(|&&b| b).count() < 6
                            || (u.crop_h as f64) < (u.ocr_bbox_px[3] - u.ocr_bbox_px[1]) * 0.3)
                    {
                        // A source speck can match its own mask perfectly but
                        // cannot support a readable character-sized vector.
                        // Preserve it natively and use the original OCR box for
                        // its invisible label; a qualified healthy donor above
                        // can still repair a genuinely damaged observation.
                        return Some(0.0);
                    }
                    measured.iter().find(|(k, _)| *k == sid).map(|(_, v)| *v)
                })
                .fold(1.0f64, f64::min);
            worst_by_region.insert(r.id, worst);
        }
        for r in regions.iter_mut() {
            if !matches!(r.disposition, RegionDisposition::Vector) {
                continue;
            }
            let worst = worst_by_region.get(&r.id).copied().unwrap_or(1.0);
            if worst < policy.min_ink_iou {
                r.disposition = RegionDisposition::Raster {
                    reason: FallbackReason::FidelityBelowPolicy,
                };
                *fallback_reasons
                    .entry(format!("{:?}", FallbackReason::FidelityBelowPolicy))
                    .or_insert(0) += 1;
                for &ui in &r.units {
                    let ink = plan.owned[ui].unit.mask.iter().filter(|b| **b).count() as u64;
                    coverage.text_ink_px_vector -= ink;
                    coverage.text_ink_px_raster += ink;
                }
                units_below_policy += r.units.len();
            }
        }
    }

    // encoding (four-part key) ---------------------------------------------------
    let mut keys: Vec<EncodingKey> = Vec::new();
    let mut occ: Vec<crate::page_pdf::Occurrence> = Vec::new();
    for r in &regions {
        if !matches!(r.disposition, RegionDisposition::Vector) {
            continue;
        }
        for &ui in &r.units {
            let u = &plan.owned[ui].unit;
            let Some(gidx) = shapes.iter().position(|s| s.shape_key == u.shape_key) else {
                continue;
            };
            let advance = (shapes[gidx].ink_span_fu[0].ceil() as u16)
                .saturating_add(2)
                .max(1);
            keys.push(EncodingKey {
                visual_glyph_id: gidx,
                semantic_string: u.semantic_text.clone(),
                writing_mode: WritingMode::Horizontal,
                required_metrics: MetricsKey {
                    advance,
                    units_per_em: policy.upem,
                },
            });
            occ.push((
                gidx,
                0,
                reconstruction
                    .occurrences
                    .iter()
                    .find(|record| {
                        record.symbol_id == u.symbol_id && (record.repaired || record.reused)
                    })
                    .and_then(|record| record.replacement_bbox_px)
                    .unwrap_or(u.bbox_px),
                u.span_id.clone(),
                u.symbol_id.clone(),
                u.semantic_text.clone(),
            ));
        }
    }
    let cids = allocate_cids(&keys);
    // page_pdf draws CIDs 1-based (CID 0 is .notdef); convert passes the
    // 0-based index and the assembler restores the real CID.
    for (o, cid) in occ.iter_mut().zip(cids.iter()) {
        o.1 = (*cid as u32).saturating_sub(1);
    }
    let mut encodings: Vec<(usize, String)> = Vec::new();
    for (k, _) in keys.iter().enumerate() {
        let cid = cids[k];
        if encodings.len() < cid {
            encodings.push((keys[k].visual_glyph_id, keys[k].semantic_string.clone()));
        }
    }
    let _font_bytes = build_font(&shapes, &encodings, policy.upem)?;

    // Derive suppression ownership from the final PDF occurrence list itself:
    // a symbol is cleaned only if an encoded glyph will actually be emitted.
    let vector_owned_symbols: std::collections::BTreeSet<String> = if policy.profile == "clearscan"
    {
        occ.iter().map(|occurrence| occurrence.4.clone()).collect()
    } else {
        std::collections::BTreeSet::new()
    };
    let needs_raster_recomposition =
        policy.profile != "clearscan" || !vector_owned_symbols.is_empty();
    let (
        clearscan_rgb,
        raster_ink_pixels_suppressed,
        antialias_fringe_pixels_suppressed,
        weak_rules,
    ) = if policy.profile == "clearscan" && needs_raster_recomposition {
        let (rgb, ink_count, fringe_count, weak_rules) = clean_replaced_text(
            input,
            &plan,
            &vector_owned_symbols,
            &vector_owned_symbols,
            &reconstruction,
            policy.dpi,
            seg.paper,
        );
        (Some(rgb), ink_count, fringe_count, weak_rules)
    } else {
        (None, 0, 0, Vec::new())
    };

    // The compact page background sits below native-resolution fallback
    // patches. Remove every recognized text mask from that low-resolution
    // layer, including glyphs that remain raster, or their downsampled ink
    // will show as a soft duplicate underneath the source-exact patch.
    let clearscan_background = if policy.profile == "clearscan" && needs_raster_recomposition {
        let all_text_symbols: std::collections::BTreeSet<String> = plan
            .owned
            .iter()
            .map(|owned| owned.unit.symbol_id.clone())
            .collect();
        Some(
            clean_replaced_text(
                input,
                &plan,
                &all_text_symbols,
                &vector_owned_symbols,
                &reconstruction,
                policy.dpi,
                seg.paper,
            )
            .0,
        )
    } else {
        None
    };

    stage_timings_ms.insert(
        "tracing_placement_cleanup".into(),
        tracing_started.elapsed().as_millis(),
    );
    let composition_started = std::time::Instant::now();
    // raster patches (fallback regions) + artwork ------------------------------
    let mut patches: Vec<Patch> = Vec::new();
    let mut semantic_owner: BTreeMap<String, String> = BTreeMap::new();
    for s in &ocr.spans {
        semantic_owner.insert(s.id.clone(), "invisible".into());
    }
    for r in &regions {
        if !needs_raster_recomposition
            || !matches!(r.disposition, RegionDisposition::Raster { .. })
            || r.units.is_empty()
        {
            continue;
        }
        let mut bb = r.bbox_px;
        if policy.profile == "clearscan" {
            let padding = if policy.dpi >= 450.0 { 2.0 } else { 1.0 };
            bb = [
                bb[0] - padding,
                bb[1] - padding,
                bb[2] + padding,
                bb[3] + padding,
            ];
        }
        let x0 = bb[0].max(0.0) as usize;
        let y0 = bb[1].max(0.0) as usize;
        let x1 = (bb[2] as usize).min(w as usize).max(x0 + 1);
        let y1 = (bb[3] as usize).min(h as usize).max(y0 + 1);
        let pw = x1 - x0;
        let ph = y1 - y0;
        let mut rgb = vec![0u8; pw * ph * 3];
        for yy in 0..ph {
            for xx in 0..pw {
                let si = ((y0 + yy) * w as usize + (x0 + xx)) * 3;
                let di = (yy * pw + xx) * 3;
                let source = clearscan_rgb.as_deref().unwrap_or(&input.rgb);
                rgb[di..di + 3].copy_from_slice(&source[si..si + 3]);
            }
        }
        patches.push(Patch {
            compact_background: false,
            bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
            rgb,
            w: pw as u32,
            h: ph as u32,
        });
        for &ui in &r.units {
            semantic_owner.insert(plan.owned[ui].unit.span_id.clone(), "invisible".into());
        }
    }
    for r in &regions {
        if matches!(r.disposition, RegionDisposition::Vector) {
            for &ui in &r.units {
                semantic_owner.insert(
                    plan.owned[ui].unit.span_id.clone(),
                    "visible_tounicode".into(),
                );
            }
        }
    }
    // unrecognized/artwork ink is also restored as source raster pixels (VS-05:
    // preserve or invent nothing). Bucketed on a 32px grid to bound object count.
    let patch_source = clearscan_rgb.as_deref().unwrap_or(&input.rgb);
    if needs_raster_recomposition {
        patches.extend(artwork_patches(patch_source, w as usize, h as usize, &plan));
    }

    // Compact backgrounds are supplemented by native residual-detail patches
    // below. Explicit protection remains independent of OCR segmentation.
    if policy.profile == "clearscan" {
        // Protection must work even when OCR finds no glyph in the polygon.
        for &protected in &protected_boxes {
            patches.push(patch_from_rgb(
                patch_source,
                w as usize,
                h as usize,
                protected,
            ));
        }
    }

    // Coherent weak marks are native content even if OCR/segmentation missed
    // them. Copy the cleaned source so their strip cannot repaint vector ink.
    for bbox in weak_rules {
        let cell = (8.0 * policy.dpi / 300.0).round().max(8.0);
        let padded = [
            (bbox[0] / cell).floor() * cell,
            (bbox[1] / cell).floor() * cell,
            ((bbox[2] / cell).ceil() * cell).min(w as f64),
            ((bbox[3] / cell).ceil() * cell).min(h as f64),
        ];
        patches.push(patch_from_rgb(patch_source, w as usize, h as usize, padded));
    }

    // coalesce: merge overlapping or exactly-adjacent patches (the artwork
    // buckets tile the page, so this collapses hundreds of 32x32 cells into a
    // few large rects). Merged patches copy the full source rect of the union,
    // so every emitted pixel stays byte-identical to the source.
    // ClearScan always rebuilds merged images from the cleaned source raster.
    let patches = if !needs_raster_recomposition {
        // No emitted vector can supersede source ink: retain one whole-page
        // image directly, avoiding cleanup, detail tiling and patch coalescing.
        vec![patch_from_rgb(
            &input.rgb,
            w as usize,
            h as usize,
            [0.0, 0.0, w as f64, h as f64],
        )]
    } else if policy.profile == "clearscan" {
        let mut layers = coalesce_patches_rgb(patch_source, w as usize, h as usize, patches);
        let background = downsampled_background_patch(
            clearscan_background.as_deref().unwrap_or(patch_source),
            w,
            h,
            policy.dpi,
        );
        let (background, exceptions) = compact_paper_background(background, w, h, &layers);
        layers.extend(
            exceptions
                .into_iter()
                .map(|bbox| patch_from_rgb(patch_source, w as usize, h as usize, bbox)),
        );
        let detail = residual_detail_patches(patch_source, w, h, &background, &layers);
        layers.extend(detail);
        let mut layers = coalesce_patches_rgb(patch_source, w as usize, h as usize, layers);
        let native_area: f64 = layers
            .iter()
            .map(|p| (p.bbox_px[2] - p.bbox_px[0]) * (p.bbox_px[3] - p.bbox_px[1]))
            .sum();
        // Fragmented native patches can cost more than a single cleaned
        // residual page. Compare actual lossless streams, not area alone.
        // Source ink has already been suppressed in patch_source.
        let fragmented = layers.len() > 32 && native_area > (w as f64 * h as f64) * 0.2;
        let prefer_whole = if fragmented {
            let whole = patch_from_rgb(
                patch_source,
                w as usize,
                h as usize,
                [0.0, 0.0, w as f64, h as f64],
            );
            let whole_bytes = crate::page_pdf::lossless_patch_cost(std::slice::from_ref(&whole))?;
            let layered_bytes = crate::page_pdf::lossless_patch_cost(&layers)?
                + crate::page_pdf::lossless_patch_cost(std::slice::from_ref(&background))?;
            whole_bytes * 10 < layered_bytes * 9
        } else {
            false
        };
        if prefer_whole || native_area > (w as f64 * h as f64) * 0.6 {
            vec![patch_from_rgb(
                patch_source,
                w as usize,
                h as usize,
                [0.0, 0.0, w as f64, h as f64],
            )]
        } else {
            layers.insert(0, background);
            layers
        }
    } else if vector_owned_symbols.is_empty() {
        coalesce_patches(input, patches)
    } else {
        patches
    };
    let raster_bytes: usize = patches.iter().map(|p| p.rgb.len()).sum();

    // invisible owners: exactly one per span that is NOT painted by a vector
    // region (SPEC §6.2: never a duplicate layer under already-searchable text)
    let vector_spans: std::collections::HashSet<String> = occ.iter().map(|o| o.3.clone()).collect();
    let visible_slots: std::collections::BTreeSet<String> = plan
        .owned
        .iter()
        .filter(|u| vector_owned_symbols.contains(&u.unit.symbol_id))
        .flat_map(|u| u.slots.iter().map(|s| s.symbol_id.clone()))
        .collect();
    let mut owners: Vec<Owner> = Vec::new();
    for r in &regions {
        if !matches!(r.disposition, RegionDisposition::Raster { .. }) {
            continue;
        }
        for &ui in &r.units {
            let sid = plan.owned[ui].unit.span_id.clone();
            if vector_spans.contains(&sid) {
                continue; // visible ToUnicode already owns this span
            }
            // dedup by SPAN ID: two spans may carry identical OCR text (a
            // repeated word where only one has visual components); text-based
            // dedup would silently drop the other span's owner
            if owners.iter().any(|o| o.span_id == sid) {
                continue;
            }
            let text = ocr
                .spans
                .iter()
                .find(|s| s.id == sid)
                .map(|s| s.text.clone())
                .unwrap_or_default();
            let bbox = ocr
                .spans
                .iter()
                .find(|s| s.id == sid)
                .map(|s| span_bbox(&s.polygon))
                .unwrap_or([0.0, 0.0, 0.0, 0.0]);
            // placement on the traced INK baseline: the first unit of the span
            // (its traced glyph box), matching how visible runs are placed
            let place = plan
                .owned
                .iter()
                .find(|u| u.unit.span_id == sid)
                .map(|u| u.unit.bbox_px)
                .unwrap_or(bbox);
            owners.push(Owner {
                characters: Vec::new(),
                visible_order: BTreeMap::new(),
                text,
                bbox_px: bbox,
                place_px: place,
                span_id: sid,
            });
        }
    }
    for s in &ocr.spans {
        let complete_vector_span = vector_spans.contains(&s.id)
            && (policy.profile != "clearscan"
                || s.symbols
                    .iter()
                    .all(|symbol| visible_slots.contains(&symbol.id)));
        if complete_vector_span || owners.iter().any(|o| o.span_id == s.id) {
            continue;
        }
        let place = plan
            .owned
            .iter()
            .find(|u| u.unit.span_id == s.id)
            .map(|u| u.unit.bbox_px)
            .unwrap_or_else(|| span_bbox(&s.polygon));
        owners.push(Owner {
            characters: Vec::new(),
            visible_order: BTreeMap::new(),
            text: s.text.clone(),
            bbox_px: span_bbox(&s.polygon),
            place_px: place,
            span_id: s.id.clone(),
        });
    }
    // clamp owner boxes to the canonical raster (OCR polygons may overrun it)
    for o in owners.iter_mut() {
        o.bbox_px[0] = o.bbox_px[0].max(0.0);
        o.bbox_px[1] = o.bbox_px[1].max(0.0);
        o.bbox_px[2] = o.bbox_px[2].min(w as f64);
        o.bbox_px[3] = o.bbox_px[3].min(h as f64);
    }
    let _owner_encodings: Vec<(usize, String)> =
        owners.iter().map(|o| (0usize, o.text.clone())).collect();
    let span_texts: Vec<(String, String)> = ocr
        .spans
        .iter()
        .map(|s| (s.id.clone(), s.text.clone()))
        .collect();
    // reading-order lines: OCR-authoritative separators, no invented whitespace
    let mut lines: Vec<crate::page_pdf::LineSpec> = Vec::new();
    {
        let mut cur_text = String::new();
        let mut cur_spans: Vec<String> = Vec::new();
        for s in &ocr.spans {
            if s.text.is_empty() {
                continue;
            }
            cur_text.push_str(&s.text);
            cur_text.push_str(&s.separator_after);
            cur_spans.push(s.id.clone());
            if s.separator_after.contains('\n') {
                lines.push(crate::page_pdf::LineSpec {
                    text: cur_text.trim_end().to_string(),
                    spans: std::mem::take(&mut cur_spans),
                });
                cur_text.clear();
            }
        }
        if !cur_spans.is_empty() {
            lines.push(crate::page_pdf::LineSpec {
                text: cur_text.trim_end().to_string(),
                spans: cur_spans,
            });
        }
    }
    // One font resource for everything: the vector CIDs plus an owner CID per
    // fallback span text (referencing GID1, drawn invisibly — the overlay the M0
    // baseline proved extractable). No second font, no second layer.
    let mut all_encodings = encodings.clone();
    let mut owner_cids: Vec<u32> = Vec::new();
    for o in &owners {
        if policy.profile == "clearscan" {
            owner_cids.push(1);
            continue;
        }
        let glyph_idx = if let Some((_, _t)) = encodings.iter().find(|(_, t)| t == &o.text) {
            encodings.iter().position(|(_, t)| t == &o.text).unwrap()
        } else {
            0usize
        };
        if let Some(cid) = all_encodings.iter().position(|(_, t)| t == &o.text) {
            owner_cids.push(cid as u32 + 1);
            continue;
        }
        let cid = all_encodings.len() as u32 + 1;
        all_encodings.push((glyph_idx, o.text.clone()));
        owner_cids.push(cid);
    }
    if policy.profile == "clearscan" {
        // A many-character ToUnicode string on one fallback CID can trigger
        // PDFium's overlap suppression. Keep the original span as ActualText,
        // but give its characters independent CIDs and OCR character boxes.
        let owner_shape_index = shapes.len();
        if !owners.is_empty() {
            shapes.push(crate::glyphs::semantic_owner_shape(outline_em));
        }
        for (owner_index, owner) in owners.iter_mut().enumerate() {
            let chars: Vec<_> = owner.text.char_indices().collect();
            let span = input.spans.iter().find(|s| s.id == owner.span_id);
            if let Some(span) = span {
                for u in plan.owned.iter().filter(|u| {
                    u.unit.span_id == owner.span_id
                        && vector_owned_symbols.contains(&u.unit.symbol_id)
                }) {
                    let order = u
                        .slots
                        .iter()
                        .filter_map(|slot| {
                            span.symbols
                                .iter()
                                .find(|s| s.id == slot.symbol_id)
                                .map(|s| s.range.0)
                        })
                        .min();
                    if let Some(order) = order {
                        owner.visible_order.insert(u.unit.symbol_id.clone(), order);
                    }
                }
            }
            for (i, &(start, ch)) in chars.iter().enumerate() {
                let end = start + ch.len_utf8();
                if span
                    .and_then(|s| {
                        s.symbols
                            .iter()
                            .find(|s| s.range.0 <= start && s.range.1 >= end)
                    })
                    .is_some_and(|symbol| visible_slots.contains(&symbol.id))
                {
                    continue;
                }
                let label = ch.to_string();
                let cid = if let Some(index) = all_encodings
                    .iter()
                    .position(|(g, t)| *g == owner_shape_index && t == &label)
                {
                    index as u32 + 1
                } else {
                    all_encodings.push((owner_shape_index, label));
                    all_encodings.len() as u32
                };
                let mut b = owner.bbox_px;
                if let Some(symbol) = span.and_then(|s| {
                    s.symbols
                        .iter()
                        .find(|s| s.range.0 <= start && s.range.1 >= end)
                }) {
                    b = span_bbox(&symbol.polygon);
                    if let Some(text) = owner.text.get(symbol.range.0..symbol.range.1) {
                        let n = text.chars().count().max(1);
                        let k = owner
                            .text
                            .get(symbol.range.0..start)
                            .map(|s| s.chars().count())
                            .unwrap_or(0);
                        let width = (b[2] - b[0]) / n as f64;
                        b[0] += k as f64 * width;
                        b[2] = b[0] + width;
                    }
                } else {
                    let width = (b[2] - b[0]) / chars.len() as f64;
                    b[0] += i as f64 * width;
                    b[2] = b[0] + width;
                }
                b[0] = b[0].clamp(0.0, w as f64);
                b[2] = b[2].clamp(b[0], w as f64);
                b[1] = b[1].clamp(0.0, h as f64);
                b[3] = b[3].clamp(b[1], h as f64);
                owner.characters.push(crate::page_pdf::OwnerCharacter {
                    cid,
                    bbox_px: b,
                    order: start,
                });
                if owner.characters.len() == 1 {
                    owner_cids[owner_index] = cid;
                }
            }
        }
    }
    let mut occ_records: Vec<OccurrenceRecord> = Vec::new();
    for r in &regions {
        for &ui in &r.units {
            let u = &plan.owned[ui];
            occ_records.push(OccurrenceRecord {
                page_id: input.page_id.clone(),
                span_id: u.unit.span_id.clone(),
                symbol_id: u.unit.symbol_id.clone(),
                semantic_text: u.semantic_text(),
                owner: match r.disposition {
                    RegionDisposition::Vector
                        if policy.profile != "clearscan"
                            || vector_owned_symbols.contains(&u.unit.symbol_id) =>
                    {
                        "visible_tounicode"
                    }
                    // A region proposal is not proof that a glyph survived
                    // encoding/tracing. Report only actual emitted ownership.
                    _ => "invisible",
                }
                .into(),
            });
        }
    }
    for (au, _) in &plan.artwork_units {
        occ_records.push(OccurrenceRecord {
            page_id: input.page_id.clone(),
            span_id: au.span_id.clone(),
            symbol_id: au.symbol_id.clone(),
            semantic_text: String::new(),
            owner: "unmapped".into(),
        });
    }

    let mut invariants: BTreeMap<String, bool> = BTreeMap::new();
    invariants.insert("visual".into(), visual_ok);
    invariants.insert("semantic".into(), semantic_ok);

    // real outline statistics per glyph (contours/points traced for this shape)
    let glyph_stats: Vec<GlyphStat> = shapes
        .iter()
        .enumerate()
        .map(|(gi, g)| GlyphStat {
            gid: gi,
            symbol_id: occ
                .iter()
                .find(|(gidx, ..)| *gidx == gi)
                .map(|(.., _span, sym, _text)| sym.clone())
                .unwrap_or_default(),
            stages: g.stages.clone(),
            contours: g.num_contours,
            points: g.num_points,
            budget_ok: g.stages.trace_max_px <= crate::trace::Budget::from_m0_policy().trace_max
                && g.stages.curve_max_px <= crate::trace::Budget::from_m0_policy().curve_max
                && g.stages.quant_bound_px <= crate::trace::Budget::from_m0_policy().quant_max,
        })
        .collect();
    let glyph_stats: Vec<GlyphStat> = glyph_stats
        .into_iter()
        .filter(|st| !st.symbol_id.is_empty() || st.contours > 0)
        .collect();
    let patch_records: Vec<PatchRecord> = patches
        .iter()
        .map(|p| PatchRecord {
            compact_background: p.compact_background,
            bbox_px: p.bbox_px,
            w: p.w,
            h: p.h,
            rgb_sha256: scanweave_core::hash_hex(&p.rgb),
        })
        .collect();

    // authoritative page geometry: the OCR page's raster→pt affine, applied
    // once at normalization. Axis-aligned only (b == c == 0): skews are
    // unsupported geometry and must be rejected, not silently approximated
    // with the CLI's --dpi default (a 600 dpi scan laid out at 300 dpi would
    // get the wrong physical dimensions).
    let m = input.raster_to_page_pt;
    if m[1].abs() > 1e-9 || m[2].abs() > 1e-9 {
        return Err(format!(
            "unsupported geometry: raster_to_page_pt has skew (b={}, c={})",
            m[1], m[2]
        ));
    }
    if m[0] <= 0.0 || m[3] >= 0.0 {
        return Err(format!(
            "unsupported geometry: raster_to_page_pt scale must be positive in x and negative in y (d={})",
            m[3]
        ));
    }
    let to_pt = crate::page_pdf::PageTransform {
        a: m[0],
        d: m[3],
        e: m[4],
        f: m[5],
    };
    let (page_w_pt, page_h_pt) = (to_pt.page_w(w as f64), to_pt.page_h(h as f64));

    let parts = crate::page_pdf::PageParts {
        raster_baseline: false,
        encoded_source: None,
        page_w_pt,
        page_h_pt,
        to_pt,
        source_rgb: input.rgb.clone(),
        source_w: w as usize,
        source_h: h as usize,
        shapes,
        encodings: all_encodings.clone(),
        occurrences: occ,
        span_texts,
        dpi: policy.dpi,
        paper: seg.paper,
        ink: seg.ink,
        patches,
        owners,
        owner_cids,
        lines,
    };

    // the report describes the EMITTED content: the units that remain vector
    // after the policy gate (degraded units are raster, hence exact)
    let mut unit_ious: Vec<f64> = regions
        .iter()
        .filter(|r| matches!(r.disposition, RegionDisposition::Vector))
        .flat_map(|r| r.units.iter())
        .filter_map(|&ui| {
            let sid = plan.owned[ui].unit.symbol_id.clone();
            measured.iter().find(|(k, _)| *k == sid).map(|(_, v)| *v)
        })
        .collect();
    let mut preservation_ious: Vec<f64> = regions
        .iter()
        .filter(|r| matches!(r.disposition, RegionDisposition::Vector))
        .flat_map(|r| r.units.iter())
        .filter_map(|&ui| {
            let sid = plan.owned[ui].unit.symbol_id.clone();
            if reconstruction.repaired_symbols.contains(&sid)
                || reconstruction.reused_symbols.contains(&sid)
            {
                return None;
            }
            measured.iter().find(|(k, _)| *k == sid).map(|(_, v)| *v)
        })
        .collect();
    unit_ious.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    preservation_ious.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let vector_units = unit_ious.len();
    let raster_ink_px = coverage.text_ink_px_raster + coverage.other_ink_px;
    let fidelity = Fidelity {
        vector_ink_iou_min: unit_ious.first().copied(),
        vector_ink_iou_mean: if unit_ious.is_empty() {
            None
        } else {
            Some(unit_ious.iter().sum::<f64>() / unit_ious.len() as f64)
        },
        preservation_ink_iou_min: preservation_ious.first().copied(),
        raster_ink_px,
        units_below_policy,
        min_ink_iou: policy.min_ink_iou,
    };
    let _ = vector_units;

    stage_timings_ms.insert(
        "raster_composition_and_owners".into(),
        composition_started.elapsed().as_millis(),
    );
    let report = Report {
        segmentation_method: "global_corner_paper".into(),
        stage_timings_ms,
        candidates: Vec::new(),
        fidelity,
        reconstruction,
        selected: "reconstruct".into(),
        glyph_stats,
        patches: patch_records,
        occurrences: occ_records,
        page_id: input.page_id.clone(),
        policy: policy.clone(),
        supplied_chars: input.spans.iter().map(|s| s.text.chars().count()).sum(),
        components_total: plan.components_total,
        components_owned: plan.components_owned,
        components_artwork: plan.components_artwork,
        visual_units: plan.owned.len(),
        semantic_spans: input.spans.len(),
        regions: regions
            .iter()
            .map(|r| RegionRecord {
                id: r.id,
                kind: r.kind.clone(),
                units: r.units.len(),
                bbox_px: r.bbox_px,
                disposition: r.disposition.clone(),
            })
            .collect(),
        coverage,
        raster_ink_pixels_suppressed,
        antialias_fringe_pixels_suppressed,
        fallback_reasons,
        font_glyphs: parts.shapes.len() + 1,
        font_bytes: 0,
        pdf_bytes: 0,
        raster_bytes,
        semantic_owner,
        ownership_invariants: invariants,
        elapsed_ms: start.elapsed().as_millis(),
    };

    Ok((parts, report))
}

/// Source-pixel patches for non-text artwork (never dropped, never relabelled).
/// Merge overlapping or exactly-adjacent patches transitively (deterministic:
/// creation order is the merge order). Each merged patch is re-copied from the
/// source raster, so source fidelity is exact for every merged rect.
fn coalesce_patches(input: &Input, patches: Vec<Patch>) -> Vec<Patch> {
    coalesce_patches_rgb(
        &input.rgb,
        input.width as usize,
        input.height as usize,
        patches,
    )
}

fn coalesce_patches_rgb(
    source_rgb: &[u8],
    w: usize,
    h: usize,
    mut patches: Vec<Patch>,
) -> Vec<Patch> {
    fn merges(a: [f64; 4], b: [f64; 4]) -> bool {
        // overlapping OR touching (gap == 0)
        a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3]
    }
    let mut out: Vec<Patch> = Vec::with_capacity(patches.len());
    while !patches.is_empty() {
        let mut base = patches.swap_remove(0);
        let mut changed = true;
        while changed {
            changed = false;
            let mut i = 0;
            while i < patches.len() {
                if merges(base.bbox_px, patches[i].bbox_px) {
                    let union = [
                        base.bbox_px[0].min(patches[i].bbox_px[0]),
                        base.bbox_px[1].min(patches[i].bbox_px[1]),
                        base.bbox_px[2].max(patches[i].bbox_px[2]),
                        base.bbox_px[3].max(patches[i].bbox_px[3]),
                    ];
                    base = patch_from_rgb(source_rgb, w, h, union);
                    patches.swap_remove(i);
                    changed = true;
                } else {
                    i += 1;
                }
            }
        }
        out.push(base);
    }
    out
}

fn patch_from_rgb(source_rgb: &[u8], w: usize, h: usize, bb: [f64; 4]) -> Patch {
    let x0 = bb[0].max(0.0) as usize;
    let y0 = bb[1].max(0.0) as usize;
    let x1 = ((bb[2] as usize).min(w)).max(x0 + 1);
    let y1 = ((bb[3] as usize).min(h)).max(y0 + 1);
    let (pw, ph) = (x1 - x0, y1 - y0);
    let mut rgb = vec![0u8; pw * ph * 3];
    for yy in 0..ph {
        for xx in 0..pw {
            let si = ((y0 + yy) * w + (x0 + xx)) * 3;
            let di = (yy * pw + xx) * 3;
            rgb[di..di + 3].copy_from_slice(&source_rgb[si..si + 3]);
        }
    }
    Patch {
        compact_background: false,
        bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
        rgb,
        w: pw as u32,
        h: ph as u32,
    }
}

/// Remove scan ink only where an emitted visible vector owns it. The exact
/// segmentation mask is authoritative; a one- or two-pixel antialias fringe is
/// cleared only with local grayscale edge support or a native fallback
/// patch covering the sample. Other OCR/artwork masks protect their pixels. Each
/// cleared sample receives local paper estimated outside all ink and fringes.
fn clean_replaced_text(
    input: &Input,
    plan: &OwnershipPlan,
    vector_owned_symbols: &std::collections::BTreeSet<String>,
    emitted_symbols: &std::collections::BTreeSet<String>,
    reconstruction: &crate::visual_dict::Reconstruction,
    dpi: f64,
    fallback_paper: [u8; 3],
) -> (Vec<u8>, usize, usize, Vec<[f64; 4]>) {
    let mut rgb = input.rgb.clone();
    let w = input.width as usize;
    let h = input.height as usize;
    if rgb.len() != w.saturating_mul(h).saturating_mul(3) {
        return (rgb, 0, 0, Vec::new());
    }
    let mut protected = vec![false; w * h];
    let mut vector_ink = vec![false; w * h];
    for owned in &plan.owned {
        let vector = vector_owned_symbols.contains(&owned.unit.symbol_id);
        for (i, ink) in owned.unit.mask.iter().enumerate() {
            if !*ink {
                continue;
            }
            let x = owned.unit.bbox_px[0].round() as isize + (i % owned.unit.crop_w) as isize;
            let y = owned.unit.bbox_px[1].round() as isize + (i / owned.unit.crop_w) as isize;
            if x < 0 || y < 0 || x >= w as isize || y >= h as isize {
                continue;
            }
            let at = y as usize * w + x as usize;
            if vector {
                vector_ink[at] = true;
            } else {
                protected[at] = true;
            }
        }
    }
    for (unit, _) in &plan.artwork_units {
        for (i, ink) in unit.mask.iter().enumerate() {
            if !*ink {
                continue;
            }
            let x = unit.bbox_px[0].round() as isize + (i % unit.crop_w) as isize;
            let y = unit.bbox_px[1].round() as isize + (i / unit.crop_w) as isize;
            if x >= 0 && y >= 0 && x < w as isize && y < h as isize {
                protected[y as usize * w + x as usize] = true;
            }
        }
    }
    // Caller protection is independent of OCR and segmentation. Use its
    // conservative bounding box both for erasure and for paper sampling.
    for region in &input.protected_regions {
        let x0 = region
            .polygon
            .iter()
            .map(|p| p[0])
            .fold(f64::INFINITY, f64::min)
            .floor()
            .max(0.0) as usize;
        let y0 = region
            .polygon
            .iter()
            .map(|p| p[1])
            .fold(f64::INFINITY, f64::min)
            .floor()
            .max(0.0) as usize;
        let x1 = region
            .polygon
            .iter()
            .map(|p| p[0])
            .fold(f64::NEG_INFINITY, f64::max)
            .ceil()
            .max(0.0) as usize;
        let y1 = region
            .polygon
            .iter()
            .map(|p| p[1])
            .fold(f64::NEG_INFINITY, f64::max)
            .ceil()
            .max(0.0) as usize;
        for y in y0.min(h)..y1.min(h) {
            for x in x0.min(w)..x1.min(w) {
                protected[y * w + x] = true;
            }
        }
    }
    let weak_rules = protect_weak_rules(
        &input.rgb,
        w,
        h,
        dpi,
        fallback_paper,
        &vector_ink,
        &mut protected,
    );
    let mut erase: Vec<bool> = vector_ink
        .iter()
        .zip(&protected)
        .map(|(&vector, &keep)| vector && !keep)
        .collect();
    // Antialias suppression still requires the original independent-donor
    // two-sided coverage agreement. An unrecognized nearby mark must not
    // validate its own removal through the source halo.
    let fringe = if dpi >= 450.0 { 2isize } else { 1isize };
    for owned in &plan.owned {
        let unit = &owned.unit;
        if !vector_owned_symbols.contains(&unit.symbol_id) {
            continue;
        }
        let actual_vector = emitted_symbols.contains(&unit.symbol_id);
        let record = reconstruction
            .occurrences
            .iter()
            .find(|o| o.symbol_id == unit.symbol_id && (o.repaired || o.reused));
        let witness = record
            .and_then(|r| r.prototype_id.as_deref())
            .and_then(|key| {
                reconstruction
                    .prototype_units
                    .get(key.strip_prefix("prototype:").unwrap_or(key))
            });
        // Native fallback patches include the entire fringe. The base can be
        // cleaned there because those exact source samples are painted above it.
        if actual_vector && witness.and_then(|u| u.gray_halo.as_ref()).is_none() {
            continue;
        }
        let target = record
            .and_then(|r| r.replacement_bbox_px)
            .unwrap_or(unit.bbox_px);
        let mut source_ink: Vec<u8> = unit
            .mask
            .iter()
            .enumerate()
            .filter(|(_, ink)| **ink)
            .map(|(i, _)| {
                let at = ((unit.bbox_px[1] as usize + i / unit.crop_w) * w
                    + unit.bbox_px[0] as usize
                    + i % unit.crop_w)
                    * 3;
                ((input.rgb[at] as u16 + input.rgb[at + 1] as u16 + input.rgb[at + 2] as u16) / 3)
                    as u8
            })
            .collect();
        source_ink.sort_unstable();
        let source_dark = source_ink.get(source_ink.len() / 20).copied().unwrap_or(0) as f64;
        let paper = fallback_paper.iter().map(|&v| v as f64).sum::<f64>() / 3.0;
        let witness_levels = witness.and_then(|u| {
            let halo = u.gray_halo.as_ref()?;
            let gray = u.gray_samples.as_ref()?;
            let mut ink: Vec<u8> = gray
                .iter()
                .zip(&u.mask)
                .filter_map(|(&g, &m)| m.then_some(g))
                .collect();
            if ink.is_empty() {
                return None;
            }
            ink.sort_unstable();
            let mut paper = halo.clone();
            paper.sort_unstable();
            Some((
                ink[ink.len() / 20] as f64,
                paper[paper.len() * 19 / 20] as f64,
            ))
        });
        // Register the independent donor's soft edge to the observed ink.
        // Only owned source pixels fit this small translation; an unknown
        // outside mark cannot serve as evidence for erasing itself.
        let mut shift = (0.0, 0.0);
        if let (Some(donor), Some((dark, light))) = (witness, witness_levels) {
            let mut best = f64::INFINITY;
            let stride = unit.mask.len().div_ceil(256).max(1);
            for sy in [-1.0, -0.5, 0.0, 0.5, 1.0] {
                for sx in [-1.0, -0.5, 0.0, 0.5, 1.0] {
                    let mut loss = 0.0;
                    let mut n = 0;
                    for i in (0..unit.mask.len()).step_by(stride) {
                        if !unit.mask[i] {
                            continue;
                        }
                        let x = unit.bbox_px[0] + (i % unit.crop_w) as f64 + 0.5;
                        let y = unit.bbox_px[1] + (i / unit.crop_w) as f64 + 0.5;
                        let at = ((y.floor() as usize) * w + x.floor() as usize) * 3;
                        let observed = (paper
                            - (input.rgb[at] as f64
                                + input.rgb[at + 1] as f64
                                + input.rgb[at + 2] as f64)
                                / 3.0)
                            / (paper - source_dark).max(1.0);
                        let value = donor_edge_coverage(donor, target, x + sx, y + sy, dark, light);
                        loss += (observed - value).powi(2).min(0.04);
                        n += 1;
                    }
                    // Prefer the zero-phase solution on equally supported fits.
                    let cost = loss / (n as f64).max(1.0) + 1e-6 * (sx * sx + sy * sy);
                    if cost < best {
                        best = cost;
                        shift = (sx, sy);
                    }
                }
            }
        }
        for (i, &ink) in unit.mask.iter().enumerate() {
            if !ink {
                continue;
            }
            let x = unit.bbox_px[0] as isize + (i % unit.crop_w) as isize;
            let y = unit.bbox_px[1] as isize + (i / unit.crop_w) as isize;
            for dy in -fringe..=fringe {
                for dx in -fringe..=fringe {
                    let (nx, ny) = (x + dx, y + dy);
                    if nx < 0 || ny < 0 || nx >= w as isize || ny >= h as isize {
                        continue;
                    }
                    let at = ny as usize * w + nx as usize;
                    if erase[at] || protected[at] {
                        continue;
                    }
                    if !actual_vector {
                        erase[at] = true;
                        continue;
                    }
                    let Some(donor) = witness else {
                        continue;
                    };
                    let Some((dark, light)) = witness_levels else {
                        continue;
                    };
                    let expected = donor_edge_coverage(
                        donor,
                        target,
                        nx as f64 + 0.5 + shift.0,
                        ny as f64 + 0.5 + shift.1,
                        dark,
                        light,
                    );
                    let p = at * 3;
                    let observed = (paper
                        - (input.rgb[p] as f64
                            + input.rgb[p + 1] as f64
                            + input.rgb[p + 2] as f64)
                            / 3.0)
                        / (paper - source_dark).max(1.0);
                    let edge_agreement =
                        (0.005..=0.50).contains(&expected) && (observed - expected).abs() <= 0.08;
                    // Bright dropout samples inside a strongly supported donor
                    // stroke are obsolete impressions too. They must not be
                    // treated as paper merely because binarization omitted them.
                    // Unlike a neighbourhood maximum, the registered donor
                    // centre must itself support this interior classification.
                    let supported_interior = expected >= 0.75 && (0.005..=0.50).contains(&observed);
                    // Registration and differing scanner phases leave a
                    // half-source-pixel edge uncertainty. Require corroboration
                    // at three subpixel donor positions, never the target halo
                    // itself or a single darkest neighbouring source sample.
                    let mut support = 0;
                    if (0.005..=0.50).contains(&observed) {
                        for dy in [-0.5, 0.0, 0.5] {
                            for dx in [-0.5, 0.0, 0.5] {
                                let coverage = donor_edge_coverage(
                                    donor,
                                    target,
                                    nx as f64 + 0.5 + shift.0 + dx,
                                    ny as f64 + 0.5 + shift.1 + dy,
                                    dark,
                                    light,
                                );
                                if coverage >= 0.05 && coverage >= observed - 0.08 {
                                    support += 1;
                                }
                            }
                        }
                    }
                    if edge_agreement || supported_interior || support >= 3 {
                        erase[at] = true;
                    }
                }
            }
        }
    }
    let original = input.rgb.as_slice();
    let raster_ink_pixels_suppressed = vector_ink
        .iter()
        .zip(&protected)
        .filter(|(ink, keep)| **ink && !**keep)
        .count();
    let antialias_fringe_pixels_suppressed = erase
        .iter()
        .zip(&vector_ink)
        .filter(|(erased, ink)| **erased && !**ink)
        .count();
    // A paper estimate must not sample the same unresolved edge it replaces.
    // Exclude the full source-ink neighbourhood, including protected content,
    // before taking a local robust colour estimate. This preserves coloured
    // paper and broad illumination instead of copying gray fringe into cores.
    let radius = if dpi >= 450.0 { 12usize } else { 8usize };
    let sample_guard =
        dilated_ink_guard(&vector_ink, &protected, w, h, fringe as usize + 1, radius);
    let radius = radius as isize;
    for index in 0..erase.len() {
        if !erase[index] {
            continue;
        }
        let (x, y) = ((index % w) as isize, (index / w) as isize);
        // Bounded 25x25 neighbourhood; no per-sample heap allocation.
        let mut samples = [[0u8; 625]; 3];
        let mut sample_count = 0usize;
        for dy in -radius..=radius {
            for dx in -radius..=radius {
                if dx.abs().max(dy.abs()) < 2 {
                    continue;
                }
                let nx = x + dx;
                let ny = y + dy;
                if nx < 0 || ny < 0 || nx >= w as isize || ny >= h as isize {
                    continue;
                }
                let ni = ny as usize * w + nx as usize;
                if sample_guard[ni] || erase[ni] {
                    continue;
                }
                let p = ni * 3;
                let luma = (0.2126 * original[p] as f64
                    + 0.7152 * original[p + 1] as f64
                    + 0.0722 * original[p + 2] as f64) as u8;
                if luma < 96 {
                    continue;
                }
                for c in 0..3 {
                    samples[c][sample_count] = original[p + c];
                }
                sample_count += 1;
            }
        }
        let p = index * 3;
        for c in 0..3 {
            if sample_count > 0 {
                samples[c][..sample_count].sort_unstable();
                rgb[p + c] = samples[c][sample_count / 2];
            } else {
                rgb[p + c] = fallback_paper[c];
            }
        }
    }
    (
        rgb,
        raster_ink_pixels_suppressed,
        antialias_fringe_pixels_suppressed,
        weak_rules,
    )
}

/// Preserve coherent faint rules independently of OCR segmentation. Weak
/// ridge segments can connect through dark glyph cores, but only weak samples
/// gain protection. Return native strips so reduction cannot attenuate them.
fn protect_weak_rules(
    rgb: &[u8],
    w: usize,
    h: usize,
    dpi: f64,
    paper: [u8; 3],
    _ink: &[bool],
    protected: &mut [bool],
) -> Vec<[f64; 4]> {
    let scale = (dpi / 300.0).round().max(1.0) as usize;
    let offset = 2 * scale;
    let minimum = 8 * scale;
    let max_gap = 4 * scale;
    let light = paper.iter().map(|&v| v as u16).sum::<u16>() / 3;
    let lum: Vec<u16> = rgb
        .as_chunks::<3>().0.iter()
        .map(|p| (p[0] as u16 + p[1] as u16 + p[2] as u16) / 3)
        .collect();
    let weak = |at: usize| lum[at] >= light.saturating_sub(32) && lum[at] + 3 <= light;
    let mut boxes = Vec::new();
    for vertical in [false, true] {
        let (lines, length) = if vertical { (w, h) } else { (h, w) };
        for fixed in offset..lines.saturating_sub(offset) {
            let at = |v: usize| {
                if vertical {
                    v * w + fixed
                } else {
                    fixed * w + v
                }
            };
            let mut start = None;
            let mut support = 0;
            let mut gap = 0;
            let mut last = 0;
            for v in 0..=length {
                let connected = v < length && lum[at(v)] + 3 <= light;
                if connected {
                    if start.is_none() {
                        start = Some(v);
                    }
                    let i = at(v);
                    let delta = if vertical { offset } else { offset * w };
                    let ridge = weak(i) && lum[i] + 3 <= (lum[i - delta] + lum[i + delta]) / 2;
                    if ridge {
                        support += 1;
                        gap = 0;
                        last = v + 1;
                    } else if weak(i) {
                        gap += 1;
                    }
                }
                if !connected || gap > max_gap {
                    if let Some(begin) = start.take() {
                        if support >= minimum {
                            for u in begin..last {
                                if weak(at(u)) {
                                    protected[at(u)] = true;
                                }
                            }
                            boxes.push(if vertical {
                                [fixed as f64, begin as f64, (fixed + 1) as f64, last as f64]
                            } else {
                                [begin as f64, fixed as f64, last as f64, (fixed + 1) as f64]
                            });
                        }
                    }
                    support = 0;
                    gap = 0;
                    last = 0;
                }
            }
        }
    }
    boxes
}

/// Bilinear grayscale coverage in a donor's pixel-centre frame, including
/// its retained two-pixel halo. No observed outside pixel enters this model.
fn donor_edge_coverage(
    donor: &crate::units::Unit,
    target: [f64; 4],
    x: f64,
    y: f64,
    dark: f64,
    light: f64,
) -> f64 {
    let Some(halo) = donor.gray_halo.as_ref() else {
        return 0.0;
    };
    let xx = (x - target[0]) / (target[2] - target[0]) * donor.crop_w as f64 + 1.5;
    let yy = (y - target[1]) / (target[3] - target[1]) * donor.crop_h as f64 + 1.5;
    let sample = |x: isize, y: isize| {
        if x < 0 || y < 0 || x >= donor.crop_w as isize + 4 || y >= donor.crop_h as isize + 4 {
            light
        } else {
            halo[y as usize * (donor.crop_w + 4) + x as usize] as f64
        }
    };
    let (ix, iy) = (xx.floor() as isize, yy.floor() as isize);
    let (fx, fy) = (xx - xx.floor(), yy - yy.floor());
    let value = (sample(ix, iy) * (1.0 - fx) + sample(ix + 1, iy) * fx) * (1.0 - fy)
        + (sample(ix, iy + 1) * (1.0 - fx) + sample(ix + 1, iy + 1) * fx) * fy;
    ((light - value) / (light - dark).max(1.0)).clamp(0.0, 1.0)
}

/// Separable bounded box dilation. Protect artwork over the entire paper
/// sampling radius without quadratic work per artwork/source pixel.
fn dilated_ink_guard(
    ink: &[bool],
    protected: &[bool],
    w: usize,
    h: usize,
    ink_radius: usize,
    protected_radius: usize,
) -> Vec<bool> {
    fn dilate(mask: &[bool], w: usize, h: usize, r: usize) -> Vec<bool> {
        let mut horizontal = vec![false; w * h];
        for y in 0..h {
            let mut sum = 0usize;
            for x in 0..w + r {
                if x < w {
                    sum += usize::from(mask[y * w + x]);
                }
                if x > 2 * r && x - 2 * r - 1 < w {
                    sum -= usize::from(mask[y * w + x - 2 * r - 1]);
                }
                if x >= r {
                    let xx = x - r;
                    if xx < w {
                        horizontal[y * w + xx] = sum > 0;
                    }
                }
            }
        }
        let mut out = vec![false; w * h];
        for x in 0..w {
            let mut sum = 0usize;
            for y in 0..h + r {
                if y < h {
                    sum += usize::from(horizontal[y * w + x]);
                }
                if y > 2 * r && y - 2 * r - 1 < h {
                    sum -= usize::from(horizontal[(y - 2 * r - 1) * w + x]);
                }
                if y >= r {
                    let yy = y - r;
                    if yy < h {
                        out[yy * w + x] = sum > 0;
                    }
                }
            }
        }
        out
    }
    let mut guard = dilate(ink, w, h, ink_radius);
    for (g, p) in guard
        .iter_mut()
        .zip(dilate(protected, w, h, protected_radius))
    {
        *g |= p;
    }
    guard
}

/// The low-resolution base retains paper tone and broad scan variation after
/// replaced source ink has been removed. Native-resolution fallback and
/// artwork patches are painted above it.
fn downsampled_background_patch(source_rgb: &[u8], w: u32, h: u32, dpi: f64) -> Patch {
    let target_dpi = dpi.clamp(72.0, 150.0);
    let scale = target_dpi / dpi.max(1.0);
    let bw = ((w as f64 * scale).round() as u32).max(1);
    let bh = ((h as f64 * scale).round() as u32).max(1);
    let source = image::RgbImage::from_raw(w, h, source_rgb.to_vec())
        .expect("input raster dimensions were validated before ClearScan assembly");
    let reduced = image::imageops::resize(&source, bw, bh, image::imageops::FilterType::Lanczos3);
    Patch {
        compact_background: true,
        bbox_px: [0.0, 0.0, w as f64, h as f64],
        rgb: reduced.into_raw(),
        w: bw,
        h: bh,
    }
}

/// Reduce only an already cleaned paper layer. Every exposed channel sample
/// remains within three levels of the 150-DPI representation or receives a
/// cleaned-source native exception tile. The candidate mean error is at most
/// 0.5 and exception tiles cover at most 5% of the page. Native patch borders
/// remain tested. This does not classify unknown content as disposable paper.
/// The residual-detail pass still examines the original cleaned source after
/// choosing this representation and restores coherent fine marks natively.
fn compact_paper_background(
    base: Patch,
    w: u32,
    h: u32,
    native: &[Patch],
) -> (Patch, Vec<[f64; 4]>) {
    let image = image::RgbImage::from_raw(base.w, base.h, base.rgb.clone()).unwrap();
    let mut covered = vec![false; (base.w * base.h) as usize];
    for p in native {
        // Ignore only samples fully inside an opaque native patch. Keep one
        // reduced pixel at the boundary to constrain interpolation there.
        let x0 = (p.bbox_px[0] * base.w as f64 / w as f64).ceil() as usize + 1;
        let y0 = (p.bbox_px[1] * base.h as f64 / h as f64).ceil() as usize + 1;
        let x1 = (p.bbox_px[2] * base.w as f64 / w as f64).floor() as usize;
        let y1 = (p.bbox_px[3] * base.h as f64 / h as f64).floor() as usize;
        for y in y0..y1.saturating_sub(1).min(base.h as usize) {
            for x in x0..x1.saturating_sub(1).min(base.w as usize) {
                covered[y * base.w as usize + x] = true;
            }
        }
    }
    let bw = base.w.div_ceil(2);
    let bh = base.h.div_ceil(2);
    let small = image::imageops::resize(&image, bw, bh, image::imageops::FilterType::Lanczos3);
    let restored = image::imageops::resize(
        &small,
        base.w,
        base.h,
        image::imageops::FilterType::Lanczos3,
    );
    let mut error = 0u64;
    let mut count = 0u64;
    let mut exceptions = std::collections::BTreeSet::new();
    // Four reduced samples per exception tile: unlike artwork buckets, small
    // paper residuals must not inflate into 32px rectangles around whole words.
    let cell = (4 * w).div_ceil(base.w).max(4);
    for (i, (a, b)) in base
        .rgb
        .as_chunks::<3>().0.iter()
        .zip(restored.as_raw().as_chunks::<3>().0.iter())
        .enumerate()
    {
        if covered[i] {
            continue;
        }
        let mut max = 0;
        for c in 0..3 {
            let d = a[c].abs_diff(b[c]);
            max = max.max(d);
            error += d as u64;
            count += 1;
        }
        if max > 3 {
            // Keep source-exact native tiles for exceptional samples instead
            // of allowing one faint mark to force an entire noisy page native.
            // Include a reduced pixel of margin for image interpolation.
            let x = (i % base.w as usize) as u32;
            let y = (i / base.w as usize) as u32;
            let x0 = x.saturating_sub(1) * w / base.w;
            let y0 = y.saturating_sub(1) * h / base.h;
            let x1 = ((x + 2) * w).div_ceil(base.w).min(w);
            let y1 = ((y + 2) * h).div_ceil(base.h).min(h);
            for ty in y0 / cell..y1.div_ceil(cell) {
                for tx in x0 / cell..x1.div_ceil(cell) {
                    exceptions.insert((tx, ty));
                }
            }
        }
    }
    let area: u64 = exceptions
        .iter()
        .map(|&(x, y)| (cell.min(w - x * cell) as u64) * (cell.min(h - y * cell) as u64))
        .sum();
    // This is a sparse paper-resource correction, not general page separation.
    if count == 0 || error as f64 > count as f64 * 0.50 || area > w as u64 * h as u64 / 20 {
        return (base, Vec::new());
    }
    let boxes = exceptions
        .into_iter()
        .map(|(x, y)| {
            [
                (x * cell) as f64,
                (y * cell) as f64,
                ((x * cell + cell).min(w)) as f64,
                ((y * cell + cell).min(h)) as f64,
            ]
        })
        .collect();
    (
        Patch {
            rgb: small.into_raw(),
            w: bw,
            h: bh,
            ..base
        },
        boxes,
    )
}

/// Preserve source detail that the reduced layer cannot represent. This is a
/// conservative local residual check, not a foreground/meaning classifier.
/// Existing native patches are excluded; returned tiles always use cleaned
/// source samples. Dense residuals naturally coalesce to a native page.
fn residual_detail_patches(
    source: &[u8],
    w: u32,
    h: u32,
    reduced: &Patch,
    native: &[Patch],
) -> Vec<Patch> {
    let mut covered = vec![false; w as usize * h as usize];
    for patch in native {
        let [x0, y0, x1, y1] = patch.bbox_px;
        for y in y0.max(0.0) as usize..(y1 as usize).min(h as usize) {
            for x in x0.max(0.0) as usize..(x1 as usize).min(w as usize) {
                covered[y * w as usize + x] = true;
            }
        }
    }
    let small = image::RgbImage::from_raw(reduced.w, reduced.h, reduced.rgb.clone()).unwrap();
    let restored = image::imageops::resize(&small, w, h, image::imageops::FilterType::Lanczos3);
    let samples = restored.as_raw();
    // Discover complete source-supported ridges before assigning 32px storage
    // tiles. A tile seam must never truncate the evidence for a thin mark.
    let luma = |x: usize, y: usize| -> u16 {
        let i = (y * w as usize + x) * 3;
        (source[i] as u16 + source[i + 1] as u16 + source[i + 2] as u16) / 3
    };
    let residual = |x: usize, y: usize| {
        let i = y * w as usize + x;
        (0..3).any(|c| samples[3 * i + c].saturating_sub(source[3 * i + c]) >= 2)
    };
    let mut tiles = std::collections::BTreeSet::new();
    for y in 2..(h as usize).saturating_sub(2) {
        let mut run = 0;
        for x in 0..w as usize {
            run = if residual(x, y) && luma(x, y) + 3 <= (luma(x, y - 2) + luma(x, y + 2)) / 2 {
                run + 1
            } else {
                0
            };
            if run == 8 {
                for xx in x + 1 - 8..=x {
                    if !covered[y * w as usize + xx] {
                        tiles.insert((xx / 32, y / 32));
                    }
                }
            } else if run > 8 && !covered[y * w as usize + x] {
                tiles.insert((x / 32, y / 32));
            }
        }
    }
    for x in 2..(w as usize).saturating_sub(2) {
        let mut run = 0;
        for y in 0..h as usize {
            run = if residual(x, y) && luma(x, y) + 3 <= (luma(x - 2, y) + luma(x + 2, y)) / 2 {
                run + 1
            } else {
                0
            };
            if run == 8 {
                for yy in y + 1 - 8..=y {
                    if !covered[yy * w as usize + x] {
                        tiles.insert((x / 32, yy / 32));
                    }
                }
            } else if run > 8 && !covered[y * w as usize + x] {
                tiles.insert((x / 32, y / 32));
            }
        }
    }
    let mut out = Vec::new();
    for (cx, cy) in tiles {
        let x0 = cx * 32;
        let y0 = cy * 32;
        out.push(patch_from_rgb(
            source,
            w as usize,
            h as usize,
            [
                x0 as f64,
                y0 as f64,
                (x0 + 32).min(w as usize) as f64,
                (y0 + 32).min(h as usize) as f64,
            ],
        ));
    }
    out
}

fn artwork_patches(source_rgb: &[u8], w: usize, h: usize, plan: &OwnershipPlan) -> Vec<Patch> {
    const CELL: usize = 32;
    let mut cells: std::collections::BTreeMap<(usize, usize), Vec<(usize, usize)>> =
        std::collections::BTreeMap::new();
    for (au, _) in &plan.artwork_units {
        for (i, ink) in au.mask.iter().enumerate() {
            if !*ink {
                continue;
            }
            let gx = au.bbox_px[0] as usize + (i % au.crop_w);
            let gy = au.bbox_px[1] as usize + (i / au.crop_w);
            cells
                .entry((gx / CELL, gy / CELL))
                .or_default()
                .push((gx, gy));
        }
    }
    let mut patches = Vec::new();
    for ((cx, cy), pixels) in cells {
        let (bx, by) = (cx * CELL, cy * CELL);
        let bw = CELL.min(w.saturating_sub(bx));
        let bh = CELL.min(h.saturating_sub(by));
        if bw == 0 || bh == 0 {
            continue;
        }
        // Copy the full source bucket, except exact thresholded ink owned by a
        // glyph that is actually emitted as vector. Those samples are replaced
        // with the measured page paper color; antialias fringe stays raster.
        let mut rgb = vec![0u8; bw * bh * 3];
        for gy in by..by + bh {
            let si = gy * w + bx;
            let di = (gy - by) * bw;
            rgb[di * 3..di * 3 + bw * 3].copy_from_slice(&source_rgb[si * 3..si * 3 + bw * 3]);
        }
        let _ = pixels;
        patches.push(Patch {
            compact_background: false,
            bbox_px: [bx as f64, by as f64, (bx + bw) as f64, (by + bh) as f64],
            rgb,
            w: bw as u32,
            h: bh as u32,
        });
    }
    patches
}

/// The one-page B0 candidate: the canonical source raster page plus the
/// invisible per-glyph ToUnicode owner layer (the "restore everything as
/// raster, keep text searchable" candidate the harness compares against).
pub fn baseline_one_page(
    parts: &crate::page_pdf::PageParts,
    policy: &Policy,
) -> Result<Vec<u8>, String> {
    // the raster baseline keeps EVERY span's searchable text (visible glyph
    // runs for vector spans, owner overlays for fallback spans), drawn
    // invisibly over one whole-page source patch — the accepted M0-Q B0 shape
    let encodings = parts.encodings.clone();
    let font = build_font(&parts.shapes, &encodings, policy.upem)?;
    let patch = whole_page_patch(parts, parts.source_w, parts.source_h)?;
    let baseline = crate::page_pdf::PageParts {
        raster_baseline: true,
        patches: vec![patch],
        ..parts.clone()
    };
    let doc = vec![baseline];
    let (bytes, _stats) =
        crate::page_pdf::assemble_document(&doc, &parts.shapes, &encodings, &font)?;
    Ok(bytes)
}

/// One exact source patch covering the whole canonical raster (the raster
/// baseline candidate's pixels: byte-identical to the source page).
pub fn whole_page_patch(
    parts: &crate::page_pdf::PageParts,
    _w_px: usize,
    _h_px: usize,
) -> Result<crate::page_pdf::Patch, String> {
    let (w, h) = (parts.source_w, parts.source_h);
    if w == 0 || h == 0 || parts.source_rgb.len() != w * h * 3 {
        return Err("source raster missing from page parts".into());
    }
    Ok(crate::page_pdf::Patch {
        compact_background: false,
        bbox_px: [0.0, 0.0, w as f64, h as f64],
        rgb: parts.source_rgb.clone(),
        w: w as u32,
        h: h as u32,
    })
}

#[cfg(test)]
mod dpi_tests {
    use super::clearscan_source_dpi;

    #[test]
    fn derives_dpi_from_authoritative_page_affine() {
        assert!(
            (clearscan_source_dpi([0.24, 0.0, 0.0, -0.24, 0.0, 216.0], "p300").unwrap() - 300.0)
                .abs()
                < 1e-9
        );
        assert!(
            (clearscan_source_dpi([0.12, 0.0, 0.0, -0.12, 0.0, 216.0], "p600").unwrap() - 600.0)
                .abs()
                < 1e-9
        );
        // Conservative axis choice avoids claiming more detail than the
        // lower-resolution direction supports.
        assert!(
            (clearscan_source_dpi([0.12, 0.0, 0.0, -0.24, 0.0, 216.0], "anisotropic").unwrap()
                - 300.0)
                .abs()
                < 1e-9
        );
        assert!(clearscan_source_dpi([0.0, 0.0, 0.0, -0.24, 0.0, 216.0], "invalid").is_err());
    }
}

#[cfg(test)]
mod contour_coverage_tests {
    use super::*;

    #[test]
    fn fidelity_uses_covered_area_and_the_pdf_construction_frame() {
        // This rectangle covers 10% of column 0 and 90% of column 1.
        // Only column 1 is foreground at half coverage, even with an offset,
        // anisotropic font construction frame.
        let mut path = kurbo::BezPath::new();
        path.move_to((11.8, 20.0));
        path.line_to((13.8, 20.0));
        path.line_to((13.8, 24.0));
        path.line_to((11.8, 24.0));
        path.close_path();
        let shape = GlyphShape {
            shape_key: "area-regression".into(),
            path,
            num_contours: 1,
            num_points: 4,
            bbox_fu: [11.8, 20.0, 13.8, 24.0],
            ink_span_fu: [6.0, 4.0],
            anchor_bbox_fu: [10.0, 20.0, 16.0, 24.0],
            stages: crate::units::StageMetrics {
                trace_max_px: 0.0,
                trace_p95_px: 0.0,
                curve_max_px: 0.0,
                quant_bound_px: 0.0,
            },
        };
        assert_eq!(
            reconstructed_glyph_ink_iou(&shape, 3, 1, &[false, true, false]),
            1.0
        );
    }

    #[test]
    fn compact_background_retains_a_faint_unowned_line_natively() {
        let (w, h) = (64u32, 64u32);
        let mut rgb = vec![250u8; (w * h * 3) as usize];
        for y in 31..47 {
            for c in 0..3 {
                rgb[(y * 64 + 17) * 3 + c] = 244;
            }
        }
        let background = downsampled_background_patch(&rgb, w, h, 600.0);
        let patches = residual_detail_patches(&rgb, w, h, &background, &[]);
        for y in 31..47 {
            assert!(
                patches.iter().any(|p| p.bbox_px[0] <= 17.0
                    && p.bbox_px[2] > 17.0
                    && p.bbox_px[1] <= y as f64
                    && p.bbox_px[3] > y as f64),
                "line endpoint across a tile seam must survive"
            );
        }
        // Samples inside a retained tile are source exact, not estimated ink.
        for p in patches {
            let x = p.bbox_px[0] as usize;
            let y = p.bbox_px[1] as usize;
            for yy in 0..p.h as usize {
                for xx in 0..p.w as usize {
                    assert_eq!(
                        &p.rgb[(yy * p.w as usize + xx) * 3..(yy * p.w as usize + xx) * 3 + 3],
                        &rgb[((y + yy) * 64 + x + xx) * 3..((y + yy) * 64 + x + xx) * 3 + 3]
                    );
                }
            }
        }
    }

    #[test]
    fn caller_protection_does_not_require_an_ocr_unit() {
        let mut rgb = vec![250u8; 64 * 64 * 3];
        // Even a short mark below the coherent-residual criterion is protected.
        rgb[(20 * 64 + 20) * 3..(20 * 64 + 20) * 3 + 3].fill(247);
        let mut input = Input {
            rgb: rgb.clone(),
            width: 64,
            height: 64,
            page_id: "protected-unknown".into(),
            spans: vec![],
            protected_regions: vec![ProtectedInput {
                id: "faint".into(),
                polygon: vec![[18.0, 18.0], [23.0, 18.0], [23.0, 23.0], [18.0, 23.0]],
                reason: "unknown mark".into(),
            }],
            raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, 15.36],
            pixel_sha256: None,
        };
        let (parts, _) = convert_parts(
            &input,
            &Policy {
                profile: "clearscan".into(),
                ..Policy::default()
            },
        )
        .unwrap();
        assert!(parts.patches.iter().any(|p| !p.compact_background
            && p.bbox_px[0] <= 18.0
            && p.bbox_px[1] <= 18.0
            && p.bbox_px[2] >= 23.0
            && p.bbox_px[3] >= 23.0));
        // OCR polygons may lie in the permitted boundary tolerance sliver.
        // A wholly off-raster protected box must be discarded before copying.
        input.protected_regions[0].polygon =
            vec![[64.25, 18.0], [65.0, 18.0], [65.0, 23.0], [64.25, 23.0]];
        let (parts, _) = convert_parts(
            &input,
            &Policy {
                profile: "clearscan".into(),
                ..Policy::default()
            },
        )
        .unwrap();
        assert!(parts
            .patches
            .iter()
            .all(|p| p.bbox_px[2] <= 64.0 && p.bbox_px[3] <= 64.0));
    }

    #[test]
    fn partially_observed_word_keeps_each_missing_unicode_range_once() {
        let mut rgb = vec![255u8; 64 * 48 * 3];
        for y in 10..30 {
            for x in 20..30 {
                rgb[(y * 64 + x) * 3..(y * 64 + x) * 3 + 3].fill(0);
            }
        }
        let poly = |b: [f64; 4]| vec![[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]];
        let span = SpanInput {
            id: "word".into(),
            text: "aéb".into(),
            separator_after: "".into(),
            polygon: poly([4.0, 8.0, 47.0, 32.0]),
            symbols: vec![
                SymbolInput {
                    id: "a".into(),
                    range: (0, 1),
                    polygon: poly([5.0, 10.0, 15.0, 30.0]),
                },
                SymbolInput {
                    id: "eacute".into(),
                    range: (1, 3),
                    polygon: poly([20.0, 10.0, 30.0, 30.0]),
                },
                SymbolInput {
                    id: "b".into(),
                    range: (3, 4),
                    polygon: poly([35.0, 10.0, 45.0, 30.0]),
                },
            ],
        };
        let input = Input {
            rgb,
            width: 64,
            height: 48,
            page_id: "partial".into(),
            spans: vec![span],
            protected_regions: vec![],
            raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, 11.52],
            pixel_sha256: None,
        };
        let (parts, _) = convert_parts(
            &input,
            &Policy {
                profile: "clearscan".into(),
                ..Policy::default()
            },
        )
        .unwrap();
        assert_eq!(
            parts
                .occurrences
                .iter()
                .map(|o| o.5.as_str())
                .collect::<Vec<_>>(),
            vec!["é"]
        );
        let owner = parts.owners.iter().find(|o| o.span_id == "word").unwrap();
        assert_eq!(
            owner
                .characters
                .iter()
                .map(|ch| parts.encodings[ch.cid as usize - 1].1.as_str())
                .collect::<Vec<_>>(),
            vec!["a", "b"]
        );
        assert_eq!(
            owner
                .characters
                .iter()
                .map(|ch| ch.order)
                .collect::<Vec<_>>(),
            vec![0, 3]
        );
        assert_eq!(owner.visible_order.get("eacute"), Some(&1));
    }

    #[test]
    fn a_source_speck_is_not_a_character_sized_vector() {
        let mut rgb = vec![255u8; 64 * 48 * 3];
        rgb[(20 * 64 + 25) * 3..(20 * 64 + 25) * 3 + 3].fill(0);
        let polygon = vec![[20.0, 10.0], [30.0, 10.0], [30.0, 35.0], [20.0, 35.0]];
        let input = Input {
            rgb,
            width: 64,
            height: 48,
            page_id: "micro".into(),
            spans: vec![SpanInput {
                id: "f".into(),
                text: "f".into(),
                separator_after: "".into(),
                polygon: polygon.clone(),
                symbols: vec![SymbolInput {
                    id: "f-char".into(),
                    range: (0, 1),
                    polygon,
                }],
            }],
            protected_regions: vec![],
            raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, 11.52],
            pixel_sha256: None,
        };
        let (parts, report) = convert_parts(
            &input,
            &Policy {
                profile: "clearscan".into(),
                ..Policy::default()
            },
        )
        .unwrap();
        assert!(parts.occurrences.is_empty());
        assert_eq!(parts.owners[0].characters.len(), 1);
        assert_eq!(report.raster_ink_pixels_suppressed, 0);
        assert!(parts.patches.iter().any(|p| !p.compact_background
            && p.bbox_px[0] <= 25.0
            && p.bbox_px[2] > 25.0
            && p.bbox_px[1] <= 20.0
            && p.bbox_px[3] > 20.0));
    }
    #[test]
    fn paper_reconstruction_excludes_gray_fringe_and_preserves_adjacent_artwork() {
        let paper = [240u8, 220, 190];
        let mut rgb = paper.repeat(64 * 64);
        for y in 20..32 {
            for x in 20..24 {
                rgb[(y * 64 + x) * 3..(y * 64 + x) * 3 + 3].fill(15);
            }
            for x in [19, 24] {
                for c in 0..3 {
                    rgb[(y * 64 + x) * 3 + c] = paper[c] - 12;
                }
            }
        }
        // An independent short faint mark adjacent to a replaced edge.
        for c in 0..3 {
            rgb[(25 * 64 + 19) * 3 + c] = paper[c] - 20;
        }
        // Broad coloured caller-protected material is not necessarily a
        // segmentation/artwork component, and must not become paper evidence.
        for y in 12..42 {
            for x in 27..50 {
                rgb[(y * 64 + x) * 3..(y * 64 + x) * 3 + 3].copy_from_slice(&[110, 170, 200]);
            }
        }
        let input = Input {
            rgb,
            width: 64,
            height: 64,
            page_id: "paper".into(),
            spans: vec![],
            protected_regions: vec![ProtectedInput {
                id: "colour".into(),
                polygon: vec![[27.0, 12.0], [50.0, 12.0], [50.0, 42.0], [27.0, 42.0]],
                reason: "illustration".into(),
            }],
            raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, 15.36],
            pixel_sha256: None,
        };
        let mut unit = crate::units::Unit {
            shape_key: "bar".into(),
            span_id: "bar".into(),
            symbol_id: "bar".into(),
            semantic_text: "I".into(),
            bbox_px: [20.0, 20.0, 24.0, 32.0],
            ocr_bbox_px: [19.0, 19.0, 25.0, 33.0],
            crop_w: 4,
            crop_h: 12,
            mask: vec![true; 48],
            gray_samples: None,
            gray_halo: None,
        };
        unit.retain_grayscale(&input.rgb, 64, 64);
        let mut mark = unit.clone();
        mark.symbol_id = "mark".into();
        mark.bbox_px = [19.0, 25.0, 20.0, 26.0];
        mark.crop_w = 1;
        mark.crop_h = 1;
        mark.mask = vec![true];
        let plan = OwnershipPlan {
            owned: vec![crate::ownership::OwnedUnit {
                unit,
                components: vec![],
                slots: vec![],
                suspect: false,
            }],
            artwork_units: vec![(mark, vec![])],
            ..Default::default()
        };
        let ids = ["bar".to_string()].into_iter().collect();
        let (clean, core, fringe, _) =
            clean_replaced_text(&input, &plan, &ids, &ids, &Default::default(), 300.0, paper);
        assert_eq!(core, 48);
        assert_eq!(
            fringe, 0,
            "a locally traced glyph cannot validate fringe deletion using itself"
        );
        assert_eq!(
            &clean[(22 * 64 + 19) * 3..(22 * 64 + 19) * 3 + 3],
            &input.rgb[(22 * 64 + 19) * 3..(22 * 64 + 19) * 3 + 3]
        );
        assert_eq!(&clean[(22 * 64 + 21) * 3..(22 * 64 + 21) * 3 + 3], &paper);
        assert_eq!(
            &clean[(25 * 64 + 19) * 3..(25 * 64 + 19) * 3 + 3],
            &input.rgb[(25 * 64 + 19) * 3..(25 * 64 + 19) * 3 + 3]
        );
        let empty = std::collections::BTreeSet::new();
        let (unchanged, _, _, _) = clean_replaced_text(
            &input,
            &plan,
            &empty,
            &empty,
            &Default::default(),
            300.0,
            paper,
        );
        assert_eq!(
            unchanged, input.rgb,
            "no emitted vector must mean no suppression"
        );
        let mut overlap = input.clone();
        overlap.protected_regions.push(ProtectedInput {
            id: "overlap".into(),
            polygon: vec![[20.0, 20.0], [22.0, 20.0], [22.0, 22.0], [20.0, 22.0]],
            reason: "unknown".into(),
        });
        let (kept, _, _, _) = clean_replaced_text(
            &overlap,
            &plan,
            &ids,
            &ids,
            &Default::default(),
            300.0,
            paper,
        );
        assert_eq!(
            &kept[(20 * 64 + 20) * 3..(20 * 64 + 20) * 3 + 3],
            &input.rgb[(20 * 64 + 20) * 3..(20 * 64 + 20) * 3 + 3]
        );
        // An independent intact donor supports a bright source dropout inside
        // the stroke. A disconnected counter/neighbor sample has no such ink
        // support and must not become an erasure rectangle.
        let mut faded = input.clone();
        let mut faded_plan = plan.clone();
        let hole = 5 * 4 + 1;
        faded_plan.owned[0].unit.mask[hole] = false;
        for c in 0..3 {
            faded.rgb[(25 * 64 + 21) * 3 + c] = paper[c] - 20;
        }
        let mut reconstruction = crate::visual_dict::Reconstruction::default();
        reconstruction
            .prototype_units
            .insert("donor".into(), plan.owned[0].unit.clone());
        reconstruction
            .occurrences
            .push(crate::visual_dict::GlyphOccurrence {
                symbol_id: "bar".into(),
                text: "I".into(),
                source_shape_key: "source".into(),
                prototype_id: Some("prototype:donor".into()),
                similarity: Some(0.99),
                source_mask_iou: None,
                replacement_bbox_px: Some([20.0, 20.0, 24.0, 32.0]),
                prototype_trace_iou: None,
                repaired: true,
                reused: false,
                restoration_evidence_passed: true,
                decision: "test".into(),
            });
        let (filled, _, _, _) = clean_replaced_text(
            &faded,
            &faded_plan,
            &ids,
            &ids,
            &reconstruction,
            300.0,
            paper,
        );
        assert_eq!(&filled[(25 * 64 + 21) * 3..(25 * 64 + 21) * 3 + 3], &paper);
        faded.protected_regions.push(ProtectedInput {
            id: "faint crossing mark".into(),
            polygon: vec![[21.0, 25.0], [22.0, 25.0], [22.0, 26.0], [21.0, 26.0]],
            reason: "unknown".into(),
        });
        let (retained, _, _, _) = clean_replaced_text(
            &faded,
            &faded_plan,
            &ids,
            &ids,
            &reconstruction,
            300.0,
            paper,
        );
        assert_eq!(
            &retained[(25 * 64 + 21) * 3..(25 * 64 + 21) * 3 + 3],
            &faded.rgb[(25 * 64 + 21) * 3..(25 * 64 + 21) * 3 + 3]
        );
    }

    #[test]
    fn compact_paper_reduction_is_bounded_and_does_not_whiten_colour() {
        let make = |rgb| Patch {
            compact_background: true,
            bbox_px: [0.0, 0.0, 128.0, 128.0],
            rgb,
            w: 64,
            h: 64,
        };
        let tone = [230u8, 210, 180];
        let (reduced, exceptions) =
            compact_paper_background(make(tone.repeat(64 * 64)), 128, 128, &[]);
        assert!(exceptions.is_empty());
        assert_eq!((reduced.w, reduced.h), (32, 32));
        assert!(reduced.rgb.chunks_exact(3).all(|p| p == tone));
        let mut detail = tone.repeat(64 * 64);
        for y in 8..56 {
            detail[(y * 64 + 23) * 3..(y * 64 + 23) * 3 + 3].fill(180);
        }
        let original = make(detail.clone());
        let (kept, _) = compact_paper_background(original, 128, 128, &[]);
        assert_eq!((kept.w, kept.h), (64, 64));
        assert_eq!(kept.rgb, detail);
    }
    #[test]
    fn paper_sampling_guard_matches_bounded_neighbourhoods() {
        let (w, h) = (7usize, 5usize);
        let mut ink = vec![false; w * h];
        ink[0] = true;
        ink[3 * w + 4] = true;
        let mut protected = vec![false; w * h];
        protected[2 * w + 3] = true;
        for r in [0usize, 1, 3, 12] {
            let guard = dilated_ink_guard(&ink, &protected, w, h, 1, r);
            for y in 0..h {
                for x in 0..w {
                    let expected = (0..h).any(|yy| {
                        (0..w).any(|xx| {
                            (ink[yy * w + xx] && x.abs_diff(xx) <= 1 && y.abs_diff(yy) <= 1)
                                || (protected[yy * w + xx]
                                    && x.abs_diff(xx) <= r
                                    && y.abs_diff(yy) <= r)
                        })
                    });
                    assert_eq!(guard[y * w + x], expected, "at {x},{y} radius {r}");
                }
            }
        }
    }
    #[test]
    fn weak_crossing_rule_survives_without_retaining_dark_glyph_cores() {
        for scale in [1usize, 2] {
            let (w, h) = (64 * scale, 48 * scale);
            let mut rgb = vec![250u8; w * h * 3];
            let mut ink = vec![false; w * h];
            for y in 15 * scale..35 * scale {
                for x in 24 * scale..28 * scale {
                    rgb[(y * w + x) * 3..(y * w + x) * 3 + 3].fill(15);
                    ink[y * w + x] = true;
                }
            }
            for y in 25 * scale..26 * scale {
                for x in 4 * scale..50 * scale {
                    if !ink[y * w + x] {
                        rgb[(y * w + x) * 3..(y * w + x) * 3 + 3].fill(244);
                    }
                }
            }
            rgb[(12 * scale * w + 52 * scale) * 3..(12 * scale * w + 52 * scale) * 3 + 3].fill(244);
            let mut protected = vec![false; w * h];
            protect_weak_rules(
                &rgb,
                w,
                h,
                300.0 * scale as f64,
                [250; 3],
                &ink,
                &mut protected,
            );
            for y in 25 * scale..26 * scale {
                for x in 4 * scale..50 * scale {
                    assert_eq!(
                        protected[y * w + x],
                        !ink[y * w + x],
                        "rule at {x},{y}, scale {scale}"
                    );
                }
            }
            assert!(
                !protected[12 * scale * w + 52 * scale],
                "isolated sample is not a coherent rule"
            );
        }
    }
    #[test]
    fn weak_vertical_rule_requires_physical_support() {
        let (w, h) = (24usize, 24usize);
        let mut rgb = vec![250u8; w * h * 3];
        for y in 2..22 {
            rgb[(y * w + 10) * 3..(y * w + 10) * 3 + 3].fill(244);
        }
        let ink = vec![false; w * h];
        let mut kept = vec![false; w * h];
        let boxes = protect_weak_rules(&rgb, w, h, 300.0, [250; 3], &ink, &mut kept);
        assert_eq!(boxes, vec![[10.0, 2.0, 11.0, 22.0]]);
        assert_eq!(kept.iter().filter(|&&b| b).count(), 20);
        let mut short = vec![250u8; w * h * 3];
        for y in 3..10 {
            short[(y * w + 10) * 3..(y * w + 10) * 3 + 3].fill(244);
        }
        let mut untouched = vec![false; w * h];
        assert!(protect_weak_rules(&short, w, h, 300.0, [250; 3], &ink, &mut untouched).is_empty());
        assert!(untouched.iter().all(|&b| !b));
    }
}
