//! M0 probe binary — thin CLI over the production implementation in scanweave-io.
//! Builds one page (raster PNG + normalized OCR JSON) into a reconstructed PDF
//! using the full M1-A pipeline (ownership plan → regions → patches + fonts).

use std::path::PathBuf;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("build") => cmd_build(&args[2..]),
        Some("hocr2json") => cmd_hocr2json(&args[2..]),
        other => {
            eprintln!("unknown subcommand {other:?}; expected build | hocr2json");
            ExitCode::from(2)
        }
    }
}

fn arg_of(args: &[String], flag: &str) -> Option<String> {
    args.iter().position(|a| a == flag).and_then(|i| args.get(i + 1)).cloned()
}

fn cmd_build(args: &[String]) -> ExitCode {
    let (Some(page_dir), Some(out_dir)) = (arg_of(args, "--page"), arg_of(args, "--out")) else {
        eprintln!("build requires --page <dir> --out <dir>");
        return ExitCode::from(2);
    };
    match m0_font_pdf::shim::build_page(&PathBuf::from(&page_dir), &PathBuf::from(&out_dir)) {
        Ok(log) => {
            println!("probe OK: page {} — {} visual units, {} fallback reasons, pdf={}B",
                     log.page_id, log.visual_units, log.fallback_reasons.len(), log.pdf_bytes);
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("probe FAILED: {e}");
            ExitCode::from(1)
        }
    }
}

fn cmd_hocr2json(args: &[String]) -> ExitCode {
    let (Some(hocr), Some(png), Some(out)) = (arg_of(args, "--hocr"), arg_of(args, "--png"), arg_of(args, "--out")) else {
        eprintln!("hocr2json requires --hocr <file> --png <png> --dpi <dpi> --out <json>");
        return ExitCode::from(2);
    };
    let dpi: f64 = arg_of(args, "--dpi").and_then(|v| v.parse().ok()).unwrap_or(0.0);
    if dpi <= 0.0 {
        eprintln!("--dpi must be > 0 (no default guess)");
        return ExitCode::from(2);
    }
    match m0_font_pdf::shim::hocr2json(&hocr, &png, dpi, &out) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("hocr2json FAILED: {e}");
            ExitCode::from(1)
        }
    }
}
