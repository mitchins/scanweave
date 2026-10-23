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

// Confidence alone cannot prove recognition. Require several multi-character
// words with positive, page-bounded character boxes before accepting a retry.
fn reliable_words(doc: &hocr::HocrDocument, width: u32, height: u32) -> usize {
    doc.words
        .iter()
        .filter(|word| {
            word.confidence.unwrap_or(0.0) >= 70.0
                && word.text.chars().filter(|c| c.is_alphanumeric()).count() >= 3
                && !word.chars.is_empty()
                && word.chars.iter().all(|c| {
                    let (x0, y0, x1, y1) = c.bbox;
                    x0 >= 0
                        && y0 >= 0
                        && x1 > x0
                        && y1 > y0
                        && x1 <= width as i64
                        && y1 <= height as i64
                })
        })
        .count()
}

// Parse and validate Poppler's physical geometry before any page rasterization.
fn physical_page_size(details: &str, dpi: u32, page: usize) -> Result<(f64, f64), String> {
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
    Ok((width, height))
}

fn pdf_page_count(info: &str) -> Result<usize, String> {
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
    Ok(pages)
}

pub fn convert_pdf(args: &[String]) -> Result<(), String> {
    let input = args.first().ok_or("missing input PDF")?;
    let output = args.get(1).ok_or("usage: scanweave input.pdf output.pdf [--dpi 300] [--lang eng] [--profile clearscan|faithful]")?;
    for pair in args[2..].chunks(2) {
        if pair.len() != 2
            || !matches!(
                pair[0].as_str(),
                "--dpi" | "--lang" | "--profile" | "--glyph-sharing"
            )
        {
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
    let sharing = super::arg_value(args, "--glyph-sharing").unwrap_or_else(|| "off".into());
    if !matches!(sharing.as_str(), "off" | "experimental")
        || (sharing == "experimental" && profile != "clearscan")
    {
        return Err("--glyph-sharing must be off or experimental (ClearScan only)".into());
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
    let pages = pdf_page_count(&info)?;
    let work = tempfile::tempdir().map_err(|e| format!("create temporary workspace: {e}"))?;
    let tesseract_version = String::from_utf8_lossy(&run("tesseract", &["--version".as_ref()])?)
        .lines()
        .next()
        .unwrap_or("unknown")
        .to_string();
    let source_images = if profile == "clearscan" {
        scanweave_io::source_image::simple_page_images(
            std::fs::read(&input).map_err(|e| e.to_string())?,
        )
    } else {
        Vec::new()
    };
    let mut decoded_bytes = 0u64;
    let mut inputs = Vec::new();
    let mut provenance = Vec::new();
    let import_started = std::time::Instant::now();
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
        let (width, height) = physical_page_size(&details, dpi, page)?;
        let png = prefix.with_extension("png");
        let native = source_images
            .get(page - 1)
            .and_then(Option::as_ref)
            .filter(|source| {
                let (w, h) = source.dimensions();
                // At nominal resolution, do not resample a 3301-pixel original to
                // 3300 pixels merely because page points were rounded on import.
                (w as f64 * 72.0 / width / dpi as f64 - 1.0).abs() < 0.01
                    && (h as f64 * 72.0 / height / dpi as f64 - 1.0).abs() < 0.01
            });
        let image = if let Some(source) = native {
            let (w, h) = source.dimensions();
            let rgb = source.decode_rgb()?;
            let image =
                image::RgbImage::from_raw(w, h, rgb).ok_or("invalid native source image")?;
            image.save(&png).map_err(|e| e.to_string())?;
            image
        } else {
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
            let bytes = std::fs::read(&png).map_err(|e| e.to_string())?;
            image::load_from_memory(&bytes)
                .map_err(|e| e.to_string())?
                .to_rgb8()
        };
        let bytes = std::fs::read(&png).map_err(|e| e.to_string())?;
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
                "--psm".as_ref(),
                "3".as_ref(),
                "hocr".as_ref(),
            ],
        )?;
        let mut ocr_bytes =
            std::fs::read(prefix.with_extension("hocr")).map_err(|e| e.to_string())?;
        let mut doc = hocr::parse_hocr(&ocr_bytes, image.width(), image.height())
            .map_err(|e| e.to_string())?;
        let mut selected_psm = 3;
        let baseline_reliable = reliable_words(&doc, image.width(), image.height());
        let mut retry_reliable = None;
        if profile == "clearscan" && doc.words.len() <= 20 && baseline_reliable < 3 {
            let retry = work.path().join(format!("retry-{page:06}"));
            run(
                "tesseract",
                &[
                    png.as_os_str(),
                    retry.as_os_str(),
                    "-l".as_ref(),
                    lang.as_ref(),
                    "--dpi".as_ref(),
                    resolution.as_ref(),
                    "--psm".as_ref(),
                    "6".as_ref(),
                    "-c".as_ref(),
                    "hocr_char_boxes=1".as_ref(),
                    "hocr".as_ref(),
                ],
            )?;
            let bytes = std::fs::read(retry.with_extension("hocr")).map_err(|e| e.to_string())?;
            let candidate = hocr::parse_hocr(&bytes, image.width(), image.height())
                .map_err(|e| e.to_string())?;
            let supported = reliable_words(&candidate, image.width(), image.height());
            retry_reliable = Some(supported);
            if supported >= 6 && supported >= baseline_reliable * 2 + 4 {
                doc = candidate;
                ocr_bytes = bytes;
                selected_psm = 6;
            }
        }
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
        provenance.push(serde_json::json!({"page":page,"width_pt":width,"height_pt":height,"raster_width":image.width(),"raster_height":image.height(),"raster_import":if native.is_some(){"native_source_samples"}else{"Poppler"},"raster_file_sha256":binding.file_sha256,"pixel_sha256":binding.pixel_sha256,"ocr_words":doc.words.len(),"selected_psm":selected_psm,"baseline_reliable_words":baseline_reliable,"retry_reliable_words":retry_reliable,"ocr_granularity":normalized.granularity,"hocr_sha256":scanweave_core::hash_hex(&ocr_bytes),"hocr":String::from_utf8_lossy(&ocr_bytes),"native_source":native.map(|source|source.provenance()),"rasterizer_args":if native.is_some(){serde_json::Value::Null}else{serde_json::json!(["-f",number.as_str(),"-l",number.as_str(),"-singlefile","-cropbox","-r",resolution.as_str(),"-png"])},"tesseract_args":["-l",lang.as_str(),"--dpi",resolution.as_str(),"--psm",selected_psm.to_string(),"-c","hocr_char_boxes=1","hocr"],"ocr":normalized.producer}));
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
    let import_ms = import_started.elapsed().as_millis();
    let converted = if sharing == "experimental" {
        let directory = std::path::PathBuf::from(format!("{output}.font04"));
        let mut intervention =
            |pages: &mut [document::DocumentPage], donors: &[Vec<scanweave_io::units::Unit>]| {
                super::font04::experiment(pages, donors, &directory)
            };
        document::convert_document_with_transform(
            "pdf-input",
            &inputs,
            &policy,
            &source_images,
            Some(&mut intervention),
        )?
    } else {
        document::convert_document_with_sources("pdf-input", &inputs, &policy, &source_images)?
    };
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

    let report = serde_json::json!({"import_ms":import_ms,"poppler_version":poppler_version,"input_sha256":input_hash,"rasterization_dpi":dpi,"ocr_language":lang,"pages":provenance,"conversion":converted.report});
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
    fn page_count_keeps_first_match_and_existing_errors() {
        use super::pdf_page_count as parse;
        assert_eq!(parse("Pages: 2\nPages: 3").unwrap(), 2);
        assert_eq!(parse("Pages: 1000").unwrap(), 1000);
        for (input, error) in [
            ("", "pdfinfo did not report page count"),
            ("Pages: invalid", "invalid PDF page count"),
            ("Pages: -1", "invalid PDF page count"),
            ("Pages: 0", "PDF must contain 1..1000 pages"),
            ("Pages: 1001", "PDF must contain 1..1000 pages"),
        ] {
            assert_eq!(parse(input).unwrap_err(), error);
        }
    }

    #[test]
    fn physical_geometry_preserves_rotation_and_error_precedence() {
        use super::physical_page_size as parse;
        assert_eq!(
            parse("Page 1 size: 100 x 200 pts\nPage 1 rot: 90", 300, 1).unwrap(),
            (200., 100.)
        );
        assert_eq!(
            parse("Page 1 size: 100 x 200 pts\nPage 1 rot: -90", 300, 1).unwrap(),
            (200., 100.)
        );
        assert_eq!(
            parse("Page 1 size: 100 x 200 pts\nPage 1 rot: invalid", 300, 1).unwrap(),
            (100., 200.)
        );
        for (input, expected) in [
            ("", "pdfinfo did not report physical page size"),
            ("Page size:", "missing page width"),
            ("Page size: invalid", "invalid page width"),
            ("Page size: 100", "missing page height"),
            ("Page size: 100 x invalid", "invalid page height"),
            (
                "Page size: NaN x 100",
                "page 7 exceeds supported raster dimensions",
            ),
            (
                "Page size: -1 x 100",
                "page 7 exceeds supported raster dimensions",
            ),
        ] {
            assert_eq!(parse(input, 300, 7).unwrap_err(), expected);
        }
    }

    #[test]
    fn retry_support_rejects_border_artifacts_and_invalid_boxes() {
        let mut doc = scanweave_io::hocr::HocrDocument::default();
        doc.words.push(scanweave_io::hocr::HocrWord {
            text: "145,000".into(),
            bbox: (0, 0, 60, 20),
            confidence: Some(90.),
            line_index: 0,
            chars: vec![scanweave_io::hocr::HocrChar {
                text: "1".into(),
                bbox: (0, 0, 8, 20),
                confidence: Some(99.),
            }],
        });
        assert_eq!(super::reliable_words(&doc, 100, 100), 1);
        doc.words[0].chars[0].bbox = (0, 0, 0, 20);
        assert_eq!(super::reliable_words(&doc, 100, 100), 0);
        doc.words[0].chars[0].bbox = (0, 0, 8, 20);
        doc.words[0].text = "|".into();
        assert_eq!(super::reliable_words(&doc, 100, 100), 0);
    }
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
