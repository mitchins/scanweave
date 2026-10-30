//! Document-level conversion: many pages -> one searchable PDF.
//!
//! The one-page pipeline (`convert`) is unchanged; this module composes it.
//! Every page is converted into [`PageParts`]; the pages' (shape, label)
//! encodings are merged into ONE document-wide encoding table in
//! first-appearance order so identical content across pages shares a CID, a
//! single font program is embedded once, and [`page_pdf::assemble_document`]
//! emits one PDF with N pages.
//!
//! `--mode auto` ranks candidates by ACTUAL serialized bytes: the shared-font
//! reconstruction against a whole-page searchable raster baseline document,
//! and selects the smaller candidate that passes the same semantic gates.

use crate::convert::{Input, Policy, Report};
use crate::fontbuild::{build_font, build_font_with_bounds};
use crate::glyphs::GlyphShape;
use crate::page_pdf::PageParts;

/// A page plus its document-global CID remap.
pub struct DocumentPage {
    pub parts: PageParts,
    /// the page's report (coverage/invariants/occurrences — page-local facts)
    pub report: Report,
}

/// A candidate document actually serialized and measured.
#[derive(Debug, Clone, serde::Serialize)]
pub struct DocumentCandidate {
    pub name: String,
    pub pages: usize,
    pub pdf_bytes: usize,
    pub font_bytes: usize,
    pub image_xobjects: usize,
    pub image_references: usize,
    pub content_bytes: usize,
    pub raster_encoded_bytes: usize,
    /// per-page analytical ink IoU (min over vector units); None = no vector
    pub page_fidelity: Vec<Option<f64>>,
    /// pages that rasterized (whole-page raster baseline marks all)
    pub raster_pages: usize,
    pub image_encoding_ms: u128,
    pub assembly_ms: u128,
}

/// Document-level report: per-page reports + document totals + the measured
/// candidates and the selection.
#[derive(Debug, Clone, serde::Serialize)]
pub struct DocumentReport {
    pub document_id: String,
    /// the policy's min_ink_iou the document was checked against
    pub min_ink_iou: f64,
    /// per-page analytical ink IoU of the emitted candidate
    pub page_fidelity: Vec<Option<f64>>,
    pub pages: usize,
    pub selected: String,
    pub candidates: Vec<DocumentCandidate>,
    pub pdf_bytes: usize,
    pub font_bytes: usize,
    pub image_xobjects: usize,
    pub image_references: usize,
    pub raster_encoded_bytes: usize,
    pub content_bytes: usize,
    pub image_encoding_ms: u128,
    pub assembly_ms: u128,
    /// Instrumented wall-time breakdown for the document pipeline. The
    /// remainder covers candidate selection and report assembly.
    pub stage_timings: DocumentStageTimings,
    pub page_order: Vec<String>,
    pub page_reports: Vec<Report>,
    pub coverage: DocumentCoverage,
    pub search: SearchPlan,
    pub ownership_invariants: std::collections::BTreeMap<String, bool>,
    /// sha256 of every source asset and OCR page (binding, per page)
    pub bindings: Vec<PageBinding>,
    #[serde(skip_serializing_if="Option::is_none")]
    pub glyph_sharing:Option<crate::glyph_sharing::transport::SharingReport>,
}

#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct DocumentStageTimings {
    pub total_ms: u128,
    pub donor_collection_ms: u128,
    pub page_conversion_ms: u128,
    pub document_font_union_ms: u128,
    pub font_build_ms: u128,
    pub reconstruction_pdf_ms: u128,
    pub raster_baseline_prepare_ms: u128,
    pub raster_baseline_pdf_ms: u128,
    pub remaining_pipeline_ms: u128,
}

#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct DocumentCoverage {
    pub text_ink_px_total: u64,
    pub text_ink_px_vector: u64,
    pub text_ink_px_raster: u64,
    pub other_ink_px: u64,
    pub unowned_ink_px: u64,
    pub multiply_owned_ink_px: u64,
}

/// Searchable text the document guarantees, by page and span — the honest
/// denominator for "search success" reporting (the Python harness measures the
/// engines against this plan).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct SearchPlan {
    pub pages: Vec<PageSearch>,
}

#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct PageSearch {
    pub page_id: String,
    pub lines: Vec<LineSearch>,
}

#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct LineSearch {
    pub text: String,
    pub spans: Vec<String>,
    /// "visible" (glyph runs) or "owner" (fallback overlay) per span
    pub owners: Vec<String>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct PageBinding {
    pub page_id: String,
    pub source_sha256: String,
    pub ocr_sha256: String,
    pub pixel_sha256: String,
}

pub struct DocumentOutput {
    pub pdf_bytes: Vec<u8>,
    /// exact shared font program used by the emitted candidate
    pub font_bytes: Vec<u8>,
    /// searchable whole-page raster baseline candidate (MRC-comparable gate)
    pub raster_baseline_pdf_bytes: Vec<u8>,
    pub report: DocumentReport,
}

/// Build the document-wide (shape, label) encoding table and remap every
/// page's CIDs onto it. Deterministic: page order, then slot order.
fn union_encodings(pages: &[DocumentPage]) -> (Vec<GlyphShape>, Vec<(usize, String)>, Vec<Remap>) {
    let mut shapes: Vec<GlyphShape> = Vec::new();
    let mut shape_index: std::collections::HashMap<String, usize> =
        std::collections::HashMap::new();
    let mut encodings: Vec<(usize, String)> = Vec::new();
    let mut enc_index: std::collections::HashMap<(usize, String), usize> =
        std::collections::HashMap::new();
    let mut remaps: Vec<Remap> = Vec::with_capacity(pages.len());

    for page in pages {
        let p = &page.parts;
        // page-local shape idx -> global shape idx
        let mut shape_map: Vec<usize> = Vec::with_capacity(p.shapes.len());
        for (i, s) in p.shapes.iter().enumerate() {
            let gi = *shape_index.entry(s.shape_key.clone()).or_insert_with(|| {
                shapes.push(s.clone());
                shapes.len() - 1
            });
            shape_map.push(gi);
            let _ = i;
        }
        // page-local CID (1-based into p.encodings) -> global CID (1-based)
        let mut cid_map: Vec<u32> = Vec::with_capacity(p.encodings.len());
        for (local_shape, text) in &p.encodings {
            let gshape = shape_map.get(*local_shape).copied().unwrap_or(0);
            let key = (gshape, text.clone());
            // 0-based global encoding index; the CID is that index + 1.
            // enc_index MUST be populated on first sight, otherwise repeated
            // (glyph, string) pairs mint new CIDs and the shared font cannot
            // deduplicate across pages (matters at the 16-bit CID ceiling).
            let gc = match enc_index.get(&key).copied() {
                Some(i) => i,
                None => {
                    encodings.push((gshape, text.clone()));
                    let i = encodings.len() - 1;
                    enc_index.insert(key, i);
                    i
                }
            };
            cid_map.push(gc as u32 + 1);
        }
        remaps.push(Remap { cid_map, shape_map });
    }
    (shapes, encodings, remaps)
}

struct Remap {
    cid_map: Vec<u32>,
    shape_map: Vec<usize>,
}

fn apply_remap(page: &mut DocumentPage, remap: &Remap) {
    for o in page.parts.occurrences.iter_mut() {
        // occurrences carry (LOCAL shape index, 0-based LOCAL cid); both must
        // be expressed in the document-wide tables
        if let Some(&g) = remap.shape_map.get(o.0) {
            o.0 = g;
        }
        if let Some(&g) = remap.cid_map.get(o.1 as usize) {
            o.1 = g.saturating_sub(1);
        }
    }
    for c in page.parts.owner_cids.iter_mut() {
        // owner_cids are 1-based local
        if let Some(&g) = remap.cid_map.get((*c).saturating_sub(1) as usize) {
            *c = g;
        }
    }
    for owner in &mut page.parts.owners {
        for ch in &mut owner.characters {
            if let Some(&global) = remap.cid_map.get(ch.cid.saturating_sub(1) as usize) {
                ch.cid = global;
            }
        }
    }
}

/// Remove programs before font construction, retaining every visible and
/// invisible reference (including per-character semantic owners). The tables
/// are already document-global; order is retained and no outline is rewritten.
fn retain_required_font_entries(
    pages: &mut [DocumentPage],
    shapes: &mut Vec<GlyphShape>,
    encodings: &mut Vec<(usize, String)>,
) {
    let mut required_shapes = vec![false; shapes.len()];
    let mut required_cids = vec![false; encodings.len()];
    for page in pages.iter() {
        for (shape, cid, ..) in &page.parts.occurrences {
            if let Some(required) = required_shapes.get_mut(*shape) {
                *required = true;
            }
            if let Some(required) = required_cids.get_mut(*cid as usize) {
                *required = true;
            }
        }
        for cid in page.parts.owner_cids.iter().copied().chain(
            page.parts.owners.iter().flat_map(|o| o.characters.iter().map(|ch| ch.cid)),
        ) {
            if let Some(required) = required_cids.get_mut(cid.saturating_sub(1) as usize) {
                *required = true;
            }
        }
    }
    for ((shape, _), required) in encodings.iter().zip(&required_cids) {
        if *required {
            if let Some(required) = required_shapes.get_mut(*shape) {
                *required = true;
            }
        }
    }
    let mut shape_map = vec![0; shapes.len()];
    let mut next = 0;
    for (index, required) in required_shapes.iter().enumerate() {
        if *required {
            shape_map[index] = next;
            next += 1;
        }
    }
    let mut index = 0;
    shapes.retain(|_| {
        let required = required_shapes[index];
        index += 1;
        required
    });
    let mut cid_map = vec![0; encodings.len()];
    let mut retained = Vec::new();
    for (index, (shape, text)) in encodings.iter().enumerate() {
        if required_cids[index] {
            retained.push((shape_map.get(*shape).copied().unwrap_or(0), text.clone()));
            cid_map[index] = retained.len() as u32;
        }
    }
    *encodings = retained;
    let remap = Remap { shape_map, cid_map };
    for page in pages {
        apply_remap(page, &remap);
    }
}

fn document_design_bounds(shapes: &[GlyphShape]) -> Option<[i16; 4]> {
    shapes.iter().map(|s| [
        s.bbox_fu[0].floor() as i16, s.bbox_fu[1].floor() as i16,
        s.bbox_fu[2].ceil() as i16, s.bbox_fu[3].ceil() as i16,
    ]).reduce(|a, b| [a[0].min(b[0]), a[1].min(b[1]), a[2].max(b[2]), a[3].max(b[3])])
}

// The layout chooser and writer must share the document-wide encoding gate.
fn allows_tonal_images(inputs: &[Input], policy: &Policy) -> bool {
    policy.profile == "clearscan"
        && inputs.iter().all(|input| input.protected_regions.is_empty())
}

/// Convert a bundle of pages into ONE document PDF.
pub fn convert_document(
    document_id: &str,
    inputs: &[Input],
    policy: &Policy,
) -> Result<DocumentOutput, String> {
    convert_document_with_sources(document_id, inputs, policy, &[])
}

/// Same converter with strictly validated source image hints from PDF import.
/// Hints cannot supersede an emitted vector or alter the faithful profile.
pub fn convert_document_with_sources(
    document_id: &str,
    inputs: &[Input],
    policy: &Policy,
    sources: &[Option<crate::source_image::EncodedSourceImage>],
) -> Result<DocumentOutput, String> {
    convert_document_with_sources_and_sharing(document_id,inputs,policy,sources,None)
}

/// Opt-in frozen native glyph sharing. None retains the default conversion path.
pub fn convert_document_with_sources_and_sharing(
    document_id:&str,inputs:&[Input],policy:&Policy,
    sources:&[Option<crate::source_image::EncodedSourceImage>],sharing:Option<f64>,
)->Result<DocumentOutput,String>{
    convert_document_with_sources_and_sharing_ceiling(document_id, inputs, policy, sources, sharing, None)
}

/// Convert with an optional absolute fit-error ceiling for glyph sharing.
pub fn convert_document_with_sources_and_sharing_ceiling(
    document_id:&str,inputs:&[Input],policy:&Policy,
    sources:&[Option<crate::source_image::EncodedSourceImage>],sharing:Option<f64>, absolute_error_ceiling:Option<f64>,
)->Result<DocumentOutput,String>{
    if sharing.is_some() && policy.profile != "clearscan" {return Err("glyph sharing requires ClearScan".into());}
    let mut effective_policy = policy.clone();
    if policy.profile == "clearscan" && policy.image_encoding.predictor == 1 {
        effective_policy.image_encoding.predictor = 0;
    }
    let policy = &effective_policy;
    let total_start = std::time::Instant::now();
    let mut stage_timings = DocumentStageTimings::default();
    if inputs.is_empty() {
        return Err("document has no pages".into());
    }
    let tonal_document = allows_tonal_images(inputs, policy);
    // 1. Collect only safe, unprotected single-glyph evidence across the
    //    document, then convert pages with sibling-page observations available
    //    to their local reconstruction dictionary.
    let stage_start = std::time::Instant::now();
    let all_donors: Vec<Vec<crate::units::Unit>> = inputs
        .iter()
        .map(crate::convert::collect_document_donors)
        .collect();
    stage_timings.donor_collection_ms = stage_start.elapsed().as_millis();
    let mut pages: Vec<DocumentPage> = Vec::with_capacity(inputs.len());
    let stage_start = std::time::Instant::now();
    for (page_index, input) in inputs.iter().enumerate() {
        let mut sibling_donors = Vec::new();
        if policy.profile == "clearscan" {
            // Bound the experimental evidence set before page conversion.
            // Repeated text-heavy documents can contain thousands of
            // siblings; a deterministic page-stratified sample caps tracing
            // work and avoids letting the first pages dominate.
            let wanted: std::collections::BTreeSet<String> = input
                .spans
                .iter()
                .flat_map(|span| span.text.chars().map(|c| c.to_string()))
                .collect();
            let mut by_label: std::collections::BTreeMap<
                String,
                std::collections::BTreeMap<usize, Vec<crate::units::Unit>>,
            > = std::collections::BTreeMap::new();
            for (donor_page, donors) in all_donors.iter().enumerate() {
                if donor_page == page_index {
                    continue;
                }
                for donor in donors {
                    if !wanted.contains(&donor.semantic_text)
                        || donor.semantic_text.chars().count() != 1
                    {
                        continue;
                    }
                    by_label
                        .entry(donor.semantic_text.clone())
                        .or_default()
                        .entry(donor_page)
                        .or_default()
                        .push(donor.clone());
                }
            }
            // Round-robin across source pages, not the first N occurrences
            // from the earliest pages.
            for (_label, page_donors) in by_label {
                let mut offsets: std::collections::BTreeMap<usize, usize> =
                    page_donors.keys().map(|&page| (page, 0)).collect();
                for _ in 0..32 {
                    let mut any = false;
                    for (&donor_page, donors) in &page_donors {
                        let offset = offsets.get_mut(&donor_page).unwrap();
                        let Some(source) = donors.get(*offset) else {
                            continue;
                        };
                        *offset += 1;
                        any = true;
                        let mut donor = source.clone();
                        donor.retain_grayscale(
                            &inputs[donor_page].rgb,
                            inputs[donor_page].width,
                            inputs[donor_page].height,
                        );
                        donor.symbol_id =
                            format!("{}:{}", inputs[donor_page].page_id, donor.symbol_id);
                        donor.span_id = format!("{}:{}", inputs[donor_page].page_id, donor.span_id);
                        sibling_donors.push(donor);
                    }
                    if !any {
                        break;
                    }
                }
            }
        } else {
            // Keep the existing faithful/ClearScan donor behaviour unchanged.
            for (donor_page, donors) in all_donors.iter().enumerate() {
                if donor_page == page_index {
                    continue;
                }
                for donor in donors {
                    let mut donor = donor.clone();
                    donor.symbol_id = format!("{}:{}", inputs[donor_page].page_id, donor.symbol_id);
                    donor.span_id = format!("{}:{}", inputs[donor_page].page_id, donor.span_id);
                    sibling_donors.push(donor);
                }
            }
        }
        let (mut parts, report) =
            crate::convert::convert_parts_with_document_donors(input, policy, &sibling_donors, tonal_document)?;
        if policy.profile == "clearscan" && parts.occurrences.is_empty() {
            parts.encoded_source = sources
                .get(page_index)
                .cloned()
                .flatten()
                .filter(|source| source.matches(input));
        }
        pages.push(DocumentPage { parts, report });
    }
    stage_timings.page_conversion_ms = stage_start.elapsed().as_millis();

    let snapshot_start = std::time::Instant::now();
    let observations=sharing.map(|_|crate::glyph_sharing::source::snapshot(&pages,&all_donors));

    let snapshot_seconds = snapshot_start.elapsed().as_secs_f64();

    // 2. document-wide font: union of (shape, label), remapped per page
    let stage_start = std::time::Instant::now();
    let (mut shapes, mut encodings, remaps) = union_encodings(&pages);
    for (page, remap) in pages.iter_mut().zip(remaps.iter()) {
        apply_remap(page, remap);
    }
    let design_bounds = document_design_bounds(&shapes);
    if policy.profile == "clearscan" {
        retain_required_font_entries(&mut pages, &mut shapes, &mut encodings);
    }
    stage_timings.document_font_union_ms = stage_start.elapsed().as_millis();
    let stage_start = std::time::Instant::now();
    let mut font_bytes = if policy.profile == "clearscan" {
        build_font_with_bounds(&shapes, &encodings, policy.upem, design_bounds)?
    } else {
        build_font(&shapes, &encodings, policy.upem)?
    };
    stage_timings.font_build_ms = stage_start.elapsed().as_millis();

    // 3. the reconstruction candidate
    let stage_start = std::time::Instant::now();
    // Explicit caller-native preservation is independent of ClearScan's lossy
    // paper policy. Conservatively retain the existing document encoding when
    // any page has caller protection; no new per-page ownership flags are needed.
    let assemble = if tonal_document {
        crate::page_pdf::assemble_document_with_tonal_fallback
    } else {crate::page_pdf::assemble_document_with_options};
    let parts:Vec<_>=pages.iter().map(|p|p.parts.clone()).collect();
    let (mut pdf_bytes,mut stats,raster_choice)=if sharing.is_some() && tonal_document {
        crate::page_pdf::assemble_document_with_tonal_choice(&parts,&shapes,&encodings,&font_bytes,policy.image_encoding)?
    }else{let(pdf,stats)=assemble(&parts,&shapes,&encodings,&font_bytes,policy.image_encoding)?;(pdf,stats,false)};
    let baseline_font=sharing.map(|_|font_bytes.clone());
    let mut sharing_report=None;
    if let (Some(multiplier),Some(rows))=(sharing,observations.as_ref()) {
        let(candidate,mut report)=crate::glyph_sharing::transport::share(rows,&parts,&shapes,&encodings,&font_bytes,policy.image_encoding,raster_choice,multiplier,absolute_error_ceiling)?;
        report.stage_seconds.insert("source_snapshot".into(), snapshot_seconds);
        if let Some(candidate)=candidate {font_bytes=candidate.font;pdf_bytes=candidate.pdf;stats=candidate.stats;}
        sharing_report=Some(report);
    }
    drop(parts);
    drop(observations);
    stage_timings.reconstruction_pdf_ms = stage_start.elapsed().as_millis();

    // 4. the whole-page searchable raster baseline candidate (auto mode ranks
    //    it against the reconstruction by real bytes)
    // the raster-baseline candidate: the same pages with the whole-page source
    // patch and the text layer drawn invisibly (searchable, zero vector ink)
    let stage_start = std::time::Instant::now();
    let mut baseline_parts: Vec<PageParts> = Vec::new();
    for p in &pages {
        let mut bp = p.parts.clone();
        bp.raster_baseline = true;
        bp.patches = vec![crate::convert::whole_page_patch(
            &p.parts,
            p.parts.source_w,
            p.parts.source_h,
        )?];
        baseline_parts.push(bp);
    }
    stage_timings.raster_baseline_prepare_ms = stage_start.elapsed().as_millis();
    let stage_start = std::time::Instant::now();
    let (baseline_pdf, baseline_stats) = crate::page_pdf::assemble_document_with_options(
        &baseline_parts,
        &shapes,
        &encodings,
        baseline_font.as_deref().unwrap_or(&font_bytes),
        policy.image_encoding,
    )?;
    stage_timings.raster_baseline_pdf_ms = stage_start.elapsed().as_millis();

    // 5. candidate accounting + selection
    let _image_xobjects: usize = pages.iter().map(|p| p.parts.patches.len()).sum();
    // both candidates are ALWAYS reported (with their real serialized sizes);
    // auto mode only decides which one is emitted
    let candidates = vec![
        DocumentCandidate {
            name: "reconstruct".into(),
            pages: pages.len(),
            pdf_bytes: pdf_bytes.len(),
            font_bytes: stats.font_bytes,
            image_xobjects: stats.image_xobjects,
            image_references: stats.image_references,
            content_bytes: stats.content_bytes,
            raster_encoded_bytes: stats.raster_encoded_bytes,
            page_fidelity: pages
                .iter()
                .map(|p| p.report.fidelity.vector_ink_iou_min)
                .collect(),
            raster_pages: pages
                .iter()
                .filter(|p| p.parts.occurrences.is_empty())
                .count(),
            image_encoding_ms: stats.image_encoding_ms,
            assembly_ms: stats.assembly_ms,
        },
        DocumentCandidate {
            name: "raster_baseline".into(),
            pages: baseline_parts.len(),
            pdf_bytes: baseline_pdf.len(),
            font_bytes: baseline_stats.font_bytes,
            image_xobjects: baseline_stats.image_xobjects,
            image_references: baseline_stats.image_references,
            content_bytes: baseline_stats.content_bytes,
            raster_encoded_bytes: baseline_stats.raster_encoded_bytes,
            // the raster baseline reproduces the source pixels exactly
            page_fidelity: baseline_parts.iter().map(|_| Some(1.0)).collect(),
            raster_pages: baseline_parts.len(),
            image_encoding_ms: baseline_stats.image_encoding_ms,
            assembly_ms: baseline_stats.assembly_ms,
        },
    ];
    // auto: the fidelity policy is a HARD gate — a candidate whose vector units
    // fall below min_ink_iou is disqualified, not ranked by bytes. The raster
    // baseline reproduces the source pixels exactly and is always qualified.
    let recon_ok = pages.iter().all(|p| {
        (policy.profile == "clearscan"
            || p.report
                .fidelity
                .preservation_ink_iou_min
                .is_none_or(|m| m >= policy.min_ink_iou))
            && (policy.profile != "clearscan" || p.report.reconstruction.restoration_qualified)
    });
    let baseline_ok = true;
    let selected: String = if policy.mode == "auto" {
        if recon_ok && (!baseline_ok || pdf_bytes.len() <= baseline_pdf.len()) {
            "reconstruct".to_string()
        } else if baseline_ok {
            "raster_baseline".to_string()
        } else {
            return Err("no candidate satisfies the fidelity policy".into());
        }
    } else if !recon_ok {
        // explicit reconstruct mode still refuses to emit a candidate that
        // violates the fidelity policy
        return Err(format!(
            "fidelity policy violated: vector units measure below min_ink_iou {} on {} page(s)              (use --mode auto to fall back to the raster baseline, or lower the policy explicitly)",
            policy.min_ink_iou,
            pages.iter().filter(|p| {
                p.report.fidelity.preservation_ink_iou_min.is_some_and(|m| m < policy.min_ink_iou)
                    || (policy.profile == "clearscan"
                        && !p.report.reconstruction.restoration_qualified)
            }).count()
        ));
    } else {
        "reconstruct".into()
    };
    let (out_bytes, out_len) = if selected == "raster_baseline" {
        (baseline_pdf.clone(), baseline_pdf.len())
    } else {
        (pdf_bytes.clone(), pdf_bytes.len())
    };

    // 6. document report
    let mut coverage = DocumentCoverage::default();
    let mut ownership_invariants = std::collections::BTreeMap::new();
    let mut ok_visual = true;
    let mut ok_semantic = true;
    for p in &pages {
        let c = &p.report.coverage;
        coverage.text_ink_px_total += c.text_ink_px_total;
        coverage.text_ink_px_vector += c.text_ink_px_vector;
        coverage.text_ink_px_raster += c.text_ink_px_raster;
        coverage.other_ink_px += c.other_ink_px;
        coverage.unowned_ink_px += c.unowned_ink_px;
        coverage.multiply_owned_ink_px += c.multiply_owned_ink_px;
        ok_visual &= p.report.ownership_invariants["visual"];
        ok_semantic &= p.report.ownership_invariants["semantic"];
    }
    ownership_invariants.insert("visual".into(), ok_visual);
    ownership_invariants.insert("semantic".into(), ok_semantic);

    let mut search = SearchPlan::default();
    for p in &pages {
        let mut ps = PageSearch {
            page_id: p.report.page_id.clone(),
            lines: Vec::new(),
        };
        for line in &p.parts.lines {
            let mut ls = LineSearch {
                text: line.text.clone(),
                spans: Vec::new(),
                owners: Vec::new(),
            };
            for sid in &line.spans {
                ls.spans.push(sid.clone());
                let owner = p
                    .report
                    .semantic_owner
                    .get(sid)
                    .cloned()
                    .unwrap_or_else(|| "visible_tounicode".into());
                ls.owners.push(owner);
            }
            ps.lines.push(ls);
        }
        search.pages.push(ps);
    }

    stage_timings.total_ms = total_start.elapsed().as_millis();
    let measured = stage_timings.donor_collection_ms
        + stage_timings.page_conversion_ms
        + stage_timings.document_font_union_ms
        + stage_timings.font_build_ms
        + stage_timings.reconstruction_pdf_ms
        + stage_timings.raster_baseline_prepare_ms
        + stage_timings.raster_baseline_pdf_ms;
    stage_timings.remaining_pipeline_ms = stage_timings.total_ms.saturating_sub(measured);
    Ok(DocumentOutput {
        pdf_bytes: out_bytes.clone(),
        font_bytes: if selected=="raster_baseline" {baseline_font.unwrap_or_else(||font_bytes.clone())}else{font_bytes.clone()},
        raster_baseline_pdf_bytes: baseline_pdf.clone(),
        report: DocumentReport {
            document_id: document_id.to_string(),
            min_ink_iou: policy.min_ink_iou,
            page_fidelity: if selected == "raster_baseline" {
                baseline_parts.iter().map(|_| Some(1.0)).collect()
            } else {
                pages
                    .iter()
                    .map(|p| p.report.fidelity.vector_ink_iou_min)
                    .collect()
            },
            pages: pages.len(),
            selected: selected.clone(),
            candidates,
            pdf_bytes: out_len,
            // the top-level accounting describes the EMITTED candidate (P2):
            // when auto falls back to the raster baseline, its image/content
            // byte statistics are the ones that matter
            font_bytes: if selected == "raster_baseline" {
                baseline_stats.font_bytes
            } else {
                stats.font_bytes
            },
            image_xobjects: if selected == "raster_baseline" {
                baseline_stats.image_xobjects
            } else {
                stats.image_xobjects
            },
            image_references: if selected == "raster_baseline" {
                baseline_stats.image_references
            } else {
                stats.image_references
            },
            raster_encoded_bytes: if selected == "raster_baseline" {
                baseline_stats.raster_encoded_bytes
            } else {
                stats.raster_encoded_bytes
            },
            content_bytes: if selected == "raster_baseline" {
                baseline_stats.content_bytes
            } else {
                stats.content_bytes
            },
            image_encoding_ms: if selected == "raster_baseline" {
                baseline_stats.image_encoding_ms
            } else {
                stats.image_encoding_ms
            },
            assembly_ms: if selected == "raster_baseline" {
                baseline_stats.assembly_ms
            } else {
                stats.assembly_ms
            },
            stage_timings,
            page_order: pages.iter().map(|p| p.report.page_id.clone()).collect(),
            page_reports: pages.iter().map(|p| p.report.clone()).collect(),
            coverage,
            search,
            ownership_invariants,
            bindings: Vec::new(),
            glyph_sharing:sharing_report,
        },
    })
}

#[cfg(test)]
mod semantic_owner_union_tests {
    use super::*;
    use crate::convert::{convert_parts, SpanInput, SymbolInput};

    #[test]
    fn hidden_and_visible_same_unicode_keep_separate_cids_across_pages() {
        let poly = |b: [f64; 4]| vec![[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]];
        let mut rgb = vec![255; 64 * 48 * 3];
        for y in 10..30 {
            for x in 20..30 {
                rgb[(y * 64 + x) * 3..(y * 64 + x) * 3 + 3].fill(0);
            }
        }
        let input = Input {
            rgb,
            width: 64,
            height: 48,
            page_id: "owner-a".into(),
            spans: vec![SpanInput {
                id: "word".into(),
                text: "ééé".into(),
                separator_after: "".into(),
                polygon: poly([4., 8., 47., 32.]),
                symbols: vec![
                    SymbolInput {
                        id: "left".into(),
                        range: (0, 2),
                        polygon: poly([5., 10., 15., 30.]),
                    },
                    SymbolInput {
                        id: "middle".into(),
                        range: (2, 4),
                        polygon: poly([20., 10., 30., 30.]),
                    },
                    SymbolInput {
                        id: "right".into(),
                        range: (4, 6),
                        polygon: poly([35., 10., 45., 30.]),
                    },
                ],
            }],
            protected_regions: vec![],
            raster_to_page_pt: [0.24, 0., 0., -0.24, 0., 11.52],
            pixel_sha256: None,
        };
        let policy = Policy {
            profile: "clearscan".into(),
            ..Policy::default()
        };
        let mut pages = Vec::new();
        for n in 0..2 {
            let mut input = input.clone();
            input.page_id = format!("owner-{n}");
            let (parts, report) = convert_parts(&input, &policy).unwrap();
            assert_eq!(parts.occurrences.len(), 1);
            let visible_shape = parts.occurrences[0].0;
            let owner = parts.owners.iter().find(|o| o.span_id == "word").unwrap();
            assert_eq!(owner.characters.len(), 2);
            for ch in &owner.characters {
                let (shape, text) = &parts.encodings[ch.cid as usize - 1];
                assert_eq!(text, "é");
                assert_ne!(*shape, visible_shape);
                assert_eq!(parts.shapes[*shape].shape_key, "__semantic_owner_frame");
            }
            pages.push(DocumentPage { parts, report });
        }
        let (mut shapes, mut encodings, remaps) = union_encodings(&pages);
        assert_eq!(
            shapes
                .iter()
                .filter(|g| g.shape_key == "__semantic_owner_frame")
                .count(),
            1
        );
        for (page, remap) in pages.iter_mut().zip(&remaps) {
            apply_remap(page, remap);
            let visible_shape = page.parts.occurrences[0].0;
            for owner in &page.parts.owners {
                for ch in &owner.characters {
                    let (shape, text) = &encodings[ch.cid as usize - 1];
                    assert_eq!(text, "é");
                    assert_ne!(*shape, visible_shape);
                    assert_eq!(shapes[*shape].shape_key, "__semantic_owner_frame");
                }
            }
        }
        // Put an abandoned trace and encoding ahead of all required entries:
        // pruning must remap visible occurrences and invisible character owners.
        let expected_encodings = encodings.clone();
        let expected_keys: Vec<_> = shapes.iter().map(|s| s.shape_key.clone()).collect();
        let expected_occurrences: Vec<_> = pages.iter().map(|p| p.parts.occurrences.clone()).collect();
        let shift = Remap {
            shape_map: (1..=shapes.len()).collect(),
            cid_map: (2..=encodings.len() as u32 + 1).collect(),
        };
        for page in &mut pages {
            apply_remap(page, &shift);
        }
        for (shape, _) in &mut encodings {
            *shape += 1;
        }
        let mut unused = shapes[0].clone();
        unused.shape_key = "unused trace".into();
        shapes.insert(0, unused);
        encodings.insert(0, (0, "unused label".into()));
        retain_required_font_entries(&mut pages, &mut shapes, &mut encodings);
        assert_eq!(encodings, expected_encodings);
        assert_eq!(shapes.iter().map(|s| s.shape_key.clone()).collect::<Vec<_>>(), expected_keys);
        for (page, expected) in pages.iter().zip(&expected_occurrences) {
            assert_eq!(&page.parts.occurrences, expected);
            for owner in &page.parts.owners {
                for ch in &owner.characters {
                    let (shape, text) = &encodings[ch.cid as usize - 1];
                    assert_eq!(text, "é");
                    assert_eq!(shapes[*shape].shape_key, "__semantic_owner_frame");
                }
            }
        }
    }
}

#[cfg(test)]
mod tonal_protection_tests {
    use super::*;

    #[test]
    fn one_protected_page_disables_tonal_layout_and_assembly_document_wide() {
        let page = Input {
            page_id: "unprotected".into(), width: 2, height: 2, rgb: vec![255; 12],
            spans: vec![], protected_regions: vec![], pixel_sha256: None,
            raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, 0.48],
        };
        let clear = Policy { profile: "clearscan".into(), ..Policy::default() };
        assert!(allows_tonal_images(&[page.clone(), page.clone()], &clear));
        let mut protected = page.clone();
        protected.protected_regions.push(crate::convert::ProtectedInput {
            id: "mark".into(), polygon: vec![[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]], reason: "caller".into(),
        });
        assert!(!allows_tonal_images(&[page.clone(), protected], &clear));
        assert!(!allows_tonal_images(&[page], &Policy::default()));
    }
}
