//! Ordinary PDF import. Poppler owns PDF decoding; Tesseract supplies genuine
//! character geometry. Both feed the existing normalized-page/document path.
use scanweave_io::{convert, document, hocr, normalize};
use std::{path::Path, process::Command};

fn run(program: &str, args: &[&std::ffi::OsStr]) -> Result<Vec<u8>, String> {
    let output = Command::new(program)
        .args(args)
        .env("LC_ALL", "C")
        .output()
        .map_err(|e| {
            format!(
                "cannot run {program}: {e}. Install Poppler (pdfinfo/pdftoppm) and Tesseract OCR."
            )
        })?;
    if !output.status.success() {
        return Err(format!(
            "{program} failed ({}): {}",
            output.status,
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    Ok(output.stdout)
}

pub fn convert_pdf(args: &[String]) -> Result<(), String> {
    let input = args.first().ok_or("missing input PDF")?;
    let output = args.get(1).ok_or("usage: scanweave input.pdf output.pdf [--dpi 300] [--lang eng] [--profile clearscan|faithful]")?;
    for pair in args[2..].chunks(2) {
        if pair.len() != 2 || !matches!(pair[0].as_str(), "--dpi" | "--lang" | "--profile") {
            return Err(format!("unknown or incomplete option: {}", pair[0]));
        }
    }
    let dpi: u32 = super::arg_value(args, "--dpi")
        .unwrap_or_else(|| "300".into())
        .parse()
        .map_err(|_| "--dpi must be an integer")?;
    if !(72..=1200).contains(&dpi) {
        return Err("--dpi must be in 72..1200".into());
    }
    let lang = super::arg_value(args, "--lang").unwrap_or_else(|| "eng".into());
    let profile = super::arg_value(args, "--profile").unwrap_or_else(|| "clearscan".into());
    if profile != "faithful" && profile != "clearscan" {
        return Err("--profile must be clearscan or faithful".into());
    }
    let input = std::fs::canonicalize(input).map_err(|e| format!("read input PDF: {e}"))?;
    if Path::new(output).canonicalize().ok().as_ref() == Some(&input) {
        return Err("input and output must be different files".into());
    }
    let report_path = format!("{output}.json");
    if Path::new(&report_path).canonicalize().ok().as_ref() == Some(&input) {
        return Err("input and report must be different files".into());
    }
    let parent = Path::new(output)
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    if !parent.is_dir() {
        return Err(format!(
            "output directory does not exist: {}",
            parent.display()
        ));
    }
    let poppler_version = String::from_utf8_lossy(
        &Command::new("pdftoppm")
            .arg("-v")
            .output()
            .map_err(|e| format!("cannot run pdftoppm: {e}; install Poppler"))?
            .stderr,
    )
    .lines()
    .next()
    .unwrap_or("unknown")
    .to_string();
    let info = run("pdfinfo", &[input.as_os_str()])?;
    let info = String::from_utf8_lossy(&info);
    let pages: usize = info
        .lines()
        .find_map(|l| l.strip_prefix("Pages:"))
        .ok_or("pdfinfo did not report page count")?
        .trim()
        .parse()
        .map_err(|_| "invalid PDF page count")?;
    if pages == 0 || pages > 1000 {
        return Err("PDF must contain 1..1000 pages".into());
    }
    let work = tempfile::tempdir().map_err(|e| format!("create temporary workspace: {e}"))?;
    let tesseract_version = String::from_utf8_lossy(&run("tesseract", &["--version".as_ref()])?)
        .lines()
        .next()
        .unwrap_or("unknown")
        .to_string();
    let mut decoded_bytes = 0u64;
    let mut inputs = Vec::new();
    let mut provenance = Vec::new();
    let input_hash = scanweave_core::hash_hex(&std::fs::read(&input).map_err(|e| e.to_string())?);
    for page in 1..=pages {
        eprintln!("scanweave: rasterizing and recognizing page {page}/{pages}");
        let number = page.to_string();
        let resolution = dpi.to_string();
        let prefix = work.path().join(format!("page-{page:06}"));
        let details = run(
            "pdfinfo",
            &[
                "-f".as_ref(),
                number.as_ref(),
                "-l".as_ref(),
                number.as_ref(),
                input.as_os_str(),
            ],
        )?;
        let details = String::from_utf8_lossy(&details);
        let size = details
            .lines()
            .find(|l| l.contains(" size:"))
            .ok_or("pdfinfo did not report physical page size")?;
        let values: Vec<_> = size
            .split_once("size:")
            .unwrap()
            .1
            .split_whitespace()
            .collect();
        let mut width: f64 = values
            .first()
            .ok_or("missing page width")?
            .parse()
            .map_err(|_| "invalid page width")?;
        let mut height: f64 = values
            .get(2)
            .ok_or("missing page height")?
            .parse()
            .map_err(|_| "invalid page height")?;
        let rotation: i32 = details
            .lines()
            .find(|l| l.contains(" rot:"))
            .and_then(|l| l.split_once("rot:"))
            .and_then(|(_, v)| v.trim().parse().ok())
            .unwrap_or(0);
        if rotation.rem_euclid(180) == 90 {
            std::mem::swap(&mut width, &mut height);
        }
        if !width.is_finite()
            || !height.is_finite()
            || width <= 0.0
            || height <= 0.0
            || width * height * (dpi as f64 / 72.0).powi(2)
                > scanweave_core::Limits::m0_defaults().max_page_pixels as f64
        {
            return Err(format!("page {page} exceeds supported raster dimensions"));
        }
        run(
            "pdftoppm",
            &[
                "-f".as_ref(),
                number.as_ref(),
                "-l".as_ref(),
                number.as_ref(),
                "-singlefile".as_ref(),
                "-cropbox".as_ref(),
                "-r".as_ref(),
                resolution.as_ref(),
                "-png".as_ref(),
                input.as_os_str(),
                prefix.as_os_str(),
            ],
        )?;
        let png = prefix.with_extension("png");
        let bytes = std::fs::read(&png).map_err(|e| e.to_string())?;
        let image = image::load_from_memory(&bytes)
            .map_err(|e| e.to_string())?
            .to_rgb8();
        decoded_bytes += image.as_raw().len() as u64;
        if decoded_bytes > 512 * 1024 * 1024 {
            return Err(
                "document exceeds 512 MiB decoded page budget; split into smaller PDFs".into(),
            );
        }
        if image.width() as u64 * image.height() as u64
            > scanweave_core::Limits::m0_defaults().max_page_pixels
        {
            return Err(format!("page {page} exceeds raster pixel budget"));
        }
        run(
            "tesseract",
            &[
                png.as_os_str(),
                prefix.as_os_str(),
                "-l".as_ref(),
                lang.as_ref(),
                "--dpi".as_ref(),
                resolution.as_ref(),
                "-c".as_ref(),
                "hocr_char_boxes=1".as_ref(),
                "hocr".as_ref(),
            ],
        )?;
        let ocr_bytes = std::fs::read(prefix.with_extension("hocr")).map_err(|e| e.to_string())?;
        let doc = hocr::parse_hocr(&ocr_bytes, image.width(), image.height())
            .map_err(|e| e.to_string())?;
        if doc.words.is_empty() {
            eprintln!("scanweave: page {page}: Tesseract recognized no words; preserving the page image without searchable text for this page");
        }
        let binding = normalize::Binding {
            asset_path: format!("page-{page:06}.png"),
            file_sha256: scanweave_core::hash_hex(&bytes),
            pixel_sha256: scanweave_core::pixel_hash::pixel_hash(
                scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
                image.width() as u64,
                image.height() as u64,
                scanweave_core::pixel_hash::ColourTag::Srgb,
                None,
                image.as_raw(),
            )
            .map_err(|e| e.to_string())?,
        };
        let mut normalized = normalize::build_normalized_page(
            &normalize::ImageMeta {
                width: image.width(),
                height: image.height(),
            },
            &doc,
            Some(dpi as f64),
            &binding,
        )
        .map_err(|e| e.to_string())?;
        normalized.producer.name = "Tesseract".into();
        normalized.producer.version = tesseract_version.clone();
        normalized.producer.languages = vec![lang.clone()];
        normalized.page_id = format!("p{page:06}");
        normalized.page.width_pt = width;
        normalized.page.height_pt = height;
        normalized.page.raster_to_page_pt = [
            width / image.width() as f64,
            0.0,
            0.0,
            -height / image.height() as f64,
            0.0,
            height,
        ];
        normalized
            .validate(&scanweave_core::Limits::m0_defaults())
            .map_err(|e| e.to_string())?;
        normalized
            .verify_binding(image.as_raw())
            .map_err(|e| e.to_string())?;
        inputs.push(convert::input_from_ocr_page(
            image.as_raw(),
            image.width(),
            image.height(),
            &normalized.page_id,
            &normalized,
        ));
        provenance.push(serde_json::json!({"page":page,"width_pt":width,"height_pt":height,"raster_width":image.width(),"raster_height":image.height(),"raster_file_sha256":binding.file_sha256,"pixel_sha256":binding.pixel_sha256,"ocr_words":doc.words.len(),"ocr_granularity":normalized.granularity,"hocr_sha256":scanweave_core::hash_hex(&ocr_bytes),"hocr":String::from_utf8_lossy(&ocr_bytes),"rasterizer_args":["-f",number.as_str(),"-l",number.as_str(),"-singlefile","-cropbox","-r",resolution.as_str(),"-png"],"tesseract_args":["-l",lang.as_str(),"--dpi",resolution.as_str(),"-c","hocr_char_boxes=1","hocr"],"ocr":normalized.producer}));
    }
    let policy = convert::Policy {
        dpi: dpi as f64,
        glyph_dictionary: if profile == "clearscan" {
            "visual".into()
        } else {
            "off".into()
        },
        profile,
        ..Default::default()
    };
    let converted = document::convert_document("pdf-input", &inputs, &policy)?;
    // Unique, same-directory temporary publication avoids shared .tmp races.
    let parent = Path::new(output)
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let mut staged = tempfile::NamedTempFile::new_in(parent).map_err(|e| e.to_string())?;
    use std::io::Write;
    staged
        .write_all(&converted.pdf_bytes)
        .map_err(|e| e.to_string())?;

    let report = serde_json::json!({"poppler_version":poppler_version,"input_sha256":input_hash,"rasterization_dpi":dpi,"ocr_language":lang,"pages":provenance,"conversion":converted.report});
    let mut staged_report = tempfile::NamedTempFile::new_in(parent).map_err(|e| e.to_string())?;
    staged_report
        .write_all(&serde_json::to_vec_pretty(&report).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    // Both files are complete before publication. Two renames are not a single
    // transaction; report the rare second-rename failure explicitly.
    staged.persist(output).map_err(|e| e.to_string())?;
    staged_report
        .persist(&report_path)
        .map_err(|e| format!("PDF written but report publication failed: {e}"))?;
    println!(
        "scanweave: wrote {output} ({} pages, {} bytes); report {report_path}",
        pages,
        converted.pdf_bytes.len()
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn missing_dependency_has_install_hint() {
        let message = super::run("scanweave-nonexistent-test-dependency", &[]).unwrap_err();
        assert!(message.contains("Install Poppler"));
    }
    #[test]
    fn report_cannot_overwrite_input() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("output.pdf.json");
        std::fs::write(&source, b"source").unwrap();
        let output = dir.path().join("output.pdf");
        let error = super::convert_pdf(&[
            source.to_string_lossy().into(),
            output.to_string_lossy().into(),
        ])
        .unwrap_err();
        assert!(error.contains("input and report"));
        assert_eq!(std::fs::read(source).unwrap(), b"source");
    }
    #[test]
    fn validates_options_before_reading_input() {
        for args in [
            vec!["missing.pdf", "out.pdf", "--dpi", "0"],
            vec!["missing.pdf", "out.pdf", "--unknown", "x"],
            vec!["missing.pdf", "out.pdf", "--lang"],
        ] {
            assert!(
                super::convert_pdf(&args.into_iter().map(str::to_string).collect::<Vec<_>>())
                    .is_err()
            );
        }
    }
}
