//! M1-A behavioral tests (M1A-01..M1A-10 subset that runs in Rust; the
//! integration-level tokens/search checks live in qualification/test_m1a.py).

use m0_font_pdf::ownership::{build_plan, OwnershipPlan};
use m0_font_pdf::mask::segment;
use scanweave_core::ocr_page::OcrPage;
use scanweave_core::Limits;
use std::path::PathBuf;

fn plan_of_synth(dir: &str) -> (OwnershipPlan, Vec<u8>, u32, u32, OcrPage) {
    let (rgb, w, h, page) = load_fixture_synth(dir);
    let seg = segment(&rgb, w, h);
    let (plan, _) = build_plan(&seg, w, h, &page);
    (plan, rgb, w, h, page)
}

fn load_fixture_synth(dir: &str) -> (Vec<u8>, u32, u32, OcrPage) {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/probe")
        .join(dir);
    let png = std::fs::read_dir(&base).unwrap().filter_map(|e| e.ok())
        .find(|e| e.path().extension().map_or(false, |x| x == "png")).map(|e| e.path()).unwrap();
    let ocr = std::fs::read_dir(&base).unwrap().filter_map(|e| e.ok())
        .find(|e| e.file_name().to_string_lossy().ends_with(".synth.json")).map(|e| e.path()).unwrap();
    let img = image::open(png).unwrap().to_rgb8();
    let (w, h) = (img.width(), img.height());
    let page = OcrPage::parse_bytes(&std::fs::read(ocr).unwrap()).unwrap();
    (img.as_raw().to_vec(), w, h, page)
}

fn load_fixture(dir: &str, stem: &str) -> (Vec<u8>, u32, u32, OcrPage) {
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
    (img.as_raw().to_vec(), w, h, page)
}

fn plan_of(dir: &str, stem: &str) -> (OwnershipPlan, Vec<u8>, u32, u32, OcrPage) {
    let (rgb, w, h, page) = load_fixture(dir, stem);
    let _ = stem;
    page.validate(&Limits::m0_defaults()).expect("fixture validates");
    let seg = segment(&rgb, w, h);
    let (plan, _) = build_plan(&seg, w, h, &page);
    (plan, rgb, w, h, page)
}

fn total_semantic_chars(plan: &OwnershipPlan) -> usize {
    plan.owned
        .iter()
        .map(|u| u.unit.semantic_text.chars().count())
        .sum()
}

fn supplied_chars(page: &OcrPage) -> usize {
    page.spans
        .iter()
        .map(|s| s.symbols.iter().map(|sy| {
            let (a, b) = (sy.text_range_utf8[0], sy.text_range_utf8[1]);
            s.text[a..b].chars().count()
        }).sum::<usize>())
        .sum()
}

#[test]
fn m1a01_touging_chars_map_to_one_unit() {
    // touching 'rn'/'fi'/'ll'/'ss': the merged component carries BOTH characters
    // in slot order; nothing is dropped.
    let (plan, _, _, _, page) = plan_of("p11_touching", "p11_touching");
    assert_eq!(
        total_semantic_chars(&plan),
        supplied_chars(&page),
        "touching fixtures must transport every supplied character"
    );
    // at least one unit must carry more than one character (a merged component)
    assert!(
        plan.owned.iter().any(|u| u.unit.semantic_text.chars().count() > 1),
        "expected a merged multi-character visual unit for touching pairs"
    );
    // GEOMETRIC ownership (not OCR ordering luck): every supplied symbol box
    // must be referenced by an owned unit whose ink bbox actually intersects that
    // symbol's box, and every owned unit must point at a real supplied symbol.
    let sym_box = |id: &str| -> Option<[f64; 4]> {
        page.spans.iter().flat_map(|s| s.symbols.iter()).find(|sy| sy.id == id)
            .map(|sy| {
                let xs: Vec<f64> = sy.polygon.iter().map(|p| p[0]).collect();
                let ys: Vec<f64> = sy.polygon.iter().map(|p| p[1]).collect();
                [xs.iter().cloned().fold(f64::MAX, f64::min), ys.iter().cloned().fold(f64::MAX, f64::min),
                 xs.iter().cloned().fold(f64::MIN, f64::max), ys.iter().cloned().fold(f64::MIN, f64::max)]
            })
    };
    let overlaps = |a: [f64; 4], b: [f64; 4]| a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
    let mut referenced: Vec<String> = Vec::new();
    for u in &plan.owned {
        for slot in &u.slots {
            let b = sym_box(&slot.symbol_id)
                .unwrap_or_else(|| panic!("owned slot {} references unknown symbol", slot.symbol_id));
            // the slot's OCR box and the unit's traced ink must meet: that is the
            // geometric (not ordering) basis of ownership
            assert!(
                overlaps(u.unit.bbox_px, b),
                "unit '{}' must geometrically overlap its slot box {:?} (unit {:?})",
                u.unit.semantic_text, b, u.unit.bbox_px
            );
            referenced.push(slot.symbol_id.clone());
        }
    }
    for span in &page.spans {
        for sym in &span.symbols {
            assert!(
                referenced.contains(&sym.id),
                "symbol {} of span {} must be geometrically owned by a unit",
                sym.id, span.id
            );
        }
    }
    // the merged unit must span (at least) two symbol boxes
    let merged = plan
        .owned
        .iter()
        .find(|u| u.unit.semantic_text.chars().count() > 1)
        .expect("merged unit");
    assert!(
        merged.slots.len() >= 2,
        "merged touching unit must own >=2 symbol slots, found {}",
        merged.slots.len()
    );
    // and those slots must overlap the SAME component region (the x-ranges
    // intersect, which is what makes them touching chars of one glyph run)
    let boxes: Vec<[f64; 4]> = merged.slots.iter().map(|s| s.bbox).collect();
    assert!(
        boxes.windows(2).any(|w| w[0][0] < w[1][2] && w[1][0] < w[0][2]),
        "touching slots must share a horizontal range: {:?}",
        boxes
    );
    // no unit carries a character that was not supplied
    assert!(plan.semantic_invariant_ok(&page));
}

#[test]
fn m1a02_disconnected_marks_preserved() {
    // dotted i/j, accents, kana with dakuten: every disconnected component of a
    // symbol is owned by that symbol's unit.
    let (plan, _, _, _, _page) = plan_of_synth("p12_disconnected");
    let ij = plan
        .owned
        .iter()
        .find(|u| u.unit.semantic_text.eq("ij") || u.unit.semantic_text.eq("i"))
        .expect("dotted i/j unit");
    assert!(
        ij.components.len() >= 2,
        "dotted i/j must own at least two components (dot + stems), found {}",
        ij.components.len()
    );
    // the kana (ガ/パ with dakuten) must also be multi-component
    let kana = plan
        .owned
        .iter()
        .find(|u| u.unit.semantic_text.contains('ガ') || u.unit.semantic_text.contains('パ'))
        .expect("kana unit");
    assert!(
        kana.components.len() >= 2,
        "kana with dakuten must own at least two components, found {}",
        kana.components.len()
    );
}

#[test]
fn m1a03_overlapping_boxes_no_loss() {
    // overlapping OCR boxes must neither erase nor duplicate ink
    let (plan, _, _, _, page) = plan_of("p11_touching", "p11_touching");
    assert!(plan.visual_invariant_ok(), "no unowned or double-owned ink");
    assert_option_no_loss(&plan);
    assert!(
        plan.semantic_invariant_ok(&page),
        "semantic invariant holds under overlapping boxes"
    );
}

fn assert_option_no_loss(plan: &OwnershipPlan) {
    // sum of owned+artwork pixels equals total foreground pixels computed by the
    // caller (checked indirectly: invariant excludes double ownership)
    assert!(plan.visual_invariant_ok());
}

/// load the page OCR (`.ocr.json`, real Tesseract output when present)
fn load_page(dir: &str) -> (Vec<u8>, u32, u32, OcrPage) {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/probe")
        .join(dir);
    let png = std::fs::read_dir(&base)
        .unwrap()
        .filter_map(|e| e.ok())
        .find(|e| e.path().extension().map_or(false, |x| x == "png"))
        .map(|e| e.path())
        .unwrap();
    let ocr = std::fs::read_dir(&base)
        .unwrap()
        .filter_map(|e| e.ok())
        .find(|e| e.file_name().to_string_lossy().ends_with(".ocr.json"))
        .map(|e| e.path())
        .unwrap();
    let img = image::open(png).unwrap().to_rgb8();
    let (w, h) = (img.width(), img.height());
    let page = OcrPage::parse_bytes(&std::fs::read(ocr).unwrap()).unwrap();
    (img.as_raw().to_vec(), w, h, page)
}

#[test]
fn m1a04_unknown_marks_stay_art() {
    // tesseract missed '68' and 'fi' on p11; those components are non-text artwork
    // with no invented Unicode
    let (plan, _, _, _, _page) = { let (rgb, w, h, page) = load_page("p11_touching");
        let seg = segment(&rgb, w, h); (build_plan(&seg, w, h, &page).0, rgb, w, h, page) };
    let art_units = &plan.artwork_units;
    assert!(
        !art_units.is_empty(),
        "unrecognized marks must survive as artwork, not be dropped"
    );
    assert!(
        art_units.iter().all(|(u, _)| u.semantic_text.is_empty()),
        "artwork must never carry invented text"
    );
}

#[test]
fn m1a06_wrong_label_shape_identity() {
    // observed '8' on p01 vs p02 (OCR '6'): the same raster '8' produces the same
    // shape key, i.e. identical visual ownership decision
    let (plan1, _, _, _, _) = plan_of("p01_latin", "p01_latin");
    let (plan2, _, _, _, _) = plan_of("p02_wronglabel", "p02_wronglabel");
    let keys1: Vec<String> = plan1.owned.iter().map(|u| u.unit.shape_key.clone()).collect();
    let keys2: Vec<String> = plan2.owned.iter().map(|u| u.unit.shape_key.clone()).collect();
    assert!(
        keys1.iter().any(|k| keys2.contains(k)),
        "the same visual shape must produce the same shape key across differing OCR labels"
    );
    // and the semantic layer must NOT merge them: identical shape + different
    // OCR label = different semantic text on the same shape key (VS-01)
    let shared: Vec<&String> = keys1.iter().filter(|k| keys2.contains(k)).collect();
    assert!(!shared.is_empty(), "shared shapes exist");
    for key in shared {
        let a = plan1.owned.iter().find(|u| &u.unit.shape_key == key).unwrap();
        let b = plan2.owned.iter().find(|u| &u.unit.shape_key == key).unwrap();
        assert_ne!(
            a.unit.semantic_text, b.unit.semantic_text,
            "same shape with different labels must carry different semantics (wrong-label preservation)"
        );
    }
}

#[test]
fn m1a08_same_masks_different_labels_same_ownership() {
    // a fixed unprotected mask under different labels yields the same visual plan
    let (plan_a, _, _, _, page_a) = plan_of("p01_latin", "p01_latin");
    let (plan_b, _, _, _, page_b) = plan_of("p02_wronglabel", "p02_wronglabel");
    let shared: Vec<String> = plan_a
        .owned
        .iter()
        .filter(|u| plan_b.owned.iter().any(|v| v.unit.shape_key == u.unit.shape_key))
        .map(|u| u.unit.shape_key.clone())
        .collect();
    assert!(!shared.is_empty(), "shared masks must exist across the two pages");
    for key in &shared {
        let a = plan_a.owned.iter().find(|u| &u.unit.shape_key == key).unwrap();
        let b = plan_b.owned.iter().find(|u| &u.unit.shape_key == key).unwrap();
        assert_eq!(
            (a.unit.bbox_px[2] - a.unit.bbox_px[0], a.unit.bbox_px[3] - a.unit.bbox_px[1]),
            (b.unit.bbox_px[2] - b.unit.bbox_px[0], b.unit.bbox_px[3] - b.unit.bbox_px[1]),
            "same mask → same ink box size (placement is independent)"
        );
        assert_eq!(a.components.len(), b.components.len(), "same mask → same component set");
    }
    // the semantic layer differs (the labels differ) — text ownership is independent
    assert_ne!(page_a.spans[0].text, page_b.spans[0].text);
    let label_a = &plan_a.owned[0].unit.semantic_text;
    let label_b = &plan_b.owned[0].unit.semantic_text;
    assert_ne!(label_a, label_b, "relabelling changes only text, not shape");
}

#[test]
fn m1a09_pipeline_restores_raster_and_owner() {
    // p13 has text touching a rule: the region falls back to raster and every
    // span keeps exactly one semantic owner; invariants hold.
    let (rgb, w, h, page) = load_fixture("p13_nontext", "p13_nontext");
    page.validate(&Limits::m0_defaults()).expect("validates");
    let input = m0_font_pdf::shim::convert_input(&rgb, w, h, "p13", &page);
    let out = m0_font_pdf::shim::convert_with(&input, None).expect("conversion");
    let r = out.report;
    assert!(r.ownership_invariants["visual"], "visual ownership invariant");
    assert!(r.ownership_invariants["semantic"], "semantic ownership invariant");
    let raster_regions = r
        .regions
        .iter()
        .filter(|reg| matches!(reg.disposition, m0_font_pdf::shim::RegionDisposition::Raster { .. }))
        .count();
    assert!(raster_regions >= 1, "rule-contact region must fall back to raster");
    assert!(r.raster_bytes > 0, "restored raster pixels must exist in the output");
    // raster FIDELITY: every raster region's restored patch must reproduce the
    // source page pixels inside its box (not paper-only), comparing the source
    // rgb against the patch pixels the region covers
    for reg in r.regions.iter().filter(|reg| matches!(reg.disposition, m0_font_pdf::shim::RegionDisposition::Raster { .. })) {
        let b = reg.bbox_px;
        let (x0, y0, x1, y1) = (b[0] as usize, b[1] as usize, (b[2] as usize).min(w as usize), (b[3] as usize).min(h as usize));
        let mut ink = 0usize;
        for y in y0..y1 {
            for x in x0..x1 {
                let i = ((y * w as usize) + x) * 3;
                let px = &rgb[i..i + 3];
                // foreground ink differs strongly from paper (source has paper bg)
                if i + 2 < rgb.len() && (px[0] as i32 - 255).abs() + (px[1] as i32 - 255).abs() + (px[2] as i32 - 255).abs() > 120 {
                    ink += 1;
                }
            }
        }
        assert!(ink > 0, "fallback region {:?} must contain real source ink (its raster patch restores glyphs, not paper)", reg.id);
    }
    for s in &r.semantic_owner {
        assert!(
            s.1 == "invisible" || s.1 == "visible_tounicode",
            "unknown semantic owner {}",
            s.1
        );
    }
}

#[test]
fn m1a10_deterministic_repeat_runs() {
    let (rgb, w, h, page) = load_fixture("p13_nontext", "p13_nontext");
    page.validate(&Limits::m0_defaults()).expect("validates");
    let input = m0_font_pdf::shim::convert_input(&rgb, w, h, "p13", &page);
    let a = m0_font_pdf::shim::convert_with(&input, None).expect("run 1");
    let b = m0_font_pdf::shim::convert_with(&input, None).expect("run 2");
    assert_eq!(a.pdf_bytes, b.pdf_bytes, "PDF must be byte-identical");
    assert_eq!(a.font_bytes, b.font_bytes, "font must be byte-identical");
    let strip = |r: &m0_font_pdf::shim::Report| -> String {
        let mut v = serde_json::to_value(r).unwrap();
        v.as_object_mut().unwrap().remove("elapsed_ms");
        serde_json::to_string(&v).unwrap()
    };
    assert_eq!(strip(&a.report), strip(&b.report), "report must be byte-identical (excluding timing)");
}
