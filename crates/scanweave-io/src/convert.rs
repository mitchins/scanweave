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
use crate::page_pdf::{assemble, Owner, Patch};
use crate::plan::{plan_regions, FallbackReason, Region, RegionDisposition, RegionKind};
use crate::trace::{trace_shape, Budget, TracedShape};
use serde::Serialize;
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize)]
pub struct Policy {
    pub preset: String,
    pub mode: String,
    pub dpi: f64,
    pub upem: u16,
    pub min_ink_iou: f64,
    pub contact_margin_px: f64,
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
pub struct Report {
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
    pub fallback_reasons: HashMap<String, usize>,
    pub font_glyphs: usize,
    pub font_bytes: usize,
    pub pdf_bytes: usize,
    pub raster_bytes: usize,
    pub semantic_owner: HashMap<String, String>,
    pub ownership_invariants: HashMap<String, bool>,
    pub elapsed_ms: u128,
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
}

pub struct Output {
    pub pdf_bytes: Vec<u8>,
    pub report: Report,
    pub font_bytes: Vec<u8>,
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
        spans: input
            .spans
            .iter()
            .map(|s| Span {
                id: s.id.clone(),
                text: s.text.clone(),
                separator_after: " ".into(),
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
        protected_regions: vec![],
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
    let start = std::time::Instant::now();
    let w = input.width;
    let h = input.height;

    // segmentation + ownership -------------------------------------------------
    let seg: Segmentation = segment(&input.rgb, w, h);
    let ocr = to_ocr_page(input);
    let (plan, _) = build_plan(&seg, w, h, &ocr);
    let visual_ok = plan.visual_invariant_ok();
    let semantic_ok = plan.semantic_invariant_ok(&ocr);

    // regions (non-text contact → raster) --------------------------------------
    let mut regions = plan_regions(&plan, 512);

    let mut coverage = Coverage::default();
    let mut fallback_reasons: HashMap<String, usize> = HashMap::new();
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

    // tracing (vector regions only); failures → raster -------------------------
    let em_px = plan
        .owned
        .iter()
        .map(|u| u.unit.crop_h as f64)
        .fold(0.0f64, f64::max);
    let upem = policy.upem as f64;
    let units_per_px = if em_px > 0.0 { upem / em_px } else { upem };
    let budget = Budget::from_m0_policy();

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
                match trace_shape(u, &budget, units_per_px) {
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
    let shapes: Vec<GlyphShape> = build_glyph_shapes(&traced, units_per_px, &budget)?;

    // encoding (four-part key) ---------------------------------------------------
    let mut keys: Vec<EncodingKey> = Vec::new();
    let mut occ: Vec<(usize, u32, [f64; 4], String, String, String)> = Vec::new();
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
    let font_bytes = build_font(&shapes, &encodings, policy.upem)?;


    // raster patches (fallback regions) + artwork ------------------------------
    let mut patches: Vec<Patch> = Vec::new();
    let mut semantic_owner: HashMap<String, String> = HashMap::new();
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
            if owners.iter().any(|o| owner_span(&ocr, &o.text) == sid) {
                continue;
            }
            let text = ocr.spans.iter().find(|s| s.id == sid).map(|s| s.text.clone()).unwrap_or_default();
            let bbox = ocr.spans.iter().find(|s| s.id == sid).map(|s| span_bbox(&s.polygon)).unwrap_or([0.0, 0.0, 0.0, 0.0]);
            owners.push(Owner { text, bbox_px: bbox });
        }
    }
    for s in &ocr.spans {
        if vector_spans.contains(&s.id) || owners.iter().any(|o| o.text == s.text) {
            continue;
        }
        owners.push(Owner { text: s.text.clone(), bbox_px: span_bbox(&s.polygon) });
    }
    // clamp owner boxes to the canonical raster (OCR polygons may overrun it)
    for o in owners.iter_mut() {
        o.bbox_px[0] = o.bbox_px[0].max(0.0);
        o.bbox_px[1] = o.bbox_px[1].max(0.0);
        o.bbox_px[2] = o.bbox_px[2].min(w as f64);
        o.bbox_px[3] = o.bbox_px[3].min(h as f64);
    }
    let owner_encodings: Vec<(usize, String)> = owners
        .iter()
        .map(|o| (0usize, o.text.clone()))
        .collect();
    let span_texts: Vec<(String, String)> = ocr.spans.iter().map(|s| (s.id.clone(), s.text.clone())).collect();
    // One font resource for everything: the vector CIDs plus an owner CID per
    // fallback span text (referencing GID1, drawn invisibly — the overlay the M0
    // baseline proved extractable). No second font, no second layer.
    let mut all_encodings = encodings.clone();
    let mut owner_cids: Vec<u32> = Vec::new();
    for o in &owners {
        let glyph_idx = if let Some((_, t)) = encodings.iter().find(|(_, t)| t == &o.text) {
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
    let font_bytes = build_font(&shapes, &all_encodings, policy.upem)?;
    let glyphless_bytes: Vec<u8> = Vec::new();
    let owner_encodings: Vec<(usize, String)> =
        owner_cids.iter().map(|cid| all_encodings[(*cid - 1) as usize].clone()).collect();

    let pdf_bytes = assemble(
        &shapes,
        &all_encodings,
        &occ,
        &span_texts,
        (w as f64 * 72.0 / policy.dpi) as f32,
        (h as f64 * 72.0 / policy.dpi) as f32,
        policy.dpi,
        seg.paper,
        seg.ink,
        font_bytes.clone(),
        glyphless_bytes,
        &owner_encodings,
        &patches,
        &owners,
        &owner_cids,
    )?;

    let mut invariants = HashMap::new();
    invariants.insert("visual".into(), visual_ok);
    invariants.insert("semantic".into(), semantic_ok);

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

    let report = Report {
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
        font_glyphs: shapes.len() + 1,
        font_bytes: font_bytes.len(),
        pdf_bytes: pdf_bytes.len(),
        raster_bytes,
        semantic_owner,
        ownership_invariants: invariants,
        elapsed_ms: start.elapsed().as_millis(),
    };

    Ok(Output {
        pdf_bytes,
        report,
        font_bytes,
    })
}

fn owner_span(ocr: &scanweave_core::ocr_page::OcrPage, text: &str) -> String {
    ocr.spans
        .iter()
        .find(|s| s.text == text)
        .map(|s| s.id.clone())
        .unwrap_or_default()
}


/// Source-pixel patches for non-text artwork (never dropped, never relabelled).
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
