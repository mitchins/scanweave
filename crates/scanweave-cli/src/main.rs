//! ScanWeave CLI (M1-A): one-page conversion.

use std::process::ExitCode;

fn usage() -> ! {
    eprintln!(
        "scanweave build <input.png> --ocr <input.hocr> [--dpi N] [--mode reconstruct] \
         --output <out.pdf> --report <out.json>"
    );
    std::process::exit(2);
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
    if mode != "reconstruct" {
        return Err(format!("unsupported --mode {mode} (M1-A: reconstruct only)"));
    }

    let rgb_bytes = std::fs::read(&input).map_err(|e| format!("read {input}: {e}"))?;
    let hocr_bytes = std::fs::read(&ocr).map_err(|e| format!("read {ocr}: {e}"))?;
    let img = image::load_from_memory(&rgb_bytes).map_err(|e| format!("decode {input}: {e}"))?;
    let img = img.to_rgb8();
    let (w, h) = (img.width(), img.height());

    let doc = scanweave_io::hocr::parse_hocr(&hocr_bytes, w, h).map_err(|e| e.to_string())?;
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
    let page = scanweave_io::normalize::build_normalized_page(
        &scanweave_io::normalize::ImageMeta { width: w, height: h },
        &doc,
        Some(dpi),
        &binding,
    )
    .map_err(|e| e.to_string())?;
    page.validate(&scanweave_core::Limits::m0_defaults()).map_err(|e| e.to_string())?;

    let spans: Vec<scanweave_io::convert::SpanInput> = page
        .spans
        .iter()
        .map(|s| scanweave_io::convert::SpanInput {
            id: s.id.clone(),
            text: s.text.clone(),
            polygon: s.polygon.clone(),
            symbols: s
                .symbols
                .iter()
                .map(|sym| scanweave_io::convert::SymbolInput {
                    id: sym.id.clone(),
                    range: (sym.text_range_utf8[0], sym.text_range_utf8[1]),
                    polygon: sym.polygon.clone(),
                })
                .collect(),
        })
        .collect();
    let input = scanweave_io::convert::Input {
        rgb: img.as_raw().to_vec(),
        width: w,
        height: h,
        page_id: page.page_id.clone(),
        spans,
    };
    let out = scanweave_io::convert::convert(&input, &scanweave_io::convert::Policy::default()).map_err(|e| e.to_string())?;

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
        page.page_id,
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
        Some("build") => match build(&args[1..]) {
            Ok(()) => ExitCode::SUCCESS,
            Err(e) => {
                eprintln!("scanweave build failed: {e}");
                ExitCode::from(2)
            }
        },
        _ => usage(),
    }
}
