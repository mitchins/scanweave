//! M1-B behavioral tests. Written BEFORE the implementation changes they cover
//! (red→green): line-level search semantics, patch economy, auto selection,
//! document assembly, and the M1A-05 contact regression.

use m0_font_pdf::shim::{convert_input, convert_with};
use m0_font_pdf::convert as io_convert;
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
    convert_with(&input, policy).expect("conversion")
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
    let pdf = String::from_utf8_lossy(&out.pdf_bytes);
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
    let pdf = String::from_utf8_lossy(&out.pdf_bytes);
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
    let out = convert_with(&input, None).expect("convert");
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
    let images = String::from_utf8_lossy(&out.pdf_bytes)
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
    let out = convert_with(&input, Some(&Policy { mode: "auto".into(), ..Policy::default() }))
        .expect("auto convert");
    let r = &out.report;
    assert_eq!(r.policy.mode, "auto");
    // the selected candidate must still carry every span's label
    assert!(r.semantic_owner.values().all(|o| o == "visible_tounicode" || o == "invisible"));
    // and it must not be larger than the reconstruct candidate on the same page
    let recon = convert_with(
        &Input { rgb: rgb.clone(), ..input.clone() },
        Some(&Policy { mode: "reconstruct".into(), ..Policy::default() }),
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
    let policy = Policy::default();
    let out = convert_document(&bundle.document_id, &inputs, &policy).expect("document");
    let pdf = String::from_utf8_lossy(&out.pdf_bytes);

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
    let out = convert_document(&bundle.document_id, &inputs, &Policy::default()).unwrap();
    let separate: usize = inputs
        .iter()
        .map(|i| io_convert(i, &Policy::default()).unwrap().pdf_bytes.len())
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
