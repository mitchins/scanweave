//! Behaviour tests: normalized OCR page validation.
//! Covers IN-02, IN-03, IN-04(partial), IN-06(partial), NF-01..NF-06, UTF-8 range rules.

use scanweave_core::error::ScanWeaveError;
use scanweave_core::ocr_page::OcrPage;
use scanweave_core::Limits;

fn fx(rel: &str) -> Vec<u8> {
    let p = format!(
        "{}/../../qualification/fixtures/{}",
        env!("CARGO_MANIFEST_DIR"),
        rel
    );
    std::fs::read(&p).unwrap_or_else(|e| panic!("fixture {p}: {e}"))
}

fn kind(e: &ScanWeaveError) -> &'static str {
    use ScanWeaveError as E;
    match e {
        E::InvalidInput { .. } => "InvalidInput",
        E::BindingMismatch { .. } => "BindingMismatch",
        E::MissingPhysicalGeometry { .. } => "MissingPhysicalGeometry",
        E::UnsupportedGeometry { .. } => "UnsupportedGeometry",
        E::UnsupportedDocumentFeature { .. } => "UnsupportedDocumentFeature",
        E::DependencyUnavailable { .. } => "DependencyUnavailable",
        E::ResourceLimit { .. } => "ResourceLimit",
        E::Cancelled => "Cancelled",
        E::ValidationFailed { .. } => "ValidationFailed",
        E::PolicyUnsatisfied { .. } => "PolicyUnsatisfied",
        E::IoFailure { .. } => "IoFailure",
        E::PublicationPartial { .. } => "PublicationPartial",
    }
}

fn parse_and_validate(rel: &str) -> Result<OcrPage, ScanWeaveError> {
    let p = OcrPage::parse_bytes(&fx(rel))?;
    p.validate(&Limits::m0_defaults())?;
    Ok(p)
}

// ---------------------------------------------------------------- positive

#[test]
fn positive_control_valid_page() {
    let page = parse_and_validate("positive/valid_page.json").expect("valid fixture must pass");
    assert_eq!(page.page_id, "p000001");
}

#[test]
fn positive_control_word_only() {
    // IN-04 (partial): word-only page is schema-valid; no symbols may be invented.
    let page = parse_and_validate("positive/word_only_page.json").expect("word-only fixture must pass");
    assert_eq!(page.granularity, scanweave_core::ocr_page::Granularity::Word);
    assert!(page.spans[0].symbols.is_empty());
}

#[test]
fn positive_control_combining_sequence() {
    // one symbol covers e+U+0301 as a whole grapheme (3 UTF-8 bytes) — legal
    parse_and_validate("positive/combining_page.json").expect("whole-grapheme coverage is legal");
}

// ------------------------------------------------------------ NF-01..NF-06

#[test]
fn nf01_unknown_property_rejected() {
    let e = parse_and_validate("negative/nf01_unknown_property.json").unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

#[test]
fn nf02_malformed_hash_rejected() {
    let e = parse_and_validate("negative/nf02_malformed_hash.json").unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

#[test]
fn nf03_zero_physical_width_rejected() {
    let e = parse_and_validate("negative/nf03_zero_physical_width.json").unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

#[test]
fn nf04_undersized_polygon_rejected() {
    let e = parse_and_validate("negative/nf04_undersized_polygon.json").unwrap_err();
    assert_eq!(kind(&e), "UnsupportedGeometry");
}

#[test]
fn nf05_duplicate_reading_order_rejected() {
    let e = parse_and_validate("negative/nf05_duplicate_reading_order.json").unwrap_err();
    assert!(matches!(kind(&e), "InvalidInput" | "ValidationFailed"));
}

#[test]
fn nf06_unsupported_direction_rejected() {
    let e = parse_and_validate("negative/nf06_unsupported_direction.json").unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

// ------------------------------------------------------- structural rejections

#[test]
fn duplicate_json_keys_rejected() {
    // {"a":1,"a":2} — duplicate object keys are rejected (SPEC Appendix A)
    let src = br#"{"schema_version":"1.0","schema_version":"1.0"}"#;
    let e = OcrPage::parse_bytes(src).unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

#[test]
fn nan_infinity_rejected() {
    let src = br#"{"schema_version":"1.0","page":{"width_pt":NaN}}"#;
    assert!(OcrPage::parse_bytes(src).is_err());
}

#[test]
fn unknown_schema_major_rejected() {
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["schema_version"] = serde_json::json!("2.0");
    let bytes = serde_json::to_vec(&v).unwrap();
    let e = OcrPage::parse_bytes(&bytes).unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

#[test]
fn oversize_page_pixels_resource_limit() {
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["raster"]["width_px"] = serde_json::json!(20000);
    v["raster"]["height_px"] = serde_json::json!(20000); // 4e8 > 8e7 budget
    v["page"]["width_pt"] = serde_json::json!(4800.0);
    v["page"]["height_pt"] = serde_json::json!(4800.0);
    let bytes = serde_json::to_vec(&v).unwrap();
    let page = OcrPage::parse_bytes(&bytes).expect("schema-valid but over budget");
    let e = page.validate(&Limits::m0_defaults()).unwrap_err();
    assert_eq!(kind(&e), "ResourceLimit");
}

// ------------------------------------------------------------- UTF-8 ranges

fn with_symbol_ranges(mutate: impl FnOnce(&mut serde_json::Value)) -> ScanWeaveError {
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    mutate(&mut v["spans"][1]["symbols"]);
    let bytes = serde_json::to_vec(&v).unwrap();
    OcrPage::parse_bytes(&bytes)
        .and_then(|p| p.validate(&Limits::m0_defaults()))
        .unwrap_err()
}

#[test]
fn mid_scalar_byte_range_rejected() {
    // s002 text is "80" (ASCII); emulate a mid-scalar split on a multibyte char by
    // replacing text with "é" (2 bytes) and ranges [0,1)+[1,2).
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["spans"][1]["text"] = serde_json::json!("é");
    v["spans"][1]["symbols"] = serde_json::json!([
        {"id":"gA","text_range_utf8":[0,1],"polygon":[[34,4],[43,4],[43,24],[34,24]],
         "confidence":{"value":null,"scale":"unknown","calibrated":false}},
        {"id":"gB","text_range_utf8":[1,2],"polygon":[[45,4],[54,4],[54,24],[45,24]],
         "confidence":{"value":null,"scale":"unknown","calibrated":false}}
    ]);
    let bytes = serde_json::to_vec(&v).unwrap();
    let e = OcrPage::parse_bytes(&bytes)
        .and_then(|p| p.validate(&Limits::m0_defaults()))
        .unwrap_err();
    assert_eq!(kind(&e), "ValidationFailed", "mid-scalar split must be rejected");
}

#[test]
fn grapheme_splitting_range_rejected() {
    // base e + combining acute (U+0301): [0,1) splits the grapheme — must be rejected
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["spans"][1]["text"] = serde_json::json!("e\u{0301}");
    v["spans"][1]["symbols"] = serde_json::json!([
        {"id":"gA","text_range_utf8":[0,1],"polygon":[[34,4],[43,4],[43,24],[34,24]],
         "confidence":{"value":null,"scale":"unknown","calibrated":false}},
        {"id":"gB","text_range_utf8":[1,3],"polygon":[[45,4],[54,4],[54,24],[45,24]],
         "confidence":{"value":null,"scale":"unknown","calibrated":false}}
    ]);
    let bytes = serde_json::to_vec(&v).unwrap();
    let e = OcrPage::parse_bytes(&bytes)
        .and_then(|p| p.validate(&Limits::m0_defaults()))
        .unwrap_err();
    assert_eq!(kind(&e), "ValidationFailed", "grapheme split must be rejected");
}

#[test]
fn overlapping_symbol_ranges_rejected() {
    let e = with_symbol_ranges(|syms| {
        syms[1]["text_range_utf8"] = serde_json::json!([0, 2]);
    });
    assert_eq!(kind(&e), "ValidationFailed");
}

#[test]
fn empty_symbol_range_rejected() {
    let e = with_symbol_ranges(|syms| {
        syms[0]["text_range_utf8"] = serde_json::json!([0, 0]);
    });
    assert_eq!(kind(&e), "ValidationFailed");
}

// ------------------------------------------------------- binding and geometry

#[test]
fn in02_binding_mismatch_detected() {
    // pixel hash of declared canonical samples differs from computed hash of given samples
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["raster"]["pixel_sha256"] = serde_json::json!("cc".repeat(32));
    let page: OcrPage =
        OcrPage::parse_bytes(&serde_json::to_vec(&v).unwrap()).expect("schema-valid");
    // canonical samples for 64x32 rgb8: all-zero buffer is a valid decode of a black image
    let samples = vec![0u8; 64 * 32 * 3];
    let e = page.verify_binding(&samples).unwrap_err();
    assert_eq!(kind(&e), "BindingMismatch");
}

#[test]
fn in02_binding_match_accepted() {
    let _page: OcrPage =
        OcrPage::parse_bytes(&fx("positive/valid_page.json")).expect("schema-valid");
    // Compute the pixel hash the fixture would need: mutate fixture to the actual hash.
    let samples = vec![7u8; 64 * 32 * 3];
    let want = scanweave_core::pixel_hash::pixel_hash(
        scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
        64,
        32,
        scanweave_core::pixel_hash::ColourTag::Srgb,
        None,
        &samples,
    )
    .unwrap();
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["raster"]["pixel_sha256"] = serde_json::json!(want);
    let bytes = serde_json::to_vec(&v).unwrap();
    let page = OcrPage::parse_bytes(&bytes).expect("schema-valid");
    page.verify_binding(&samples).expect("matching binding must pass");
}

#[test]
fn in03_stale_crop_rotation_rejected() {
    // Span polygon outside the canonical raster -> stale OCR geometry, never shifted.
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["spans"][0]["polygon"] = serde_json::json!([[200,4],[220,4],[220,24],[200,24]]); // x>64
    let bytes = serde_json::to_vec(&v).unwrap();
    let page = OcrPage::parse_bytes(&bytes).expect("schema-valid");
    let e = page.validate(&Limits::m0_defaults()).unwrap_err();
    assert_eq!(kind(&e), "UnsupportedGeometry");
}

#[test]
fn stale_rotation_flag_rejected() {
    // orientation_policy must be applied_once; anything else is an unsupported transform
    let mut v: serde_json::Value = serde_json::from_slice(&fx("positive/valid_page.json")).unwrap();
    v["raster"]["orientation_policy"] = serde_json::json!("applied_twice");
    let e = OcrPage::parse_bytes(&serde_json::to_vec(&v).unwrap()).unwrap_err();
    assert_eq!(kind(&e), "InvalidInput");
}

#[test]
fn span_content_errors_precede_parent_reference_errors() {
    let mut page = parse_and_validate("positive/valid_page.json").unwrap();
    page.spans[0].parent_span_id = Some("missing-parent".into());
    let first_id = page.spans[0].id.clone();
    // A later span's baseline still wins over an earlier span's missing parent.
    let mut later = page.spans[0].clone();
    later.id = "later-span".into();
    later.parent_span_id = None;
    for (i, symbol) in later.symbols.iter_mut().enumerate() {
        symbol.id = format!("later-symbol-{i}");
    }
    later.baseline = Some(vec![[f64::NAN, 0.0]]);
    page.reading_order.push(later.id.clone());
    page.spans.push(later);
    assert_eq!(
        page.validate(&Limits::m0_defaults()).unwrap_err(),
        ScanWeaveError::InvalidInput {
            context: "span later-span: baseline out of range".into(),
        }
    );
    page.spans.last_mut().unwrap().baseline = None;
    assert_eq!(
        page.validate(&Limits::m0_defaults()).unwrap_err(),
        ScanWeaveError::InvalidInput {
            context: format!("span {first_id}: parent_span_id missing-parent does not exist"),
        }
    );
    page.spans[0].parent_span_id = Some(first_id.clone());
    assert_eq!(
        page.validate(&Limits::m0_defaults()).unwrap_err(),
        ScanWeaveError::InvalidInput {
            context: format!("span {first_id}: parent reference cycle detected"),
        }
    );
    page.spans[0].parent_span_id = Some("later-span".into());
    page.spans.last_mut().unwrap().parent_span_id = Some(first_id.clone());
    assert_eq!(
        page.validate(&Limits::m0_defaults()).unwrap_err(),
        ScanWeaveError::InvalidInput {
            context: format!("span {first_id}: parent reference cycle detected"),
        }
    );
    page.spans.last_mut().unwrap().parent_span_id = None;
    page.validate(&Limits::m0_defaults()).unwrap();
}
