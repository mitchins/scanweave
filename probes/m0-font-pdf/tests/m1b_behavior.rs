//! M1-B behavioral tests. Written BEFORE the implementation changes they cover
//! (red→green): line-level search semantics, patch economy, auto selection,
//! document assembly, and the M1A-05 contact regression.

mod support;

use m0_font_pdf::shim::{convert_input, convert_with};

/// The behaviour tests exercise the reconstruction path, so the converter-side
/// fidelity gate (min_ink_iou) is disabled here: the qualification harness
/// applies the SPEC's own per-occurrence gates to the rendered output.
fn measurement_policy() -> m0_font_pdf::Policy {
    m0_font_pdf::Policy { min_ink_iou: 0.0, ..m0_font_pdf::Policy::default() }
}
use scanweave_io::convert::{convert, ProtectedInput};
use m0_font_pdf::{Input, Policy};
use scanweave_core::Limits;

use scanweave_core::ocr_page::OcrPage;
use std::path::PathBuf;

fn fixture(dir: &str, stem: &str) -> (Vec<u8>, u32, u32, OcrPage) {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/probe")
        .join(dir);
    let img = image::open(base.join(format!("{stem}.png")))
        .expect("fixture png")
        .to_rgb8();
    let (w, h) = (img.width(), img.height());
    let ocr_bytes = std::fs::read(base.join(format!("{stem}.ocr.json")))
        .or_else(|_| std::fs::read(base.join(format!("{stem}.synth.json"))))
        .expect("fixture ocr json");
    let page = OcrPage::parse_bytes(&ocr_bytes).expect("fixture parses");
    page.validate(&Limits::m0_defaults()).expect("fixture validates");
    (img.as_raw().to_vec(), w, h, page)
}

/// UTF-16BE hex of a string, as pdf_writer emits ActualText.
fn utf16be_hex(s: &str) -> String {
    let mut out = String::from("FEFF");
    for unit in s.encode_utf16() {
        out.push_str(&format!("{unit:04X}"));
    }
    out
}

fn build(dir: &str, stem: &str, policy: Option<&Policy>) -> scanweave_io::convert::Output {
    let (rgb, w, h, page) = fixture(dir, stem);
    let input = convert_input(&rgb, w, h, stem, &page);
    // the behaviour tests exercise the reconstruction path: the converter-side
    // fidelity gate is disabled unless the test overrides it explicitly
    let p = policy.cloned().unwrap_or_else(measurement_policy);
    convert_with(&input, Some(&p)).expect("conversion")
}

/// M1B-01: a line mixing visible spans and a raster-fallback span must be
/// natively searchable: the fallback owner run is emitted INLINE in reading
/// order (between the visible spans of its line), INVISIBLE (it paints nothing;
/// the raster patch carries the pixels), and placed on the span's traced INK
/// baseline — extractors merge runs into a line by baseline and sort by x, so
/// matching the visible line's baseline is what keeps the label in reading
/// order. Its own per-span /ActualText carries the OCR label.
#[test]
fn m1b01_mixed_line_owner_run_is_inline_on_ink_baseline() {
    let out = build("p10_multipage/page1", "p10_page1", None);
    let pdf = support::decoded_syntax(&out.pdf_bytes);
    let bt = pdf.find("BT\n").expect("text object");
    let et = pdf.rfind("ET\n").expect("text object end");
    let content = &pdf[bt..=et];
    // the fallback span "1" carries its own per-span ActualText
    assert!(
        pdf.contains("/ActualText (1)"),
        "fallback span must carry its label via /ActualText"
    );
    // and its run sits between "Page"'s EMC and "of"'s BDC (inline, reading order)
    let page_at = content.find("/ActualText (Page)").expect("Page mark");
    let seg = &content[page_at..];
    let page_emc = seg.find("EMC").expect("Page mark close");
    let owner_at = seg.find("/ActualText (1)").expect("owner mark");
    let of_bdc = seg.find("/ActualText (of)").expect("of mark");
    assert!(
        page_emc < owner_at && owner_at < of_bdc,
        "owner run must be emitted inline between the visible spans of its line"
    );
    // the owner run is invisible (paints nothing)
    let owner_run = &seg[owner_at..of_bdc];
    assert!(
        owner_run.contains("3 Tr"),
        "the owner run must be invisible so it paints no pixels"
    );
    // and it is placed on the traced ink baseline: the same Tm y as the visible
    // runs of its line (the 'of' span's runs), within a small tolerance
    let owner_y = owner_run
        .split("1 0 0 1 ")
        .nth(1)
        .and_then(|s| s.split_whitespace().nth(1))
        .and_then(|v| v.parse::<f64>().ok())
        .expect("owner Tm y");
    let of_seg = &content[content.find("/ActualText (of)").unwrap()..];
    let of_y = of_seg
        .split(" Tm")
        .next()
        .and_then(|head| head.split_whitespace().last())
        .and_then(|v| v.parse::<f64>().ok())
        .expect("of Tm y");
    assert!(
        (owner_y - of_y).abs() < 1.0,
        "owner baseline {owner_y} must match the line baseline {of_y}"
    );
    // no invented whitespace: identifiers/amounts stay contiguous ActualTexts
    for ident in ["INV-2026-0042", "1,234.56"] {
        assert!(
            pdf.contains(&format!("/ActualText ({ident})")),
            "{ident} must not be split with invented whitespace"
        );
    }
}

/// M1B-01b: pure-vector lines keep per-span /ActualText (M0-Q/M1-A behaviour),
/// so the change is minimal and existing gates stay stable.
#[test]
fn m1b01b_vector_lines_keep_per_span_marks() {
    let out = build("p09_realtext", "p09_realtext", None);
    let pdf = support::decoded_syntax(&out.pdf_bytes);
    // 'Total' is a pure-vector span: it keeps its own per-span ActualText
    assert!(
        pdf.contains("/ActualText (Total)"),
        "pure-vector spans keep their per-span /ActualText"
    );
    // and there is exactly one mark per span (no line-level duplication)
    let marks = pdf.matches("/ActualText").count();
    assert_eq!(marks, 21, "one /ActualText per span on p09, got {marks}");
}

/// M1B-02: raster fallback economy — coalesced patches must (a) keep exact
/// source pixels (sha fidelity) and (b) reduce the image XObject count
/// versus one patch per region+cell.
#[test]
fn m1b02_patch_coalescing_is_faithful_and_economical() {
    let (rgb, w, h, page) = fixture("p14_noisy", "p14_noisy");
    let input = convert_input(&rgb, w, h, "p14", &page);
    let out = convert_with(&input, Some(&measurement_policy())).expect("convert");
    let r = &out.report;
    // fidelity: every patch still byte-identical to the source crop
    for p in &r.patches {
        let (x0, y0) = (p.bbox_px[0] as usize, p.bbox_px[1] as usize);
        let (x1, y1) = (p.bbox_px[2] as usize, p.bbox_px[3] as usize);
        let mut crop = Vec::with_capacity(((x1 - x0) * (y1 - y0)) * 3);
        for yy in y0..y1.min(h as usize) {
            for xx in x0..x1.min(w as usize) {
                let i = ((yy * w as usize) + xx) * 3;
                crop.extend_from_slice(&rgb[i..i + 3]);
            }
        }
        assert_eq!(
            scanweave_core::hash_hex(&crop),
            p.rgb_sha256,
            "coalesced patch must stay byte-identical to the source"
        );
    }
    // economy: far fewer image objects than the M1-A per-cell scheme (204)
    let count = out
        .pdf_bytes
        .windows(8)
        .filter(|w| w == b"/Subtype")
        .count();
    let images = support::decoded_syntax(&out.pdf_bytes)
        .matches("/Subtype /Image")
        .count();
    assert!(
        images < 40,
        "coalesced fallback must cut image XObjects (M1-A: 204, got {images})"
    );
    let _ = count;
    // text fidelity unchanged
    assert_eq!(r.coverage.text_ink_px_raster, r.coverage.text_ink_px_total);
    assert!(r.raster_bytes > 0);
}

/// M1B-03: auto mode must choose the smallest candidate that still passes the
/// semantic gates (searchable text preserved, ownership invariants intact).
#[test]
fn m1b03_auto_selects_smallest_qualified_candidate() {
    let (rgb, w, h, page) = fixture("p14_noisy", "p14_noisy");
    let input = convert_input(&rgb, w, h, "p14", &page);
    let out = convert_with(&input, Some(&Policy { mode: "auto".into(), min_ink_iou: 0.0, ..Policy::default() }))
        .expect("auto convert");
    let r = &out.report;
    assert_eq!(r.policy.mode, "auto");
    // the selected candidate must still carry every span's label
    assert!(r.semantic_owner.values().all(|o| o == "visible_tounicode" || o == "invisible"));
    // and it must not be larger than the reconstruct candidate on the same page
    let recon = convert_with(
        &Input { rgb: rgb.clone(), ..input.clone() },
        Some(&Policy { mode: "reconstruct".into(), min_ink_iou: 0.0, ..Policy::default() }),
    )
    .expect("reconstruct convert");
    assert!(
        r.pdf_bytes <= recon.report.pdf_bytes,
        "auto ({}B) must not exceed reconstruct ({}B)",
        r.pdf_bytes,
        recon.report.pdf_bytes
    );
}

/// M1B-04: document assembly - N pages become ONE PDF: correct page count,
/// order, per-page MediaBox, ONE shared font resource, deterministic bytes,
/// and every page's searchable text present (per-page reports carried).
#[test]
fn m1b04_document_assembly_is_one_searchable_pdf() {
    use scanweave_io::document::convert_document;
    let doc = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/documents/doc4_invoice");
    let bundle_bytes = std::fs::read(doc.join("document.json")).unwrap();
    let bundle = scanweave_core::bundle::Bundle::parse_bytes(&bundle_bytes).expect("bundle parses");
    bundle
        .verify_pairing(&doc, &Limits::m0_defaults())
        .expect("bundle pairing");
    let mut inputs = Vec::new();
    for p in &bundle.pages {
        let img = image::open(doc.join(format!("{}.png", p.page_id))).unwrap().to_rgb8();
        let (w, h) = (img.width(), img.height());
        let ocr = OcrPage::parse_bytes(&std::fs::read(doc.join(&p.ocr_page_path)).unwrap()).unwrap();
        inputs.push(scanweave_io::convert::input_from_ocr_page(
            img.as_raw(), w, h, &p.page_id, &ocr,
        ));
    }
    let policy = measurement_policy();
    let out = convert_document(&bundle.document_id, &inputs, &policy).expect("document");
    let pdf = support::decoded_syntax(&out.pdf_bytes);

    // one PDF with N page objects and one shared font program
    let page_objs = pdf.matches("/Type /Page").count() - pdf.matches("/Type /Pages").count();
    assert!(page_objs >= 4, "document must carry one /Page per input page, got {page_objs}");
    assert!(pdf.contains("/Count 4"), "the page tree must list 4 pages");
    let fontfiles = pdf.matches("/FontFile2").count();
    assert_eq!(fontfiles, 1, "exactly ONE shared font program (reuse), got {fontfiles}");

    // deterministic: a second build is byte-identical
    let out2 = convert_document(&bundle.document_id, &inputs, &policy).expect("document");
    assert_eq!(out.pdf_bytes, out2.pdf_bytes, "document bytes deterministic");

    // page order + per-page reports preserved
    assert_eq!(out.report.page_order, vec!["page1", "page2", "page3", "page4"]);
    assert_eq!(out.report.page_reports.len(), 4);
    assert!(out.report.ownership_invariants["visual"] && out.report.ownership_invariants["semantic"]);

    // every span of every page has a searchable owner (visible or overlay)
    let search = &out.report.search;
    assert_eq!(search.pages.len(), 4);
    for ps in &search.pages {
        assert!(!ps.lines.is_empty(), "page {} must have searchable lines", ps.page_id);
        for l in &ps.lines {
            assert_eq!(l.spans.len(), l.owners.len());
            assert!(
                l.owners.iter().all(|o| o == "visible_tounicode" || o == "invisible"),
                "every span must have a defined searchable owner"
            );
        }
    }
    // the mixed raster-fallback line is present in the search plan
    let p1 = &search.pages[0];
    assert!(
        p1.lines.iter().any(|l| l.text.contains("Page 1 of 4.")),
        "the mixed line must be in the search plan"
    );
    // per-page MediaBox (dimensions) are the source page dims
    assert!(pdf.contains("[ 0 0 216 124.8 ]") || pdf.contains("[0 0 216 124.8]"));
}

/// M1B-04b: font reuse actually reduces bytes - the shared-font document must
/// be smaller than the concatenation of the same pages built separately.
#[test]
fn m1b04b_font_reuse_reduces_bytes() {
    use scanweave_io::document::convert_document;
    let doc = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/documents/doc4_repeat");
    let bundle_bytes = std::fs::read(doc.join("document.json")).unwrap();
    let bundle = scanweave_core::bundle::Bundle::parse_bytes(&bundle_bytes).unwrap();
    bundle.verify_pairing(&doc, &Limits::m0_defaults()).unwrap();
    let mut inputs = Vec::new();
    for p in &bundle.pages {
        let img = image::open(doc.join(format!("{}.png", p.page_id))).unwrap().to_rgb8();
        let (w, h) = (img.width(), img.height());
        let ocr = OcrPage::parse_bytes(&std::fs::read(doc.join(&p.ocr_page_path)).unwrap()).unwrap();
        inputs.push(scanweave_io::convert::input_from_ocr_page(img.as_raw(), w, h, &p.page_id, &ocr));
    }
    let out = convert_document(&bundle.document_id, &inputs, &measurement_policy()).unwrap();
    let separate: usize = inputs
        .iter()
        .map(|i| convert(i, &measurement_policy()).unwrap().pdf_bytes.len())
        .sum();
    assert!(
        out.pdf_bytes.len() < separate,
        "shared-font document ({}B) must be smaller than {} separate page PDFs ({separate}B)",
        out.pdf_bytes.len(),
        inputs.len()
    );
    let font = out.report.font_bytes;
    assert!(
        separate - out.pdf_bytes.len() >= font * (inputs.len() - 1),
        "saving must cover the {} duplicated fonts",
        inputs.len() - 1
    );
}

/// M1B-05 (explicit M1A-05 regression): text touching a RULE, a STAMP or a
/// BARCODE must (a) fall back transactionally to raster for the contacted
/// region, (b) keep every span's label searchable via the owner overlay,
/// (c) introduce no unowned or double-owned ink, and (d) preserve the traced
/// ownership invariants. The fixture p13_nontext carries all three contact
/// types (rule across line 2, barcode bars beside line 1, rotated stamp over
/// the lower block).
#[test]
fn m1b05_text_touching_rule_stamp_barcode() {
    for (dir, stem) in [
        ("p13_nontext", "p13_nontext"),
        ("p14_noisy", "p14_noisy"),
    ] {
        let out = build(dir, stem, None);
        let r = &out.report;
        assert!(
            r.fallback_reasons.contains_key("ContactNonText"),
            "{stem}: rule/artwork contact must fall back to raster"
        );
        assert!(
            r.coverage.unowned_ink_px == 0 && r.coverage.multiply_owned_ink_px == 0,
            "{stem}: no unowned or double-owned ink"
        );
        assert!(r.ownership_invariants["visual"] && r.ownership_invariants["semantic"]);
        // (b) every span keeps exactly one semantic owner (visible or overlay)
        for (span, owner) in &r.semantic_owner {
            assert!(
                owner == "visible_tounicode" || owner == "invisible",
                "{stem}: span {span} has unknown owner {owner}"
            );
        }
        let owners = r.semantic_owner.len();
        assert!(owners > 0, "{stem}: spans must be present");
        // (c) the contacted spans are the raster ones and are still reported
        let invisible = r.semantic_owner.values().filter(|o| *o == "invisible").count();
        assert!(invisible > 0, "{stem}: contacted spans must be overlaid (invisible owners)");
        // (d) raster fidelity: patches stay byte-exact source crops
        let (rgb, w, h, _page) = fixture(dir, stem);
        for p in &r.patches {
            let (x0, y0) = (p.bbox_px[0] as usize, p.bbox_px[1] as usize);
            let (x1, y1) = ((p.bbox_px[2] as usize).min(w as usize), (p.bbox_px[3] as usize).min(h as usize));
            let mut crop = Vec::new();
            for yy in y0..y1 {
                for xx in x0..x1 {
                    let i = ((yy * w as usize) + xx) * 3;
                    crop.extend_from_slice(&rgb[i..i + 3]);
                }
            }
            assert_eq!(scanweave_core::hash_hex(&crop), p.rgb_sha256, "{stem}: patch fidelity");
        }
    }
}

// ---------------------------------------------------------------------------
// P0/P1/P2 regression set (operator review of the pushed M1-B revision):
// mismatched OCR/image hashes, protected amounts, 600 DPI geometry,
// repeated-span ownership, cross-page CID reuse, selected-candidate accounting.
// ---------------------------------------------------------------------------

/// Compute the canonical pixel hash the same way the binding declares it.
fn pixel_hash(rgb: &[u8], w: u32, h: u32) -> String {
    scanweave_core::pixel_hash::pixel_hash(
        scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
        w as u64,
        h as u64,
        scanweave_core::pixel_hash::ColourTag::Srgb,
        None,
        rgb,
    )
    .unwrap()
}

/// Build a synthetic one-line page: "Amount 12.34 Amount 12.34" — two spans with
/// IDENTICAL OCR text, only one of which has visual components (the second is
/// covered by a solid block). Returns the OCR page JSON for it.
fn repeated_span_page(w: u32, h: u32, block_x: u32) -> scanweave_core::ocr_page::OcrPage {
    use scanweave_core::ocr_page::*;
    let span = |id: &str, x0: u32, x1: u32, text: &str| Span {
        id: id.into(),
        text: text.into(),
        separator_after: " ".into(),
        polygon: vec![[x0 as f64, 40.0], [x1 as f64, 40.0], [x1 as f64, 110.0], [x0 as f64, 110.0]],
        direction: Direction::Ltr,
        role: Role::Body,
        language: None,
        confidence: Confidence { value: None, scale: ConfidenceScale::Unknown, calibrated: false },
        baseline: None,
        provenance: Provenance::SourceGenerated,
        parent_span_id: None,
        symbols: text
            .chars()
            .enumerate()
            .map(|(i, c)| Symbol {
                id: format!("{id}s{i:04}"),
                text_range_utf8: [i, i + c.len_utf8()],
                polygon: vec![
                    [x0 as f64 + i as f64 * 8.0, 45.0],
                    [x0 as f64 + i as f64 * 8.0 + 8.0, 45.0],
                    [x0 as f64 + i as f64 * 8.0 + 8.0, 105.0],
                    [x0 as f64 + i as f64 * 8.0 + 8.0, 105.0],
                ],
                confidence: Confidence { value: None, scale: ConfidenceScale::Unknown, calibrated: false },
            })
            .collect(),
    };
    OcrPage {
        schema_version: SchemaVersion::V1,
        page_id: "repeated".into(),
        raster: RasterBinding {
            asset_path: "repeated.png".into(),
            file_sha256: String::new(),
            pixel_sha256: String::new(),
            width_px: w,
            height_px: h,
            canonical_format: scanweave_core::pixel_hash::CanonicalFormat::Rgb8,
            colour_tag: scanweave_core::pixel_hash::ColourTag::Srgb,
            icc_sha256: None,
            orientation_policy: OrientationPolicy::AppliedOnce,
            decoder_id: "test".into(),
            dpi_x: Some(300.0),
            dpi_y: Some(300.0),
        },
        page: PageGeometry {
            width_pt: w as f64 * 72.0 / 300.0,
            height_pt: h as f64 * 72.0 / 300.0,
            raster_to_page_pt: [72.0 / 300.0, 0.0, 0.0, -72.0 / 300.0, 0.0, h as f64 * 72.0 / 300.0],
        },
        source_geometry: None,
        producer: Producer { name: "test".into(), version: "1".into(), models: vec![], languages: vec![] },
        granularity: Granularity::Symbol,
        reading_order_status: ReadingOrderStatus::Supplied,
        reading_order: vec!["w0".into(), "w1".into()],
        spans: vec![
            span("w0", 40, 150, "Amount 12.34"),
            span("w1", block_x, block_x + 110, "Amount 12.34"),
        ],
        protected_regions: vec![],
    }
}

/// P0-1: a pixel-hash mismatch between the OCR page and the raster must REFUSE.
#[test]
fn regress_pixel_binding_mismatch_is_refused() {
    let (rgb, w, h, mut page) = fixture("p13_nontext", "p13_nontext");
    let real = pixel_hash(&rgb, w, h);
    // corrupt the declared hash: the conversion must refuse, not proceed
    page.raster.pixel_sha256 = "0".repeat(64);
    let mut input = convert_input(&rgb, w, h, "p13", &page);
    assert_eq!(input.pixel_sha256.as_deref(), Some("0".repeat(64).as_str()));
    input.pixel_sha256 = Some("0".repeat(64));
    let err = convert(&input, &measurement_policy()).map(|_| ()).unwrap_err();
    assert!(
        err.contains("pixel binding mismatch"),
        "expected a binding refusal, got: {err}"
    );
    // the real hash must be accepted through the same path
    let mut ok = input.clone();
    ok.pixel_sha256 = Some(real);
    convert(&ok, &measurement_policy()).expect("matching binding converts");
}

/// P0-2: caller-protected regions must not be vectorized — the protected
/// amount's pixels survive as exact raster, and the region reports Protected.
#[test]
fn regress_protected_amount_stays_raster() {
    let (rgb, w, h, page) = fixture("p16_statement", "p16_statement");
    // protect the "Amount" span's box: caller-provided protection has priority
    let amount = page.spans.iter().find(|s| s.text == "Amount").expect("Amount span");
    let mut input = convert_input(&rgb, w, h, "p16", &page);
    input.protected_regions = vec![ProtectedInput {
        id: "prot-amount".into(),
        polygon: amount.polygon.clone(),
        reason: "financial".into(),
    }];
    let out = convert(&input, &measurement_policy()).expect("conversion");
    let r = &out.report;
    assert!(
        r.fallback_reasons.contains_key("Protected"),
        "protected regions must force raster fallback, got {:?}",
        r.fallback_reasons
    );
    // every span keeps exactly one owner (the protected span is overlaid)
    assert!(r.semantic_owner.values().all(|o| o == "visible_tounicode" || o == "invisible"));
    // the protection pixels are reproduced exactly: the fallback patch covering
    // the protected box is byte-identical to the source crop
    let xs: Vec<f64> = amount.polygon.iter().map(|p| p[0]).collect();
    let ys: Vec<f64> = amount.polygon.iter().map(|p| p[1]).collect();
    let (x0, y0) = (xs.iter().cloned().fold(f64::MAX, f64::min) as usize, ys.iter().cloned().fold(f64::MAX, f64::min) as usize);
    let (x1, y1) = (xs.iter().cloned().fold(f64::MIN, f64::max) as usize, ys.iter().cloned().fold(f64::MIN, f64::max) as usize);
    let covering = r.patches.iter().any(|p| {
        p.bbox_px[0] <= x0 as f64 && p.bbox_px[1] <= y0 as f64 && p.bbox_px[2] >= x1 as f64 && p.bbox_px[3] >= y1 as f64
    });
    assert!(covering, "the protected box must be covered by an exact source patch");
}

/// P1-1: physical dimensions come from the page's affine, never from --dpi.
/// A 600 dpi scan must not be laid out at the bundle's 300 dpi default.
#[test]
fn regress_geometry_uses_the_page_affine() {
    let (rgb, w, h, mut page) = fixture("p13_nontext", "p13_nontext");
    // re-declare the page as a 600 dpi scan: the affine is authoritative
    let m = [72.0 / 600.0, 0.0, 0.0, -72.0 / 600.0, 0.0, h as f64 * 72.0 / 600.0];
    page.page.raster_to_page_pt = m;
    page.page.width_pt = w as f64 * 72.0 / 600.0;
    page.page.height_pt = h as f64 * 72.0 / 600.0;
    page.raster.dpi_x = Some(600.0);
    page.raster.dpi_y = Some(600.0);
    let input = convert_input(&rgb, w, h, "p13", &page);
    // the same --dpi 300 the bundle default would pass: the affine must win
    let policy = m0_font_pdf::Policy { min_ink_iou: 0.0, ..m0_font_pdf::Policy::default() };
    let out = convert(&input, &policy).expect("conversion");
    let want_w = (w as f64 * 72.0 / 600.0) as f32;
    assert!(
        (out.report.policy.dpi - 300.0).abs() < 1e-9,
        "the CLI dpi is the sampling hint; the page affine is authoritative"
    );
    let pdf = support::decoded_syntax(&out.pdf_bytes);
    assert!(
        pdf.contains(&format!("[0 0 {want_w} ")),
        "the MediaBox must use the page's 600 dpi geometry ({want_w}pt), not 300 dpi"
    );
    // a skew must be refused, not silently approximated
    let mut skewed = input.clone();
    skewed.raster_to_page_pt = [0.12, 0.01, 0.0, -0.12, 0.0, 100.0];
    let err = convert(&skewed, &policy).map(|_| ()).unwrap_err();
    assert!(err.contains("unsupported geometry"), "skew must be refused: {err}");
}

/// P1-2: min_ink_iou is enforced — units whose traced outline reproduces the
/// source ink below the policy threshold are NOT vectorized: the region
/// degrades to raster (`FidelityBelowPolicy`) and the report describes the
/// EMITTED content (no surviving vector unit below the threshold). `auto`
/// ranks the degraded reconstruction against the raster baseline by real bytes.
#[test]
fn regress_min_ink_iou_is_enforced() {
    let (rgb, w, h, page) = fixture("p16_statement", "p16_statement");
    let input = convert_input(&rgb, w, h, "p16", &page);
    let strict = m0_font_pdf::Policy { min_ink_iou: 0.98, ..m0_font_pdf::Policy::default() };
    let out = convert(&input, &strict).expect("strict policy degrades, it does not fail");
    let r = &out.report;
    assert!(
        r.fallback_reasons.contains_key("FidelityBelowPolicy"),
        "below-threshold units must degrade to raster, got {:?}",
        r.fallback_reasons
    );
    // the emitted reconstruction contains NO vector unit below the policy:
    // on this page every unit degraded (small antialiased text), so no vector
    // unit is emitted at all
    assert_eq!(
        r.fidelity.vector_ink_iou_min, None,
        "no vector unit may remain below the policy threshold"
    );
    assert!(r.fidelity.units_below_policy >= 45,
        "the small antialiased text units degraded: {}", r.fidelity.units_below_policy);
    assert_eq!(r.fidelity.raster_ink_px, r.coverage.text_ink_px_raster + r.coverage.other_ink_px);

    // auto at the same policy still ranks both candidates by real bytes
    let auto = m0_font_pdf::Policy { mode: "auto".into(), min_ink_iou: 0.98, ..m0_font_pdf::Policy::default() };
    let out2 = convert(&input, &auto).expect("auto");
    assert_eq!(out2.report.candidates.len(), 2);
    assert!(out2.report.candidates.iter().any(|(n, _)| n == "reconstruct"));
    assert!(out2.report.candidates.iter().any(|(n, _)| n == "raster_baseline"));

    // on a page where the traces meet the policy, units stay vectorized and the
    // reported minimum satisfies the threshold
    let (rgb1, w1, h1, page1) = fixture("p01_latin", "p01_latin");
    let in1 = convert_input(&rgb1, w1, h1, "p01", &page1);
    let o1 = convert(&in1, &strict).expect("p01 at 0.98");
    let m1 = o1.report.fidelity.vector_ink_iou_min.expect("p01 keeps vectors");
    assert!(m1 >= 0.98, "surviving vector units must satisfy the policy, min={m1}");
    assert!(o1.report.coverage.text_ink_px_vector > 0, "p01 stays vectorized");

    // a calibrated policy admits the vectors and reports the measure honestly
    let loose = m0_font_pdf::Policy { min_ink_iou: 0.5, ..m0_font_pdf::Policy::default() };
    let out3 = convert(&input, &loose).expect("calibrated policy converts");
    assert_eq!(out3.report.selected, "reconstruct");
    let m = out3.report.fidelity.vector_ink_iou_min.expect("measured");
    assert!(m >= 0.5, "the reported fidelity must satisfy the stated policy");
    assert_eq!(out3.report.fidelity.units_below_policy, 0, "nothing degraded at 0.5");
    // the strict policy degrades strictly more than the calibrated one
    assert!(r.coverage.text_ink_px_raster > out3.report.coverage.text_ink_px_raster);
}

/// P1-3/P1-4: repeated identical OCR text keeps BOTH spans' owners, and the
/// document-wide CID table deduplicates repeated (glyph, string) pairs.
#[test]
fn regress_repeated_spans_keep_owners_and_cids_dedup() {
    // two spans with identical OCR text; the second is covered by a solid block
    let (w, h) = (400u32, 150u32);
    let mut rgb = vec![250u8; (w * h * 3) as usize];
    let mut page = repeated_span_page(w, h, 220);
    // draw "Amount 12.34" once (span 1); span 2's area stays blank (raster-fallback)
    // Make BOTH spans raster-fallback with IDENTICAL text — the exact case
    // where text-based owner dedup silently dropped the second span's label
    // (the pre-fix bug). Each span box gets glyph-like ink AND a solid rule
    // crossing it, so the planner marks the region ContactNonText → raster and
    // the (buggy) raster-region owner loop runs for both spans.
    for x0 in [40u32, 220u32] {
        // glyph-like ink
        for gy in 50..100u32 {
            for gx in x0..(x0 + 90) {
                if (gx + gy) % 7 < 3 {
                    let i = ((gy * w + gx) * 3) as usize;
                    rgb[i] = 20;
                    rgb[i + 1] = 20;
                    rgb[i + 2] = 20;
                }
            }
        }
        // a solid rule crossing the span box (non-text contact)
        for gy in 58..66u32 {
            for gx in x0.saturating_sub(10)..(x0 + 110).min(w) {
                let i = ((gy * w + gx) * 3) as usize;
                rgb[i] = 15;
                rgb[i + 1] = 15;
                rgb[i + 2] = 15;
            }
        }
    }
    page.raster.file_sha256 = scanweave_core::hash_hex(&rgb);
    page.raster.pixel_sha256 = pixel_hash(&rgb, w, h);
    let input = convert_input(&rgb, w, h, "repeated", &page);
    let out = convert(&input, &measurement_policy()).expect("conversion");
    // BOTH spans (identical text) must keep exactly one owner each
    let owners = &out.report.semantic_owner;
    assert_eq!(owners.len(), 2, "both identical-text spans must be present: {owners:?}");
    assert!(owners.contains_key("w0") && owners.contains_key("w1"));
    // both must be FALLBACK owners: that is the code path where the pre-fix
    // text-based dedup dropped the second span
    assert_eq!(owners["w0"], "invisible", "span w0 must be a raster fallback owner");
    assert_eq!(owners["w1"], "invisible", "span w1 must be a raster fallback owner");
    // and each owner run must be discoverable in the PDF: two ActualText marks
    let pdf = support::decoded_syntax(&out.pdf_bytes);
    assert_eq!(
        pdf.matches("/ActualText (Amount 12.34)").count(),
        2,
        "both identical-text fallback spans must carry their own label mark"
    );
    // no unowned/double-owned ink
    assert_eq!(out.report.coverage.unowned_ink_px, 0);
    assert_eq!(out.report.coverage.multiply_owned_ink_px, 0);

    // cross-page CID reuse: the same page twice in one document must NOT mint
    // duplicate CIDs for the same (glyph, string) pairs. The font bytes alone
    // cannot show this (fontbuild dedups its own cmap), so count the CIDs the
    // document actually emits: the CIDToGIDMap + ToUnicode tables must cover
    // exactly the distinct (glyph, string) pairs of ONE page, not two.
    use scanweave_io::document::convert_document;
    let inputs = vec![input.clone(), input.clone()];
    let doc = convert_document("repeated-doc", &inputs, &measurement_policy()).expect("document");
    let per_page = doc.report.page_reports.iter().map(|p| p.font_glyphs).collect::<Vec<_>>();
    assert_eq!(per_page[0], per_page[1], "identical pages must trace identical glyphs");
    let pdf = support::decoded_syntax(&doc.pdf_bytes);
    let bfchars = pdf.matches("beginbfchar").count();
    assert!(bfchars >= 1, "the document font must carry a ToUnicode map");
    // count the CID entries the document's maps declare
    let declared: Vec<usize> = pdf
        .match_indices("endbfchar")
        .filter_map(|(i, _)| {
            let head = &pdf[..i];
            let seg = head.rsplit("beginbfchar").next()?;
            Some(seg.matches('<').count())
        })
        .collect();
    let total_declared: usize = declared.iter().sum();
    // one page's distinct (glyph, string) pairs = its font glyphs; the document
    // must not exceed one page's worth (the second page reuses every CID)
    assert!(
        total_declared <= per_page[0] + 1,
        "document CID table ({total_declared}) must not exceed one page's ({}); \
         cross-page CIDs are not being reused",
        per_page[0] + 1
    );
}

/// P2: top-level accounting must describe the emitted candidate. A 1.0
/// preservation requirement is not an instruction to select the baseline:
/// low-fidelity units may fall back before the reconstruction is ranked.
#[test]
fn regress_auto_reports_the_selected_candidate() {
    use scanweave_io::document::convert_document;
    let doc = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/documents/doc4_invoice");
    let bundle_bytes = std::fs::read(doc.join("document.json")).unwrap();
    let bundle = scanweave_core::bundle::Bundle::parse_bytes(&bundle_bytes).unwrap();
    bundle.verify_pairing(&doc, &Limits::m0_defaults()).unwrap();
    let mut inputs = Vec::new();
    for p in &bundle.pages {
        let img = image::open(doc.join(format!("{}.png", p.page_id))).unwrap().to_rgb8();
        let (w, h) = (img.width(), img.height());
        let ocr = OcrPage::parse_bytes(&std::fs::read(doc.join(&p.ocr_page_path)).unwrap()).unwrap();
        inputs.push(scanweave_io::convert::input_from_ocr_page(img.as_raw(), w, h, &p.page_id, &ocr));
    }
    // Exercise strict preservation without assuming which serialized candidate wins.
    let policy = m0_font_pdf::Policy { mode: "auto".into(), min_ink_iou: 1.0, ..m0_font_pdf::Policy::default() };
    let out = convert_document("doc", &inputs, &policy).expect("auto Document");
    let selected = out.report.candidates.iter()
        .find(|c| c.name == out.report.selected).expect("selected candidate is recorded");
    let cheapest = out.report.candidates.iter().min_by_key(|c| c.pdf_bytes).unwrap();
    assert_eq!(selected.pdf_bytes, cheapest.pdf_bytes, "both candidates satisfy strict preservation");
    assert_eq!(out.report.pdf_bytes, out.pdf_bytes.len());
    assert_eq!(out.report.pdf_bytes, selected.pdf_bytes);
    assert_eq!(out.report.image_xobjects, selected.image_xobjects);
    assert_eq!(out.report.content_bytes, selected.content_bytes);
    assert_eq!(out.report.font_bytes, selected.font_bytes);
    assert_eq!(out.report.raster_encoded_bytes, selected.raster_encoded_bytes);
    assert_eq!(out.report.page_fidelity, selected.page_fidelity);
    assert_eq!(out.report.page_fidelity.len(), 4);
    assert!(out.report.page_fidelity.iter().all(|f| f.is_none_or(|v| v >= 1.0)));
    assert_eq!(out.report.candidates.len(), 2);
    assert!(out.report.candidates.iter().all(|c| c.pdf_bytes > 0));
    if out.report.selected == "raster_baseline" {
        assert_eq!(out.pdf_bytes, out.raster_baseline_pdf_bytes);
        assert_eq!(out.report.page_fidelity, vec![Some(1.0); 4]);
    }

}
