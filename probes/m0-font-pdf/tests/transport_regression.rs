//! Transport regression tests (M0-Q item 2): touching visual components must
//! NOT cause OCR symbols to disappear. Image-component ownership and Unicode
//! text ownership are independent: a single visual unit may carry multiple
//! semantic characters (SPEC §3/§5.3), but every supplied character must
//! survive to exactly one unit, in order.

use m0_font_pdf::mask::segment;
use m0_font_pdf::units::extract_units;
use scanweave_core::ocr_page::OcrPage;
use scanweave_core::Limits;

/// dir = fixture directory, stem = page stem (dir/stem.png + dir/stem.ocr.json)
fn load_page(dir: &str, stem: &str) -> (Vec<u8>, u32, u32, OcrPage) {
    let base = format!("{}/../../qualification/fixtures/probe/{}", env!("CARGO_MANIFEST_DIR"), dir);
    let img = image::open(format!("{base}/{stem}.png"))
        .expect("fixture png")
        .to_rgb8();
    let (w, h) = (img.width(), img.height());
    let ocr_bytes = std::fs::read(format!("{base}/{stem}.ocr.json")).expect("fixture ocr json");
    let page = OcrPage::parse_bytes(&ocr_bytes).expect("fixture parses");
    (img.as_raw().to_vec(), w, h, page)
}

fn transport_check(dir: &str, stem: &str) {
    let (rgb, w, h, page) = load_page(dir, stem);
    page.validate(&Limits::m0_defaults()).expect("fixture validates");

    let seg = segment(&rgb, w, h);
    let (units, _unowned) = extract_units(&seg, w, h, &page);

    // every supplied character must survive into exactly one TEXT unit
    let supplied: usize = page
        .spans
        .iter()
        .map(|s| s.text.chars().count())
        .sum();
    let carried: usize = units
        .iter()
        .filter(|u| !u.semantic_text.is_empty())
        .map(|u| u.semantic_text.chars().count())
        .sum();
    assert_eq!(
        carried, supplied,
        "{dir}: transport loss — {carried} of {supplied} supplied characters carried into visual units"
    );

    // per-span order: units of a span, sorted by ink x0, must reassemble the
    // span text exactly (character order preserved)
    for span in &page.spans {
        let mut parts: Vec<(f64, String)> = units
            .iter()
            .filter(|u| u.span_id == span.id && !u.semantic_text.is_empty())
            .map(|u| (u.bbox_px[0], u.semantic_text.clone()))
            .collect();
        parts.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
        let joined: String = parts.into_iter().map(|(_, t)| t).collect();
        assert_eq!(
            joined, span.text,
            "{dir}: span {} reassembles to {joined:?} but OCR supplied {:?}",
            span.id, span.text
        );
    }
}

#[test]
fn p09_real_tesseract_118_chars_transport() {
    transport_check("p09_realtext", "p09_realtext");
}

#[test]
fn p10_repeated_text_transport() {
    for n in 1..=4 {
        // p10 per-page bundles (p10_multipage/page{n}) carry real tesseract OCR
        transport_check("p10_multipage", &format!("page{n}/p10_page{n}"));
    }
}
