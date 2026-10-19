//! M0 probe library — stable surface for probes and behavioral tests over the
//! production implementation in scanweave-io.
//!
//! The reconstruction algorithm, ownership model, assembly and reports live in
//! scanweave-io (see [`scanweave_io::convert`]); this crate only adapts the
//! workspace fixture format (a directory containing `<page>.png` +
//! `<page>.ocr.json`) for legacy probes and behavior tests.

pub use scanweave_io::{
    baseline, encoding, fontbuild, glyphs, hocr, mask, normalize, page_pdf, ownership,
    pdf, trace, units,
};

pub use scanweave_io::convert::{convert, Input, Policy, Report};

#[derive(Debug, Clone, serde::Serialize)]
pub struct PatchRecord {
    pub bbox_px: [f64; 4],
    pub w: u32,
    pub h: u32,
    pub rgb_sha256: String,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GlyphStat {
    pub gid: usize,
    pub symbol_id: String,
    pub contours: usize,
    pub points: usize,
    pub budget_ok: bool,
    pub stages: scanweave_io::units::StageMetrics,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct OccurrenceRecord {
    pub page_id: String,
    pub span_id: String,
    pub symbol_id: String,
    pub semantic_text: String,
    pub owner: String,
}
pub mod shim {
    pub use crate::{build_page, convert_input, convert_with, hocr2json};
    pub use scanweave_io::convert::{Policy, Report};
    pub use scanweave_io::plan::RegionDisposition;
}
pub use scanweave_io::ownership::OwnershipPlan;
pub use scanweave_io::page_pdf::{Owner, Patch};
pub use scanweave_io::plan::{FallbackReason, Region, RegionDisposition, RegionKind};

use std::path::PathBuf;

/// Build the input the pipeline expects from a workspace page directory.
pub fn convert_input(
    rgb: &[u8],
    width: u32,
    height: u32,
    page_id: &str,
    page: &scanweave_core::ocr_page::OcrPage,
) -> Input {
    scanweave_io::convert::input_from_ocr_page(rgb, width, height, page_id, page)
}

/// Convert one page; `policy` override optional.
pub fn convert_with(
    input: &Input,
    policy: Option<&Policy>,
) -> Result<scanweave_io::convert::Output, String> {
    let p = policy.cloned().unwrap_or_default();
    convert(input, &p)
}

/// The probe's one-page build: loads the fixture dir, converts, writes the
/// artifacts, and returns the report in its legacy shape.
pub fn build_page(page_dir: &PathBuf, out_dir: &PathBuf) -> Result<Report, String> {
    let png = std::fs::read_dir(page_dir)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok())
        .find(|e| e.path().extension().is_some_and(|x| x == "png"))
        .map(|e| e.path())
        .ok_or("no .png in page dir")?;
    let ocr_path = std::fs::read_dir(page_dir)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok())
        .find(|e| e.file_name().to_string_lossy().ends_with(".ocr.json"))
        .map(|e| e.path())
        .ok_or("no .ocr.json in page dir")?;
    let img = image::open(&png).map_err(|e| e.to_string())?.to_rgb8();
    let (w, h) = (img.width(), img.height());
    let ocr_bytes = std::fs::read(&ocr_path).map_err(|e| e.to_string())?;
    let page = scanweave_core::ocr_page::OcrPage::parse_bytes(&ocr_bytes)
        .and_then(|p| {
            p.validate(&scanweave_core::Limits::m0_defaults())?;
            Ok(p)
        })
        .map_err(|e| e.to_string())?;
    page.verify_binding(img.as_raw()).map_err(|e| e.to_string())?;
    let input = convert_input(img.as_raw(), w, h, &page.page_id, &page);
    // the probe is the harness's measuring instrument: the converter-side
    // fidelity gate is disabled so the harness applies the SPEC's own gates to
    // the rendered output (the product CLI keeps the policy enforced)
    let out = convert(&input, &Policy { min_ink_iou: 0.0, ..Policy::default() })?;
    std::fs::create_dir_all(out_dir).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("out.pdf"), &out.pdf_bytes).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("b0_raster.pdf"), &out.b0_bytes).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("out.ttf"), &out.font_bytes).map_err(|e| e.to_string())?;
    std::fs::write(
        out_dir.join("report.json"),
        serde_json::to_vec_pretty(&out.report).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    // legacy trace-log shape used by the M0 qualification harness
    // legacy glyph shape: one record per distinct visual symbol, one CID per
    // distinct semantic string attached to that symbol (E0 four-part-key
    // statement: same glyph + same string = one CID; same glyph + different
    // strings = separate CIDs)
    use std::collections::BTreeMap;
    let mut per_unit: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for o in &out.report.occurrences {
        if o.semantic_text.is_empty() {
            continue; // artwork: unowned, not a glyph
        }
        // visual-unit identity: the box position is the glyph; the OCR label is
        // the string part of the key
        let unit = o.symbol_id.split('s').next().unwrap_or(&o.symbol_id).to_string();
        let e = per_unit.entry(unit).or_default();
        if !e.contains(&o.semantic_text) {
            e.push(o.semantic_text.clone());
        }
    }
    let mut legacy_glyphs: Vec<serde_json::Value> = Vec::new();
    let mut key_stats: Vec<(&str, usize, usize, bool, [f64; 4])> = out
        .report
        .glyph_stats
        .iter()
        .filter_map(|g| {
            // match a stat to a semantic text via its occurrence
            out.report.occurrences.iter().find(|o| o.symbol_id == g.symbol_id).map(|o| {
                (
                    o.semantic_text.as_str(),
                    g.contours,
                    g.points,
                    g.budget_ok,
                    [
                        g.stages.trace_max_px,
                        g.stages.trace_p95_px,
                        g.stages.curve_max_px,
                        g.stages.quant_bound_px,
                    ],
                )
            })
        })
        .collect();
    key_stats.sort_by(|a, b| a.0.cmp(b.0));
    let mut text_stat: std::collections::HashMap<&str, (usize, usize, bool, [f64; 4])> = std::collections::HashMap::new();
    for (text, contours, points, budget_ok, stages) in &key_stats {
        let e = text_stat.entry(text).or_insert((0, 0, true, [0.0; 4]));
        e.0 += *contours;
        e.1 += *points;
        e.2 &= *budget_ok;
        e.3[0] = e.3[0].max(stages[0]);
        e.3[1] = e.3[1].max(stages[1]);
        e.3[2] = e.3[2].max(stages[2]);
        e.3[3] = e.3[3].max(stages[3]);
    }
    for (idx, (unit, texts)) in per_unit.iter().enumerate() {
        let (contours, points, budget_ok, stages) = texts.first()
            .and_then(|t| text_stat.get(t.as_str()).copied())
            .unwrap_or((0, 0, true, [0.0; 4]));
        legacy_glyphs.push(serde_json::json!({
            "gid": idx,
            "symbol_id": unit,
            "semantic_strings": texts,
            "cids": texts,
            "contours": contours,
            "points": points,
            "stages": {
                "trace_max_px": stages[0],
                "trace_p95_px": stages[1],
                "curve_max_px": stages[2],
                "quant_bound_px": stages[3],
            },
            "budget_ok": budget_ok,
        }));
    }
    let legacy = serde_json::json!({
        "page_id": out.report.page_id,
        "glyphs": legacy_glyphs,
        "occurrences": out.report.occurrences,
        "unowned_components": out.report.components_artwork,
        "em_px": 0.0,
        "coverage": out.report.coverage,
        "regions": out.report.regions,
        "notes": [],
    });
    std::fs::write(out_dir.join("trace_log.json"), serde_json::to_vec_pretty(&legacy).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    // legacy shim report fields (io Report mirrors the shim shape)
    let mut report = Report {
        fidelity: out.report.fidelity.clone(),
        reconstruction: out.report.reconstruction.clone(),
        glyph_stats: out.report.glyph_stats.clone(),
        candidates: out.report.candidates.clone(),
        selected: out.report.selected.clone(),
        patches: out.report.patches.clone(),
        occurrences: out.report.occurrences.clone(),
        page_id: out.report.page_id.clone(),
        policy: out.report.policy.clone(),
        supplied_chars: out.report.supplied_chars,
        components_total: out.report.components_total,
        components_owned: out.report.components_owned,
        components_artwork: out.report.components_artwork,
        visual_units: out.report.visual_units,
        semantic_spans: out.report.semantic_spans,
        regions: out.report.regions.clone(),
        coverage: out.report.coverage.clone(),
        raster_ink_pixels_suppressed: out.report.raster_ink_pixels_suppressed,
        antialias_fringe_pixels_suppressed: out.report.antialias_fringe_pixels_suppressed,
        fallback_reasons: out.report.fallback_reasons.clone(),
        font_glyphs: out.report.font_glyphs,
        font_bytes: out.report.font_bytes,
        pdf_bytes: out.report.pdf_bytes,
        raster_bytes: out.report.raster_bytes,
        semantic_owner: out.report.semantic_owner.clone(),
        ownership_invariants: out.report.ownership_invariants.clone(),
        elapsed_ms: out.report.elapsed_ms,
    };
    report.elapsed_ms = out.report.elapsed_ms;
    let _ = &mut report;
    Ok(report)
}

/// The import path: hOCR PNG → normalized OCR JSON (validated).
pub fn hocr2json(hocr: &str, png: &str, dpi: f64, out: &str) -> Result<(), String> {
    let hocr_bytes = std::fs::read(hocr).map_err(|e| e.to_string())?;
    let img = image::open(png).map_err(|e| e.to_string())?.to_rgb8();
    let (w, h) = (img.width(), img.height());
    let doc = scanweave_io::hocr::parse_hocr(&hocr_bytes, w, h).map_err(|e| e.to_string())?;
    let file_sha = scanweave_core::hash_hex(&std::fs::read(png).map_err(|e| e.to_string())?);
    let pixel_sha = scanweave_core::pixel_hash::pixel_hash(
        scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
        w as u64,
        h as u64,
        scanweave_core::pixel_hash::ColourTag::Srgb,
        None,
        img.as_raw(),
    )
    .map_err(|e| e.to_string())?;
    let binding = scanweave_io::normalize::Binding {
        asset_path: std::path::Path::new(png)
            .file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default(),
        file_sha256: file_sha,
        pixel_sha256: pixel_sha,
    };
    let page = scanweave_io::normalize::build_normalized_page(
        &scanweave_io::normalize::ImageMeta { width: w, height: h },
        &doc,
        Some(dpi),
        &binding,
    )
    .map_err(|e| e.to_string())?;
    page.validate(&scanweave_core::Limits::m0_defaults()).map_err(|e| e.to_string())?;
    let value = serde_json::to_value(&page).map_err(|e| e.to_string())?;
    std::fs::write(out, serde_json::to_vec_pretty(&value).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    Ok(())
}
