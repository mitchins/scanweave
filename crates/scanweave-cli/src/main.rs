//! ScanWeave CLI: one-page conversion (M1-A) and multi-page documents (M1-B).

use std::process::ExitCode;

fn usage() -> ! {
    eprintln!(
        "scanweave build <input.png> --ocr <input.hocr> [--dpi N] [--mode reconstruct|auto] \
         [--min-ink-iou F] [--profile faithful|clearscan|canonical-experimental]
         [--glyph-dictionary off|visual] [--gx-uniform-glyph-scale]
         --output <out.pdf> --report <out.json>\n\
         scanweave build --bundle <document.json> [--mode reconstruct|auto] [--min-ink-iou F] \
         [--glyph-dictionary off|visual] [--gx-uniform-glyph-scale] \
         --output <out.pdf> --report <out.json>"
    );
    std::process::exit(2);
}

/// Parse the optional fidelity policy threshold. The SPEC's conservative
/// development default (0.98) applies when the flag is absent; lowering it is
/// an explicit, recorded policy decision.
fn arg_f64(args: &[String], flag: &str, default: f64) -> Result<f64, String> {
    match arg_value(args, flag) {
        Some(v) => v
            .parse::<f64>()
            .map_err(|_| format!("{flag} must be a number in [0,1]"))
            .and_then(|f| {
                if (0.0..=1.0).contains(&f) {
                    Ok(f)
                } else {
                    Err(format!("{flag} must be within [0,1]"))
                }
            }),
        None => Ok(default),
    }
}

fn image_encoding(args: &[String]) -> Result<scanweave_io::page_pdf::ImageEncodingOptions, String> {
    use scanweave_io::page_pdf::ImageEncodingOptions;
    let mut options = ImageEncodingOptions::default();
    match arg_value(args, "--pdf-image-variant").as_deref().unwrap_or("optimized") {
        "baseline" => { options.reuse_identical = false; options.grayscale_equal_channels = false; options.predictor = 1; }
        "reuse" => { options.reuse_identical = true; options.grayscale_equal_channels = false; options.predictor = 1; }
        "gray" | "optimized" => { options.reuse_identical = true; options.grayscale_equal_channels = true; options.predictor = 1; }
        "gray-tiff" => { options.reuse_identical = true; options.grayscale_equal_channels = true; options.predictor = 2; }
        "gray-up" => { options.reuse_identical = true; options.grayscale_equal_channels = true; options.predictor = 12; }
        other => return Err(format!("unsupported --pdf-image-variant {other} (baseline | reuse | gray | gray-tiff | gray-up)")),
    }
    Ok(options)
}

/// The bundle path: one document, N pages, one searchable PDF.
fn build_bundle(args: &[String]) -> Result<(), String> {
    let bundle_path = arg_value(args, "--bundle").ok_or("missing --bundle")?;
    let dpi: f64 = arg_value(args, "--dpi")
        .map(|v| v.parse::<f64>())
        .transpose()
        .map_err(|_| "--dpi must be a number".to_string())?
        .unwrap_or(300.0);
    let output = arg_value(args, "--output").ok_or("missing --output")?;
    let report = arg_value(args, "--report").ok_or("missing --report")?;
    let mode = arg_value(args, "--mode").unwrap_or_else(|| "reconstruct".into());
    if mode != "reconstruct" && mode != "auto" {
        return Err(format!(
            "unsupported --mode {mode} (M1-B: reconstruct | auto)"
        ));
    }
    let bundle_bytes =
        std::fs::read(&bundle_path).map_err(|e| format!("read {bundle_path}: {e}"))?;
    let bundle = scanweave_core::bundle::Bundle::parse_bytes(&bundle_bytes)
        .map_err(|e| format!("bundle parse: {e}"))?;
    let root = std::path::Path::new(&bundle_path)
        .parent()
        .unwrap_or_else(|| std::path::Path::new("."));
    bundle
        .verify_pairing(root, &scanweave_core::Limits::m0_defaults())
        .map_err(|e| format!("bundle pairing: {e}"))?;

    // per page, in bundle order: source raster + normalized OCR page + binding
    let mut inputs = Vec::with_capacity(bundle.pages.len());
    let mut bindings = Vec::with_capacity(bundle.pages.len());
    for p in &bundle.pages {
        let src = bundle
            .sources
            .iter()
            .find(|s| s.source_id == p.source_id)
            .ok_or_else(|| format!("page {}: unknown source {}", p.page_id, p.source_id))?;
        if p.source_page_index != 0 {
            return Err(format!(
                "page {}: source_page_index {} unsupported (M1-B: single-image sources)",
                p.page_id, p.source_page_index
            ));
        }
        if !matches!(src.kind, scanweave_core::bundle::BundleSourceKind::Image) {
            return Err(format!(
                "page {}: source kind {:?} unsupported (M1-B: image sources only)",
                p.page_id, src.kind
            ));
        }
        let asset = root.join(&src.asset_path);
        let rgb_bytes =
            std::fs::read(&asset).map_err(|e| format!("read {}: {e}", asset.display()))?;
        let img = image::load_from_memory(&rgb_bytes)
            .map_err(|e| format!("decode {}: {e}", asset.display()))?;
        let img = img.to_rgb8();
        let (w, h) = (img.width(), img.height());
        let ocr_bytes = std::fs::read(root.join(&p.ocr_page_path))
            .map_err(|e| format!("read {}: {e}", p.ocr_page_path))?;
        let ocr = scanweave_core::ocr_page::OcrPage::parse_bytes(&ocr_bytes)
            .map_err(|e| format!("ocr {}: {e}", p.ocr_page_path))?;
        ocr.validate(&scanweave_core::Limits::m0_defaults())
            .map_err(|e| format!("ocr validate {}: {e}", p.ocr_page_path))?;
        // SPEC §4.2 pixel binding: the OCR page's declared canonical hash must
        // match the decoded source pixels before any reconstruction runs
        ocr.verify_binding(img.as_raw())
            .map_err(|e| format!("page {}: pixel binding: {e}", p.page_id))?;
        bindings.push(scanweave_io::document::PageBinding {
            page_id: p.page_id.clone(),
            source_sha256: src.file_sha256.clone(),
            ocr_sha256: p.ocr_page_sha256.clone(),
            pixel_sha256: scanweave_core::pixel_hash::pixel_hash(
                scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
                w as u64,
                h as u64,
                scanweave_core::pixel_hash::ColourTag::Srgb,
                None,
                img.as_raw(),
            )
            .map_err(|e| e.to_string())?,
        });
        inputs.push(scanweave_io::convert::input_from_ocr_page(
            img.as_raw(),
            w,
            h,
            &p.page_id,
            &ocr,
        ));
    }

    let min_ink_iou = arg_f64(args, "--min-ink-iou", 0.98)?;
    let profile = arg_value(args, "--profile").unwrap_or_else(|| "faithful".into());
    if profile != "faithful" && profile != "clearscan" && profile != "canonical-experimental" {
        return Err(format!(
            "unsupported --profile {profile} (faithful | clearscan | canonical-experimental)"
        ));
    }
    let glyph_dictionary = arg_value(args, "--glyph-dictionary").unwrap_or_else(|| {
        if profile == "clearscan" {
            "visual".into()
        } else {
            "off".into()
        }
    });
    if glyph_dictionary != "off" && glyph_dictionary != "visual" {
        return Err(format!(
            "unsupported --glyph-dictionary {glyph_dictionary} (M1-D: off | visual)"
        ));
    }
    let image_encoding = image_encoding(args)?;
    let gx_uniform_glyph_scale = args.iter().any(|a| a == "--gx-uniform-glyph-scale");
    if gx_uniform_glyph_scale && profile != "canonical-experimental" {
        return Err("--gx-uniform-glyph-scale requires --profile canonical-experimental".into());
    }
    let policy = scanweave_io::convert::Policy {
        mode,
        dpi,
        min_ink_iou,
        profile,
        gx_uniform_glyph_scale,
        glyph_dictionary,
        image_encoding,
        ..scanweave_io::convert::Policy::default()
    };
    let mut out = scanweave_io::document::convert_document(&bundle.document_id, &inputs, &policy)
        .map_err(|e| e.to_string())?;
    out.report.bindings = bindings;

    let tmp = format!("{output}.tmp");
    let tmp_report = format!("{report}.tmp");
    std::fs::write(&tmp, &out.pdf_bytes).map_err(|e| format!("write {tmp}: {e}"))?;
    std::fs::write(
        &tmp_report,
        serde_json::to_vec_pretty(&out.report).map_err(|e| e.to_string())?,
    )
    .map_err(|e| format!("write {tmp_report}: {e}"))?;
    std::fs::rename(&tmp, &output).map_err(|e| format!("rename {output}: {e}"))?;
    std::fs::rename(&tmp_report, &report).map_err(|e| format!("rename {report}: {e}"))?;
    println!(
        "build OK: document {} | {} pages, {}B pdf, {}B font, selected={} candidates={:?}",
        bundle.document_id,
        out.report.pages,
        out.report.pdf_bytes,
        out.report.font_bytes,
        out.report.selected,
        out.report
            .candidates
            .iter()
            .map(|c| (c.name.as_str(), c.pdf_bytes))
            .collect::<Vec<_>>()
    );
    Ok(())
}

fn arg_value(args: &[String], flag: &str) -> Option<String> {
    args.iter()
        .position(|a| a == flag)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

fn build(args: &[String]) -> Result<(), String> {
    let input = args
        .first()
        .filter(|s| !s.starts_with("--"))
        .cloned()
        .ok_or("missing positional input image")?;
    let ocr = arg_value(args, "--ocr").ok_or("missing --ocr")?;
    let dpi: f64 = arg_value(args, "--dpi")
        .map(|v| v.parse::<f64>())
        .transpose()
        .map_err(|_| "--dpi must be a number".to_string())?
        .ok_or("missing --dpi (no default guess)")?;
    let output = arg_value(args, "--output").ok_or("missing --output")?;
    let report = arg_value(args, "--report").ok_or("missing --report")?;
    let mode = arg_value(args, "--mode").unwrap_or_else(|| "reconstruct".into());
    if mode != "reconstruct" && mode != "auto" {
        return Err(format!(
            "unsupported --mode {mode} (M1-B: reconstruct | auto)"
        ));
    }

    let rgb_bytes = std::fs::read(&input).map_err(|e| format!("read {input}: {e}"))?;
    let ocr_bytes = std::fs::read(&ocr).map_err(|e| format!("read {ocr}: {e}"))?;
    let img = image::load_from_memory(&rgb_bytes).map_err(|e| format!("decode {input}: {e}"))?;
    let img = img.to_rgb8();
    let (w, h) = (img.width(), img.height());

    // --ocr accepts either foreign hOCR or the already-normalized ocr.json
    // (sniffed by the leading '{')
    let trimmed = ocr_bytes
        .iter()
        .copied()
        .skip_while(|b| b.is_ascii_whitespace())
        .collect::<Vec<u8>>();
    let ocr_json = trimmed.first() == Some(&b'{');

    // --ocr accepts either foreign hOCR or the already-normalized ocr.json
    // (sniffed by the leading '{'); both paths produce a normalized OcrPage
    let page = if ocr_json {
        let page: scanweave_core::ocr_page::OcrPage =
            serde_json::from_slice(&ocr_bytes).map_err(|e| format!("parse {ocr}: {e}"))?;
        page
    } else {
        let doc = scanweave_io::hocr::parse_hocr(&ocr_bytes, w, h).map_err(|e| e.to_string())?;
        let file_sha = scanweave_core::hash_hex(&rgb_bytes);
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
            asset_path: std::path::Path::new(&input)
                .file_name()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default(),
            file_sha256: file_sha,
            pixel_sha256: pixel_sha,
        };
        scanweave_io::normalize::build_normalized_page(
            &scanweave_io::normalize::ImageMeta {
                width: w,
                height: h,
            },
            &doc,
            Some(dpi),
            &binding,
        )
        .map_err(|e| e.to_string())?
    };
    page.validate(&scanweave_core::Limits::m0_defaults())
        .map_err(|e| e.to_string())?;
    // SPEC §4.2: the OCR page declares a canonical pixel hash for this raster;
    // refuse to work on pixels that do not match the declared binding
    page.verify_binding(img.as_raw())
        .map_err(|e| format!("binding {input}/{ocr}: {e}"))?;
    let input =
        scanweave_io::convert::input_from_ocr_page(img.as_raw(), w, h, &page.page_id, &page);

    let min_ink_iou = arg_f64(args, "--min-ink-iou", 0.98)?;
    let profile = arg_value(args, "--profile").unwrap_or_else(|| "faithful".into());
    let glyph_dictionary = arg_value(args, "--glyph-dictionary").unwrap_or_else(|| {
        if profile == "clearscan" {
            "visual".into()
        } else {
            "off".into()
        }
    });
    let image_encoding = image_encoding(args)?;
    let gx_uniform_glyph_scale = args.iter().any(|a| a == "--gx-uniform-glyph-scale");
    if gx_uniform_glyph_scale && profile != "canonical-experimental" {
        return Err("--gx-uniform-glyph-scale requires --profile canonical-experimental".into());
    }
    let policy = scanweave_io::convert::Policy {
        mode,
        dpi,
        min_ink_iou,
        profile,
        gx_uniform_glyph_scale,
        glyph_dictionary,
        image_encoding,
        ..scanweave_io::convert::Policy::default()
    };
    let out = scanweave_io::convert::convert(&input, &policy).map_err(|e| e.to_string())?;

    // atomic: temporary on the same filesystem, then rename
    let tmp = format!("{output}.tmp");
    let tmp_report = format!("{report}.tmp");
    std::fs::write(&tmp, &out.pdf_bytes).map_err(|e| format!("write {tmp}: {e}"))?;
    std::fs::write(
        &tmp_report,
        serde_json::to_vec_pretty(&out.report).map_err(|e| e.to_string())?,
    )
    .map_err(|e| format!("write {tmp_report}: {e}"))?;
    std::fs::rename(&tmp, &output).map_err(|e| format!("rename {output}: {e}"))?;
    std::fs::rename(&tmp_report, &report).map_err(|e| format!("rename {report}: {e}"))?;
    println!(
        "build OK: {} | {}B pdf, {}B font, {} raster regions, {}B restored raster",
        out.report.page_id,
        out.report.pdf_bytes,
        out.report.font_bytes,
        out.report.fallback_reasons.values().sum::<usize>(),
        out.report.raster_bytes
    );
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(|s| s.as_str()) {
        Some("build") => {
            if args[1..].iter().any(|a| a == "--bundle") {
                match build_bundle(&args[1..]) {
                    Ok(()) => ExitCode::SUCCESS,
                    Err(e) => {
                        eprintln!("scanweave build --bundle failed: {e}");
                        ExitCode::from(2)
                    }
                }
            } else {
                match build(&args[1..]) {
                    Ok(()) => ExitCode::SUCCESS,
                    Err(e) => {
                        eprintln!("scanweave build failed: {e}");
                        ExitCode::from(2)
                    }
                }
            }
        }
        _ => usage(),
    }
}
