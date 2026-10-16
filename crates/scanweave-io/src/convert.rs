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
use crate::page_pdf::{Owner, Patch};
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
    pub fallback_reasons: BTreeMap<String, usize>,
    pub font_glyphs: usize,
    pub font_bytes: usize,
    pub pdf_bytes: usize,
    pub raster_bytes: usize,
    pub semantic_owner: BTreeMap<String, String>,
    pub ownership_invariants: BTreeMap<String, bool>,
    #[serde(skip_serializing)]
    pub elapsed_ms: u128,
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
            raster_to_page_pt: [72.0 / 300.0, 0.0, 0.0, -72.0 / 300.0, 0.0, pt(input.height as f64)],
        },
        source_geometry: None,
        producer: Producer { name: "m1a".into(), version: "1".into(), models: vec![], languages: vec![] },
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
                confidence: Confidence { value: None, scale: ConfidenceScale::Unknown, calibrated: false },
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
                        confidence: Confidence { value: None, scale: ConfidenceScale::Unknown, calibrated: false },
                    })
                    .collect(),
            })
            .collect(),
    }
}

/// Analytical ink IoU between a traced glyph outline and the unit's source ink
/// mask: the outline is rasterized over the crop grid (scanline fill at pixel
/// centres) and compared with the mask. Empty/empty = 1, empty/nonempty = 0.
pub(crate) fn glyph_ink_iou(g: &GlyphShape, crop_w: usize, crop_h: usize, mask: &[bool]) -> f64 {
    if crop_w == 0 || crop_h == 0 {
        return 1.0;
    }
    // flatten the path to line segments in crop-pixel coordinates. The path is
    // expressed in the glyph's construction frame: the crop maps to
    // [anchor_bbox_fu[0], +ink_span_fu[0]] x [anchor_bbox_fu[1], +ink_span_fu[1]]
    // (the same frame page_pdf uses to place the run: tx = x0 - anchor*sx/upem).
    let k = (g.ink_span_fu[0] / crop_w as f64).max(f64::EPSILON); // font units per px
    let mut polys: Vec<Vec<[f64; 2]>> = Vec::new();
    let mut cur: Vec<[f64; 2]> = Vec::new();
    let mut start = [0.0f64, 0.0f64];
    let mut last = [0.0f64, 0.0f64];
    let flatten = |p0: [f64; 2], p1: [f64; 2], p2: [f64; 2], p3: [f64; 2], cur: &mut Vec<[f64; 2]>| {
        const N: usize = 12;
        for i in 1..=N {
            let t = i as f64 / N as f64;
            let u = 1.0 - t;
            let x = u * u * u * p0[0] + 3.0 * u * u * t * p1[0] + 3.0 * u * t * t * p2[0] + t * t * t * p3[0];
            let y = u * u * u * p0[1] + 3.0 * u * u * t * p1[1] + 3.0 * u * t * t * p2[1] + t * t * t * p3[1];
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
                start = [p.x / k, crop_h as f64 - p.y / k];
                last = start;
                cur.push(start);
            }
            kurbo::PathEl::LineTo(p) => {
                last = [p.x / k, crop_h as f64 - p.y / k];
                cur.push(last);
            }
            kurbo::PathEl::QuadTo(c, p) => {
                // raise the quad to a cubic and flatten
                let (cx, cy, px, py) = (c.x / k, crop_h as f64 - c.y / k, p.x / k, crop_h as f64 - p.y / k);
                let c1 = [last[0] + 2.0 / 3.0 * (cx - last[0]), last[1] + 2.0 / 3.0 * (cy - last[1])];
                let c2 = [px + 2.0 / 3.0 * (cx - px), py + 2.0 / 3.0 * (cy - py)];
                flatten(last, c1, c2, [px, py], &mut cur);
                last = [px, py];
            }
            kurbo::PathEl::CurveTo(c1, c2, p) => {
                let flip = |v: f64| crop_h as f64 - v / k;
                flatten(
                    last,
                    [c1.x / k, flip(c1.y)],
                    [c2.x / k, flip(c2.y)],
                    [p.x / k, flip(p.y)],
                    &mut cur,
                );
                last = [p.x / k, flip(p.y)];
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
    const SUB: usize = 4;
    let mut cover = vec![0u8; crop_w * crop_h];
    for row in 0..crop_h {
        for sub in 0..SUB {
            let py = row as f64 + (sub as f64 + 0.5) / SUB as f64;
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
                        // accumulate the sub-row's contribution as a count
                        cover[idx] = cover[idx].saturating_add(if frac >= 0.5 { 2 } else { 1 });
                    }
                }
                i += 2;
            }
        }
    }
    // foreground when at least half the sub-rows cover the pixel
    let fill: Vec<bool> = cover.iter().map(|c| *c as usize >= SUB.div_ceil(2)).collect();
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
    let pdf_bytes = crate::page_pdf::assemble(
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
    )?;
    let b0 = baseline_one_page(&parts, policy)?;

    let candidates: Vec<(String, usize)> = vec![
        ("reconstruct".to_string(), pdf_bytes.len()),
        ("raster_baseline".to_string(), b0.len()),
    ];
    // the fidelity policy is a hard gate (SPEC §4.2 / policy note): the raster
    // baseline reproduces the source pixels exactly, the reconstruction does
    // not if its vector units measure below min_ink_iou
    let preservation_ok = report.fidelity.preservation_ink_iou_min
        .is_none_or(|m| m >= policy.min_ink_iou);
    let restoration_ok = policy.profile != "clearscan" || report.reconstruction.restoration_qualified;
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
    let pdf_bytes = if selected == "raster_baseline" { b0.clone() } else { pdf_bytes };
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
    let start = std::time::Instant::now();
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
    let units_per_px = if em_px > 0.0 { upem / em_px } else { upem };
    let budget = Budget::from_m0_policy();
    let mut reconstruction = crate::visual_dict::reconstruct(
        &mut plan, policy, &input.rgb, input.width, input.height,
    );

    let mut traced: Vec<TracedShape> = Vec::new();
    let mut missing: std::collections::HashSet<(String,)> = std::collections::HashSet::new();
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
                let prototype = reconstruction.prototype_units.get(&u.shape_key).unwrap_or(u);
                match trace_shape(prototype, &budget, units_per_px) {
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
    let shapes: Vec<GlyphShape> = build_glyph_shapes(&traced, units_per_px, &budget)?;
    // Restoration has a separate gate: the selected observed prototype must
    // survive the actual tracing step with high overlap to its refined donor.
    for occurrence in reconstruction.occurrences.iter_mut().filter(|o| o.repaired) {
        let prototype_key = occurrence.prototype_id.as_deref().unwrap_or("").strip_prefix("prototype:").unwrap_or("");
        let donor = reconstruction.prototype_units.get(prototype_key);
        let traced_iou = donor.and_then(|donor| shapes.iter().find(|s| s.shape_key == prototype_key)
            .map(|g| glyph_ink_iou(g, donor.crop_w, donor.crop_h, &donor.mask)));
        occurrence.prototype_trace_iou = traced_iou;
        if traced_iou.is_none_or(|iou| iou < 0.90) {
            occurrence.repaired = false;
            occurrence.restoration_evidence_passed = false;
            occurrence.decision = "rejected_traced_prototype_fidelity".into();
            missing.insert((occurrence.symbol_id.clone(),));
        }
    }
    reconstruction.restoration_qualified = reconstruction.occurrences.iter()
        .filter(|o| o.repaired).all(|o| o.restoration_evidence_passed && o.prototype_trace_iou.is_some_and(|v| v >= 0.90));
    if !missing.is_empty() {
        for r in regions.iter_mut() {
            if !matches!(r.disposition, RegionDisposition::Vector) {
                continue;
            }
            if r.units.iter().any(|ui| missing.contains(&(plan.owned[*ui].unit.symbol_id.clone(),))) {
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
                let iou = glyph_ink_iou(g, u.crop_w, u.crop_h, &u.mask);
                measured.push((u.symbol_id.clone(), iou));
            }
        }
    }
    for occurrence in &mut reconstruction.occurrences {
        occurrence.source_mask_iou = measured.iter()
            .find(|(symbol, _)| symbol == &occurrence.symbol_id)
            .map(|(_, iou)| *iou);
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
                    if reconstruction.repaired_symbols.contains(&sid) {
                        return None;
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
            let advance = (shapes[gidx].ink_span_fu[0].ceil() as u16).saturating_add(2).max(1);
            keys.push(EncodingKey {
                visual_glyph_id: gidx,
                semantic_string: u.semantic_text.clone(),
                writing_mode: WritingMode::Horizontal,
                required_metrics: MetricsKey { advance, units_per_em: policy.upem },
            });
            occ.push((
                gidx,
                0,
                u.bbox_px,
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


    // raster patches (fallback regions) + artwork ------------------------------
    let mut patches: Vec<Patch> = Vec::new();
    let mut semantic_owner: BTreeMap<String, String> = BTreeMap::new();
    for s in &ocr.spans {
        semantic_owner.insert(s.id.clone(), "invisible".into());
    }
    for r in &regions {
        if !matches!(r.disposition, RegionDisposition::Raster { .. }) || r.units.is_empty() {
            continue;
        }
        let bb = r.bbox_px;
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
                rgb[di..di + 3].copy_from_slice(&input.rgb[si..si + 3]);
            }
        }
        patches.push(Patch {
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
                semantic_owner.insert(plan.owned[ui].unit.span_id.clone(), "visible_tounicode".into());
            }
        }
    }
    // unrecognized/artwork ink is also restored as source raster pixels (VS-05:
    // preserve or invent nothing). Bucketed on a 32px grid to bound object count.
    patches.extend(artwork_patches(input, &plan));

    // coalesce: merge overlapping or exactly-adjacent patches (the artwork
    // buckets tile the page, so this collapses hundreds of 32x32 cells into a
    // few large rects). Merged patches copy the full source rect of the union,
    // so every emitted pixel stays byte-identical to the source.
    let patches = coalesce_patches(input, patches);
    let raster_bytes: usize = patches.iter().map(|p| p.rgb.len()).sum();

    // invisible owners: exactly one per span that is NOT painted by a vector
    // region (SPEC §6.2: never a duplicate layer under already-searchable text)
    let vector_spans: std::collections::HashSet<String> = regions
        .iter()
        .filter(|r| matches!(r.disposition, RegionDisposition::Vector))
        .flat_map(|r| r.units.iter())
        .map(|&ui| plan.owned[ui].unit.span_id.clone())
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
            let text = ocr.spans.iter().find(|s| s.id == sid).map(|s| s.text.clone()).unwrap_or_default();
            let bbox = ocr.spans.iter().find(|s| s.id == sid).map(|s| span_bbox(&s.polygon)).unwrap_or([0.0, 0.0, 0.0, 0.0]);
            // placement on the traced INK baseline: the first unit of the span
            // (its traced glyph box), matching how visible runs are placed
            let place = plan
                .owned
                .iter()
                .find(|u| u.unit.span_id == sid)
                .map(|u| u.unit.bbox_px)
                .unwrap_or(bbox);
            owners.push(Owner { text, bbox_px: bbox, place_px: place, span_id: sid });
        }
    }
    for s in &ocr.spans {
        if vector_spans.contains(&s.id) || owners.iter().any(|o| o.span_id == s.id) {
            continue;
        }
        let place = plan
            .owned
            .iter()
            .find(|u| u.unit.span_id == s.id)
            .map(|u| u.unit.bbox_px)
            .unwrap_or_else(|| span_bbox(&s.polygon));
        owners.push(Owner {
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
    let _owner_encodings: Vec<(usize, String)> = owners
        .iter()
        .map(|o| (0usize, o.text.clone()))
        .collect();
    let span_texts: Vec<(String, String)> = ocr.spans.iter().map(|s| (s.id.clone(), s.text.clone())).collect();
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
        let glyph_idx = if let Some((_, _t)) = encodings.iter().find(|(_, t)| t == &o.text) {
            encodings.iter().position(|(_, t)| t == &o.text).unwrap()
        } else {
            0usize
        };
        if let Some(cid) = all_encodings
            .iter()
            .position(|(_, t)| t == &o.text)
        {
            owner_cids.push(cid as u32 + 1);
            continue;
        }
        let cid = all_encodings.len() as u32 + 1;
        all_encodings.push((glyph_idx, o.text.clone()));
        owner_cids.push(cid);
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
                    RegionDisposition::Vector => "visible_tounicode",
                    RegionDisposition::Raster { .. } => "invisible",
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
            if reconstruction.repaired_symbols.contains(&sid) { return None; }
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

    let report = Report {
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
fn coalesce_patches(input: &Input, mut patches: Vec<Patch>) -> Vec<Patch> {
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
                    base = patch_from_source(input, union);
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

fn patch_from_source(input: &Input, bb: [f64; 4]) -> Patch {
    let (w, h) = (input.width as usize, input.height as usize);
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
            rgb[di..di + 3].copy_from_slice(&input.rgb[si..si + 3]);
        }
    }
    Patch {
        bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
        rgb,
        w: pw as u32,
        h: ph as u32,
    }
}

fn artwork_patches(input: &Input, plan: &OwnershipPlan) -> Vec<Patch> {
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
            cells.entry((gx / CELL, gy / CELL)).or_default().push((gx, gy));
        }
    }
    let mut patches = Vec::new();
    let (w, h) = (input.width as usize, input.height as usize);
    for ((cx, cy), pixels) in cells {
        let (bx, by) = (cx * CELL, cy * CELL);
        let bw = CELL.min(w.saturating_sub(bx));
        let bh = CELL.min(h.saturating_sub(by));
        if bw == 0 || bh == 0 {
            continue;
        }
        // copy the full source bucket (paper + marks): no invented background
        let mut rgb = vec![0u8; bw * bh * 3];
        for gy in by..by + bh {
            let si = gy * w + bx;
            let di = (gy - by) * bw;
            rgb[di * 3..di * 3 + bw * 3].copy_from_slice(&input.rgb[si * 3..si * 3 + bw * 3]);
        }
        let _ = pixels;
        patches.push(Patch {
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
    let (bytes, _stats) = crate::page_pdf::assemble_document(&doc, &parts.shapes, &encodings, &font)?;
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
        bbox_px: [0.0, 0.0, w as f64, h as f64],
        rgb: parts.source_rgb.clone(),
        w: w as u32,
        h: h as u32,
    })
}
