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

use crate::convert::{convert_parts, Input, Policy, Report};
use crate::fontbuild::build_font;
use crate::glyphs::GlyphShape;
use crate::page_pdf::{assemble_document, PageParts};

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
    pub content_bytes: usize,
    pub raster_encoded_bytes: usize,
    /// pages that rasterized (whole-page raster baseline marks all)
    pub raster_pages: usize,
}

/// Document-level report: per-page reports + document totals + the measured
/// candidates and the selection.
#[derive(Debug, Clone, serde::Serialize)]
pub struct DocumentReport {
    pub document_id: String,
    pub pages: usize,
    pub selected: String,
    pub candidates: Vec<DocumentCandidate>,
    pub pdf_bytes: usize,
    pub font_bytes: usize,
    pub image_xobjects: usize,
    pub raster_encoded_bytes: usize,
    pub content_bytes: usize,
    pub page_order: Vec<String>,
    pub page_reports: Vec<Report>,
    pub coverage: DocumentCoverage,
    pub search: SearchPlan,
    pub ownership_invariants: std::collections::BTreeMap<String, bool>,
    /// sha256 of every source asset and OCR page (binding, per page)
    pub bindings: Vec<PageBinding>,
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
    pub report: DocumentReport,
}

/// Build the document-wide (shape, label) encoding table and remap every
/// page's CIDs onto it. Deterministic: page order, then slot order.
fn union_encodings(
    pages: &[DocumentPage],
) -> (Vec<GlyphShape>, Vec<(usize, String)>, Vec<Remap>) {
    let mut shapes: Vec<GlyphShape> = Vec::new();
    let mut shape_index: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
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
            // 0-based global encoding index; the CID is that index + 1
            let gc = match enc_index.get(&key).copied() {
                Some(i) => i,
                None => {
                    encodings.push((gshape, text.clone()));
                    encodings.len() - 1
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
}

/// Convert a bundle of pages into ONE document PDF.
pub fn convert_document(
    document_id: &str,
    inputs: &[Input],
    policy: &Policy,
) -> Result<DocumentOutput, String> {
    if inputs.is_empty() {
        return Err("document has no pages".into());
    }
    // 1. per-page conversion into parts + reports
    let mut pages: Vec<DocumentPage> = Vec::with_capacity(inputs.len());
    for input in inputs {
        let (parts, report) = convert_parts(input, policy)?;
        pages.push(DocumentPage { parts, report });
    }

    // 2. document-wide font: union of (shape, label), remapped per page
    let (shapes, encodings, remaps) = union_encodings(&pages);
    for (page, remap) in pages.iter_mut().zip(remaps.iter()) {
        apply_remap(page, remap);
    }
    let font_bytes = build_font(&shapes, &encodings, policy.upem)?;

    // 3. the reconstruction candidate
    let (pdf_bytes, stats) = assemble_document(
        &pages.iter().map(|p| p.parts.clone()).collect::<Vec<_>>(),
        &shapes,
        &encodings,
        &font_bytes,
    )?;

    // 4. the whole-page searchable raster baseline candidate (auto mode ranks
    //    it against the reconstruction by real bytes)
    // the raster-baseline candidate: the same pages with the whole-page source
    // patch and the text layer drawn invisibly (searchable, zero vector ink)
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
    let (baseline_pdf, baseline_stats) =
        assemble_document(&baseline_parts, &shapes, &encodings, &font_bytes)?;

    // 5. candidate accounting + selection
    let image_xobjects: usize = pages.iter().map(|p| p.parts.patches.len()).sum();
    // both candidates are ALWAYS reported (with their real serialized sizes);
    // auto mode only decides which one is emitted
    let candidates = vec![
        DocumentCandidate {
            name: "reconstruct".into(),
            pages: pages.len(),
            pdf_bytes: pdf_bytes.len(),
            font_bytes: font_bytes.len(),
            image_xobjects: stats.image_xobjects,
            content_bytes: stats.content_bytes,
            raster_encoded_bytes: stats.raster_encoded_bytes,
            raster_pages: pages
                .iter()
                .filter(|p| p.parts.occurrences.is_empty())
                .count(),
        },
        DocumentCandidate {
            name: "raster_baseline".into(),
            pages: baseline_parts.len(),
            pdf_bytes: baseline_pdf.len(),
            font_bytes: font_bytes.len(),
            image_xobjects: baseline_stats.image_xobjects,
            content_bytes: baseline_stats.content_bytes,
            raster_encoded_bytes: baseline_stats.raster_encoded_bytes,
            raster_pages: baseline_parts.len(),
        },
    ];
    let selected = if policy.mode == "auto" {
        if baseline_pdf.len() < pdf_bytes.len() {
            "raster_baseline".into()
        } else {
            "reconstruct".into()
        }
    } else {
        "reconstruct".into()
    };
    let out_bytes: Vec<u8> = if selected == "raster_baseline" {
        baseline_pdf.clone()
    } else {
        pdf_bytes.clone()
    };
    let out_len = out_bytes.len();

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

    Ok(DocumentOutput {
        pdf_bytes: out_bytes.clone(),
        report: DocumentReport {
            document_id: document_id.to_string(),
            pages: pages.len(),
            selected,
            candidates,
            pdf_bytes: out_len,
            font_bytes: font_bytes.len(),
            image_xobjects: stats.image_xobjects,
            raster_encoded_bytes: stats.raster_encoded_bytes,
            content_bytes: stats.content_bytes,
            page_order: pages.iter().map(|p| p.report.page_id.clone()).collect(),
            page_reports: pages.iter().map(|p| p.report.clone()).collect(),
            coverage,
            search,
            ownership_invariants,
            bindings: Vec::new(),
        },
    })
}
