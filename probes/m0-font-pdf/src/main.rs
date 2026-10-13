//! M0 vertical probe: source raster mask → VTracer compound contour → TrueType
//! (write-fonts) → Type0/CIDFontType2 PDF (pdf-writer) with independent CID/GID/
//! Unicode mappings. Dev-scope binary; logic destined for core/io split at M1.
//!
//! Usage: m0-font-pdf build --page <dir-with-png+ocr.json> --out <dir>
//! Writes: <dir>/out.pdf, <dir>/out.ttf, <dir>/trace_log.json

mod baseline;
mod encoding;
mod fontbuild;
mod glyphs;
mod mask;
mod pdf;
mod trace;
mod units;

use std::path::PathBuf;
use std::process::ExitCode;

#[derive(Debug, Clone, serde::Serialize)]
pub struct StageMetrics {
    pub trace_max_px: f64,
    pub trace_p95_px: f64,
    pub curve_max_px: f64,
    pub quant_bound_px: f64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GlyphRecord {
    pub shape_key: String,
    pub label_text: String,
    pub gid: usize,
    pub cids: Vec<usize>,
    pub semantic_strings: Vec<String>,
    pub contours: usize,
    pub points: usize,
    pub em_px: f64,
    pub units_per_px: f64,
    pub stages: StageMetrics,
    pub budget_ok: bool,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct OccurrenceRecord {
    pub page_id: String,
    pub span_id: String,
    pub symbol_id: String,
    pub semantic_text: String,
    pub cid: usize,
    pub bbox_px: [f64; 4],
    /// SPEC §6.2 semantic owner (probe subset: visible_tounicode | unmapped)
    pub owner: String,
}

#[derive(Debug, Default, serde::Serialize)]
pub struct TraceLog {
    pub page_id: String,
    pub glyphs: Vec<GlyphRecord>,
    pub occurrences: Vec<OccurrenceRecord>,
    pub unowned_components: usize,
    pub em_px: f64,
    pub notes: Vec<String>,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("build") => cmd_build(&args[2..]),
        other => {
            eprintln!("unknown or missing subcommand {other:?}; expected: build --page <dir> --out <dir>");
            ExitCode::from(2)
        }
    }
}

fn keys_to_semantic(keys: &[encoding::EncodingKey], cid: usize) -> String {
    keys[cid - 1].semantic_string.clone()
}

fn arg_of(args: &[String], flag: &str) -> Option<String> {
    args.iter()
        .position(|a| a == flag)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

fn cmd_build(args: &[String]) -> ExitCode {
    let (Some(page_dir), Some(out_dir)) = (arg_of(args, "--page"), arg_of(args, "--out")) else {
        eprintln!("build requires --page <dir> and --out <dir>");
        return ExitCode::from(2);
    };
    match build(&PathBuf::from(page_dir), &PathBuf::from(out_dir)) {
        Ok(log) => {
            println!(
                "probe OK: page {} — {} glyph shapes, {} occurrences, unowned_components={}",
                log.page_id,
                log.glyphs.len(),
                log.occurrences.len(),
                log.unowned_components
            );
            for g in &log.glyphs {
                println!(
                    "  gid={} cids={:?} text={:?} contours={} points={} stages(max/curve/quant={:.3}/{:.3}/{:.3}px) budget_ok={}",
                    g.gid,
                    g.cids,
                    g.label_text,
                    g.contours,
                    g.points,
                    g.stages.trace_max_px,
                    g.stages.curve_max_px,
                    g.stages.quant_bound_px,
                    g.budget_ok
                );
            }
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("probe FAILED: {e}");
            ExitCode::from(1)
        }
    }
}

fn build(page_dir: &PathBuf, out_dir: &PathBuf) -> Result<TraceLog, String> {
    // locate page png + ocr json, paired by identical file stem
    let mut png: Option<PathBuf> = None;
    let mut ocr_path: Option<PathBuf> = None;
    for e in std::fs::read_dir(page_dir).map_err(|e| e.to_string())?.flatten() {
        let name = e.file_name().to_string_lossy().to_string();
        if name.ends_with(".png") {
            png = Some(e.path());
        } else if name.ends_with(".ocr.json") {
            ocr_path = Some(e.path());
        }
    }
    let stem_eq = match (&png, &ocr_path) {
        (Some(p), Some(o)) => p.file_stem().map(|s| s.to_string_lossy().to_string())
            == o.file_name().map(|s| s.to_string_lossy().to_string().trim_end_matches(".ocr.json").to_string()),
        _ => false,
    };
    if !stem_eq {
        return Err("png and ocr.json stems do not match — ambiguous page directory".into());
    }
    let png = png.ok_or("no .png in page dir")?;
    let ocr_path = ocr_path.ok_or("no .ocr.json in page dir")?;

    // 1. decode raster
    let img = image::open(&png).map_err(|e| e.to_string())?.to_rgb8();
    let (w, h) = (img.width(), img.height());

    // 2. parse + validate normalized OCR, verify pixel binding
    let ocr_bytes = std::fs::read(&ocr_path).map_err(|e| e.to_string())?;
    let page = scanweave_core::ocr_page::OcrPage::parse_bytes(&ocr_bytes)
        .and_then(|p| {
            p.validate(&scanweave_core::Limits::m0_defaults())?;
            Ok(p)
        })
        .map_err(|e| e.to_string())?;
    page.verify_binding(&img.as_raw())
        .map_err(|e| e.to_string())?;

    // 3. segmentation
    let seg = mask::segment(img.as_raw(), w, h);

    // 4. components + units per symbol observation
    let (unit_list, unowned) = units::extract_units(&seg, w, h, &page);

    let mut log = TraceLog {
        page_id: page.page_id.clone(),
        unowned_components: unowned,
        ..Default::default()
    };

    // 5. em scale: tallest unit ink height
    let em_px = unit_list
        .iter()
        .map(|u| u.height_px() as f64)
        .fold(f64::MIN, f64::max);
    log.em_px = em_px;
    let upem = 2048.0;
    let units_per_px = upem / em_px;

    // 6. trace distinct shapes
    let mut traced: Vec<trace::TracedShape> = Vec::new();
    let policy = trace::Budget::from_m0_policy();
    for u in &unit_list {
        if traced.iter().any(|t| t.shape_key == u.shape_key) {
            continue;
        }
        let t = trace::trace_shape(u, &policy, units_per_px)
            .map_err(|e| format!("trace failure for shape {}: {e}", u.shape_key))?;
        traced.push(t);
    }

    // 7. build glyph outlines + records
    let shapes = glyphs::build_glyph_shapes(&traced, units_per_px, &policy)?;

    // 8. allocate CIDs: key = (visual glyph, semantic string, writing mode,
    //    required metrics) — the SPEC §6.1 four-part key (encoding.rs). Same key
    //    dedups; mutating any component yields a distinct CID. Same shape with
    //    different labels shares the GID but gets distinct CIDs.
    let mut keys: Vec<encoding::EncodingKey> = Vec::new();
    let mut occ_meta: Vec<(usize, [f64; 4], String, String)> = Vec::new(); // glyph_idx, bbox, span, symbol
    let mut artwork: Vec<(usize, [f64; 4])> = Vec::new(); // glyph_idx, bbox (no semantics)
    for u in &unit_list {
        let glyph_idx = shapes.iter().position(|s| s.shape_key == u.shape_key).unwrap();
        if u.semantic_text.is_empty() {
            // unowned ink: vector artwork, never text (no invented Unicode)
            artwork.push((glyph_idx, u.bbox_px));
            continue;
        }
        let advance = (shapes[glyph_idx].ink_span_fu[0].ceil() as u16).saturating_add(2).max(1);
        keys.push(encoding::EncodingKey {
            visual_glyph_id: glyph_idx,
            semantic_string: u.semantic_text.clone(),
            writing_mode: encoding::WritingMode::Horizontal, // vertical is M4
            required_metrics: encoding::MetricsKey { advance, units_per_em: 2048 },
        });
        occ_meta.push((glyph_idx, u.bbox_px, u.span_id.clone(), u.symbol_id.clone()));
    }
    let cids = encoding::allocate_cids(&keys);
    // cid -> (glyph_idx, semantic) table for font/ToUnicode construction
    let mut encodings: Vec<(usize, String)> = Vec::new();
    for (k, _) in keys.iter().enumerate() {
        let cid = cids[k];
        if encodings.len() < cid {
            encodings.push((keys[k].visual_glyph_id, keys[k].semantic_string.clone()));
        }
    }
    let mut occurrences: Vec<(usize, usize, [f64; 4], String, String, String)> = Vec::new();
    for ((glyph_idx, bbox, span_id, symbol_id), cid) in occ_meta.iter().zip(cids.iter()) {
        occurrences.push((
            *glyph_idx,
            cid - 1, // pdf layer shifts +1 for the .notdef reservation
            *bbox,
            span_id.clone(),
            symbol_id.clone(),
            keys_to_semantic(&keys, *cid),
        ));
    }

    // 9. serialize font
    let font_bytes =
        fontbuild::build_font(&shapes, &encodings, upem as u16).map_err(|e| e.to_string())?;

    let contour_polylines: std::collections::HashMap<String, Vec<Vec<[f64; 2]>>> = traced
        .iter()
        .map(|t| (t.shape_key.clone(), t.polylines.clone()))
        .collect();

    // 10. assemble PDF
    let page_w_pt = page.page.width_pt as f32;
    let page_h_pt = page.page.height_pt as f32;
    let paper = seg.paper;
    let (pdf_bytes, breakdown) = pdf::assemble(
        &shapes,
        &encodings,
        &occurrences,
        &artwork,
        &contour_polylines,
        page_w_pt,
        page_h_pt,
        paper,
        font_bytes.clone(),
    )
    .map_err(|e| e.to_string())?;

    // B0 searchable raster control (same OCR, own path), plus a text-less twin
    // for render-neutrality verification (invisible text must paint nothing)
    let (b0_bytes, b0_breakdown) = baseline::assemble_raster(
        img.as_raw(),
        w,
        h,
        &encodings,
        &occurrences,
        page_w_pt,
        page_h_pt,
        font_bytes.clone(),
        &shapes,
    )
    .map_err(|e| e.to_string())?;
    let (b0_notext_bytes, _) = baseline::assemble_raster(
        img.as_raw(),
        w,
        h,
        &encodings,
        &[],
        page_w_pt,
        page_h_pt,
        font_bytes.clone(),
        &shapes,
    )
    .map_err(|e| e.to_string())?;

    // outputs
    std::fs::create_dir_all(out_dir).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("out.pdf"), &pdf_bytes).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("b0_raster.pdf"), &b0_bytes).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("b0_notext.pdf"), &b0_notext_bytes)
        .map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("out.ttf"), &font_bytes).map_err(|e| e.to_string())?;
    std::fs::write(
        out_dir.join("breakdown.json"),
        serde_json::to_vec_pretty(&serde_json::json!({
            "B2_reconstructed": breakdown,
            "B0_searchable_raster": b0_breakdown,
            "font_file": font_bytes.len(),
        }))
        .map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;

    // trace log
    for (gi, s) in shapes.iter().enumerate() {
        let cids: Vec<usize> = encodings
            .iter()
            .enumerate()
            .filter(|(_, (g, _))| *g == gi)
            .map(|(i, _)| i)
            .collect();
        let texts: Vec<String> = cids.iter().map(|i| encodings[*i].1.clone()).collect();
        log.glyphs.push(GlyphRecord {
            shape_key: s.shape_key.clone(),
            label_text: texts.first().cloned().unwrap_or_default(),
            gid: gi + 1, // gid 0 = .notdef
            cids,
            semantic_strings: texts,
            contours: s.num_contours,
            points: s.num_points,
            em_px,
            units_per_px,
            stages: s.stages.clone(),
            budget_ok: s.stages.trace_max_px <= policy.trace_max
                && s.stages.curve_max_px <= policy.curve_max
                && s.stages.quant_bound_px <= policy.quant_max,
        });
    }
    for (glyph_idx, cid, bbox, span_id, symbol_id, text) in &occurrences {
        log.occurrences.push(OccurrenceRecord {
            page_id: page.page_id.clone(),
            span_id: span_id.clone(),
            symbol_id: symbol_id.clone(),
            semantic_text: text.clone(),
            cid: *cid,
            bbox_px: *bbox,
            owner: "visible_tounicode".into(),
        });
        let _ = glyph_idx;
    }
    for (glyph_idx, bbox) in &artwork {
        log.occurrences.push(OccurrenceRecord {
            page_id: page.page_id.clone(),
            span_id: "unowned".into(),
            symbol_id: "artwork".into(),
            semantic_text: String::new(),
            cid: usize::MAX,
            bbox_px: *bbox,
            owner: "unmapped".into(),
        });
        let _ = glyph_idx;
    }
    let log_path = out_dir.join("trace_log.json");
    std::fs::write(&log_path, serde_json::to_vec_pretty(&log).unwrap()).map_err(|e| e.to_string())?;
    Ok(log)
}
