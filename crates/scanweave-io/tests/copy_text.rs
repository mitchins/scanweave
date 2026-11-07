//! Copy-text regression for invisible OCR text (#31).
//!
//! PDFium groups text objects into lines by origin y, sorts each line by origin
//! x and re-emits a span's /ActualText whenever the span's objects stop being
//! consecutive. With one object per OCR character, a duplicate OCR line on the
//! same baseline interleaved with the original and copied text repeated words.

use scanweave_io::{
    convert::{Input, Policy, SpanInput, SymbolInput},
    document,
};

fn poly(b: [f64; 4]) -> Vec<[f64; 2]> {
    vec![[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]
}

/// A span whose characters split its box evenly, one OCR symbol each.
fn span(id: &str, text: &str, b: [f64; 4], separator_after: &str) -> SpanInput {
    let chars: Vec<(usize, char)> = text.char_indices().collect();
    let width = (b[2] - b[0]) / chars.len() as f64;
    let symbols = chars
        .iter()
        .enumerate()
        .map(|(i, &(start, ch))| SymbolInput {
            id: format!("{id}s{i}"),
            range: (start, start + ch.len_utf8()),
            polygon: poly([
                b[0] + i as f64 * width,
                b[1],
                b[0] + (i + 1) as f64 * width,
                b[3],
            ]),
        })
        .collect();
    SpanInput {
        id: id.into(),
        text: text.into(),
        separator_after: separator_after.into(),
        polygon: poly(b),
        symbols,
    }
}

#[test]
fn duplicate_ocr_line_is_copied_once_per_span() {
    let Some(library) = std::env::var_os("SCANWEAVE_PDFIUM_LIBRARY") else {
        eprintln!("skipping PDFium copy-text test: SCANWEAVE_PDFIUM_LIBRARY is unset");
        return;
    };
    let (width, height) = (900u32, 200u32);
    // Blank paper: every span stays invisible OCR text over the raster.
    let spans = vec![
        span("a", "METHOD", [40.0, 60.0, 160.0, 84.0], " "),
        span("b", "OF", [176.0, 60.0, 216.0, 84.0], " "),
        span("c", "SOLICITATI:", [232.0, 60.0, 452.0, 84.0], "\n"),
        // Tesseract's duplicate reading of the same ink, on the same baseline.
        span("d", "OF", [180.0, 61.0, 220.0, 84.0], " "),
        span("e", "SOLICITATION", [238.0, 61.0, 470.0, 84.0], "\n"),
        span("f", "Quoquo", [40.0, 120.0, 160.0, 144.0], " "),
        span("g", "pacto", [176.0, 120.0, 276.0, 144.0], "\n"),
    ];
    let input = Input {
        rgb: vec![255; (width * height * 3) as usize],
        width,
        height,
        page_id: "copy-text".into(),
        spans,
        protected_regions: vec![],
        raster_to_page_pt: [0.24, 0., 0., -0.24, 0., height as f64 * 0.24],
        pixel_sha256: None,
    };
    let policy = Policy {
        profile: "clearscan".into(),
        glyph_dictionary: "visual".into(),
        ..Policy::default()
    };
    let doc = document::convert_document("copy-text", std::slice::from_ref(&input), &policy)
        .unwrap();
    let pdfium = pdfium_render::prelude::Pdfium::new(
        pdfium_render::prelude::Pdfium::bind_to_library(library).unwrap(),
    );
    let pdf = pdfium.load_pdf_from_byte_slice(&doc.pdf_bytes, None).unwrap();
    let text = pdf.pages().get(0).unwrap().text().unwrap().all();
    for (word, expected) in [
        ("METHOD", 1),
        ("SOLICITATI:", 1),
        ("SOLICITATION", 1),
        ("Quoquo", 1),
        ("pacto", 1),
    ] {
        assert_eq!(text.matches(word).count(), expected, "{word} in {text:?}");
    }
    assert_eq!(text.matches("OF").count(), 2, "{text:?}");
}
