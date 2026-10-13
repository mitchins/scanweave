//! hOCR import tests: IN-01 (real geometry, no OCR invocation), IN-04 (word-only honesty),
//! IN-06 (bounded rejection of malformed XML / external entities), IN-05 (missing DPI via builder).

use scanweave_io::hocr::{parse_hocr, HocrWord};
use scanweave_io::normalize::{build_normalized_page, Binding};

fn binding() -> Binding {
    Binding {
        asset_path: "pages/p000001.png".into(),
        file_sha256: "aa".repeat(32),
        pixel_sha256: "bb".repeat(32),
    }
}

const CHAR_BOX_HOCR: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head><title></title><meta http-equiv="Content-Type" content="text/html;charset=utf-8" /><meta name='ocr-system' content='tesseract 5.3.4' /><meta name='ocr-capabilities' content='ocr_line ocr_page ocrx_word ocrx_cinfo'/></head>
 <body><div class='ocr_page' id='page_1' title='image "scan.tif"; bbox 0 0 64 32; ppageno 0'>
  <div class='ocr_carea' id='area_1' title='bbox 10 14 55 25'>
   <p class='ocr_par' id='par_1' lang='eng' title='bbox 10 14 55 25'>
    <span class='ocr_line' id='line_1' title='bbox 10 14 55 25; baseline 0 0; x_size 12; x_descenders 2; x_ascenders 2'>
     <span class='ocrx_word' id='word_1' title='bbox 10 14 25 25; x_wconf 96'>80<span class='ocrx_cinfo' title='x_bboxes 10 14 17 25; x_confs 96'><u>8</u></span><span class='ocrx_cinfo' title='x_bboxes 18 14 25 25; x_confs 95'><u>0</u></span></span>
     <span class='ocrx_word' id='word_2' title='bbox 30 14 45 25; x_wconf 92'>ab<span class='ocrx_cinfo' title='x_bboxes 30 14 37 25; x_confs 92'><u>a</u></span><span class='ocrx_cinfo' title='x_bboxes 38 14 45 25; x_confs 91'><u>b</u></span></span>
    </span>
   </p>
  </div>
 </div></body>
</html>
"#;

const WORD_ONLY_HOCR: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title></title></head>
 <body><div class='ocr_page' id='page_1' title='image "scan.tif"; bbox 0 0 64 32; ppageno 0'>
  <span class='ocrx_word' id='word_1' title='bbox 10 14 25 25; x_wconf 90'>Hello</span>
 </div></body>
</html>
"#;

#[test]
fn in01_char_box_hocr_imports_symbol_geometry() {
    let doc = parse_hocr(CHAR_BOX_HOCR.as_bytes(), 64, 32).expect("char-box hOCR must parse");
    assert_eq!(doc.words.len(), 2, "two words on the page");
    let w0 = &doc.words[0];
    assert_eq!(w0.text, "80");
    assert_eq!(
        w0.chars.len(),
        2,
        "per-character boxes must be captured when present"
    );
    assert_eq!(w0.chars[0].text, "8");
    assert_eq!(w0.chars[0].bbox, (10, 14, 17, 25));
    assert_eq!(w0.chars[1].bbox, (18, 14, 25, 25));
    assert_eq!(w0.confidence, Some(96.0));
    // No OCR engine is invoked by import: this test is the proof — parse is pure bytes->struct.
}

#[test]
fn in04_word_only_hocr_stays_word_level() {
    let doc = parse_hocr(WORD_ONLY_HOCR.as_bytes(), 64, 32).expect("word-only hOCR must parse");
    assert_eq!(doc.words.len(), 1);
    let w = &doc.words[0];
    assert_eq!(w.text, "Hello");
    assert!(
        w.chars.is_empty(),
        "word-only input must NOT fabricate per-character boxes"
    );
    let page = build_normalized_page(
        &scanweave_io::normalize::ImageMeta {
            width: 64,
            height: 32,
        },
        &doc,
        Some(300.0),
        &binding(),
    )
    .expect("normalized page builds");
    assert_eq!(page.granularity, scanweave_core::ocr_page::Granularity::Word);
    assert!(
        page.spans[0].symbols.is_empty(),
        "no equal-width invented characters"
    );
}

#[test]
fn in05_missing_dpi_is_explicit_error() {
    let doc = parse_hocr(WORD_ONLY_HOCR.as_bytes(), 64, 32).unwrap();
    let e = build_normalized_page(
        &scanweave_io::normalize::ImageMeta {
            width: 64,
            height: 32,
        },
        &doc,
        None,
        &binding(),
    )
    .unwrap_err();
    assert!(
        matches!(e, scanweave_core::error::ScanWeaveError::MissingPhysicalGeometry { .. }),
        "absent DPI must yield MissingPhysicalGeometry, got {e:?}"
    );
}

#[test]
fn in06_malformed_xml_bounded_rejection() {
    let e = parse_hocr(b"<html><body><div class='ocr_page'", 64, 32).unwrap_err();
    assert!(matches!(
        e,
        scanweave_core::error::ScanWeaveError::InvalidInput { .. }
    ));
}

#[test]
fn in06_external_entity_not_fetched() {
    // A DOCTYPE with a SYSTEM external entity must not trigger a fetch; parse must
    // reject or ignore it (never resolve). This machine would hang/leak if fetched.
    let evil = br#"<?xml version="1.0"?><!DOCTYPE html [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<html xmlns="http://www.w3.org/1999/xhtml"><body><div class='ocr_page' id='p' title='bbox 0 0 64 32'>
<span class='ocrx_word' id='w1' title='bbox 1 1 2 2; x_wconf 90'>&xxe;</span></div></body></html>"#;
    let result = parse_hocr(&evil[..], 64, 32);
    match result {
        Err(e) => assert!(matches!(
            e,
            scanweave_core::error::ScanWeaveError::InvalidInput { .. }
        )),
        Ok(doc) => {
            // tolerated only if the entity reference did not resolve to file content
            assert!(!doc.words.iter().any(|w: &HocrWord| w.text.contains("root:")),
                "external entity content must never appear");
        }
    }
}

#[test]
fn in06_oversize_input_bounded() {
    let big = vec![b'x'; 17 * 1024 * 1024]; // > max_ocr_page_bytes (16 MiB)
    let e = parse_hocr(&big, 64, 32).unwrap_err();
    assert!(matches!(
        e,
        scanweave_core::error::ScanWeaveError::ResourceLimit { .. }
    ));
}
