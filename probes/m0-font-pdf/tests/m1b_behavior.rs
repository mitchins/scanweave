//! M1-B behavioral tests. Written BEFORE the implementation changes they cover
//! (red→green): line-level search semantics, patch economy, auto selection,
//! document assembly, and the M1A-05 contact regression.

use m0_font_pdf::shim::{convert_input, convert_with};
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
/// searchable natively: the fallback owner run is drawn VISIBLY (empty
/// placeholder glyph paints nothing — the raster patch carries the pixels) at
/// the span position, emitted INLINE in reading order, with its own per-span
/// /ActualText carrying the OCR label. This is the PDFium native-search fix
/// for N1 (invisible runs were hoisted to the end of the text page).
#[test]
fn m1b01_mixed_line_owner_run_is_visible_and_inline() {
    let out = build("p10_multipage/page1", "p10_page1", None);
    let pdf = String::from_utf8_lossy(&out.pdf_bytes);
    let bt = pdf.find("BT\n").expect("text object");
    let et = pdf.rfind("ET\n").expect("text object end");
    let content = &pdf[bt..=et];
    // the fallback span "1" carries its own per-span ActualText (pdf_writer
    // emits ActualText as a literal PDF string, e.g. (1))
    assert!(
        pdf.contains("/ActualText (1)"),
        "fallback span must carry its label via /ActualText"
    );
    // and its run sits between "Page"'s EMC and "of"'s BDC (inline, reading order)
    let page_end = content.find("/ActualText (Page)").expect("Page mark");
    let seg = &content[page_end..];
    let page_emc = seg.find("EMC").expect("Page mark close");
    let owner_at = seg.find("/ActualText (1)").expect("owner mark");
    let of_bdc = seg.find("/ActualText (of)").expect("of mark");
    assert!(
        page_emc < owner_at && owner_at < of_bdc,
        "owner run must be emitted inline between the visible spans of its line"
    );
    // the owner run is VISIBLE (no invisible rendering mode around it)
    let owner_run = &seg[owner_at..of_bdc];
    assert!(
        !owner_run.contains("3 Tr"),
        "the owner run must not be invisible (PDFium hoists invisible runs)"
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

/// M1B-05: M1A-05 regression — text touching a rule / stamp / barcode must keep
/// the ContactNonText fallback AND still be searchable via the owner overlay,
/// with no unowned or double-owned ink.
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
    }
}
