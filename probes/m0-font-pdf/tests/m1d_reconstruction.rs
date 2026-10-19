use m0_font_pdf::Policy;
mod support;

use scanweave_io::convert::{convert, Input, SpanInput, SymbolInput};
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize)]
struct Fixture {
    width: u32,
    height: u32,
    observations: Vec<Observation>,
}
#[derive(Deserialize)]
struct Observation {
    id: String,
    text: String,
    bbox: [f64; 4],
}

fn fixture_input() -> Input {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../qualification/fixtures/m1d_damage");
    let image = image::open(root.join("source.png")).unwrap().to_rgb8();
    let fixture: Fixture = serde_json::from_slice(&std::fs::read(root.join("positions.json")).unwrap()).unwrap();
    let spans = fixture.observations.into_iter().map(|o| {
        let [x0,y0,x1,y1] = o.bbox;
        let polygon = vec![[x0,y0],[x1,y0],[x1,y1],[x0,y1]];
        SpanInput {
            id: o.id.clone(), text: o.text.clone(), separator_after: " ".into(),
            polygon: polygon.clone(),
            symbols: vec![SymbolInput { id: o.id, range: (0, o.text.len()), polygon }],
        }
    }).collect();
    Input {
        rgb: image.as_raw().clone(), width: fixture.width, height: fixture.height,
        page_id: "m1d-damaged-glyph".into(), spans, protected_regions: Vec::new(),
        raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, fixture.height as f64 * 0.24],
        pixel_sha256: None,
    }
}

#[test]
fn clearscan_repairs_a_damaged_glyph_from_same_document_donors() {
    let input = fixture_input();
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../qualification/evidence/m1d_reconstruction");
    std::fs::create_dir_all(&root).unwrap();

    let faithful = convert(&input, &Policy::default()).expect("faithful conversion");
    let clear_policy = Policy {
        profile: "clearscan".into(), glyph_dictionary: "visual".into(),
        min_ink_iou: 0.98, ..Policy::default()
    };
    let clearscan = convert(&input, &clear_policy).expect("ClearScan conversion");

    std::fs::write(root.join("faithful.pdf"), &faithful.pdf_bytes).unwrap();
    std::fs::write(root.join("clearscan.pdf"), &clearscan.pdf_bytes).unwrap();
    std::fs::write(root.join("font.ttf"), &clearscan.font_bytes).unwrap();
    std::fs::write(root.join("reconstruction.json"), serde_json::to_vec_pretty(&clearscan.report).unwrap()).unwrap();
    std::fs::write(root.join("source.png"), std::fs::read(
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../qualification/fixtures/m1d_damage/source.png")
    ).unwrap()).unwrap();

    let repaired: Vec<_> = clearscan.report.reconstruction.occurrences.iter().filter(|o| o.repaired).collect();
    assert_eq!(repaired.len(), 1, "only the deliberately damaged e should be repaired");
    assert_eq!(repaired[0].symbol_id, "s00");
    assert!(repaired[0].similarity.unwrap() < 0.96,
        "repair must qualify below the old near-identical mask rule");
    assert!(repaired[0].source_mask_iou.unwrap() < 0.98,
        "the preserved source-mask gate must reject this repaired occurrence");
    assert!(clearscan.report.reconstruction.restoration_qualified);
    assert_eq!(clearscan.report.reconstruction.observations.len(), 27);
    let prototype = clearscan.report.reconstruction.prototypes.iter()
        .find(|p| p.members.contains(&"s02".to_string())).unwrap();
    assert_eq!(prototype.members.len(), 10, "only intact cohort members should be donors");
    assert!(!prototype.members.contains(&"s00".to_string()));
    assert!(!prototype.members.contains(&"s01".to_string()));
    assert_eq!(repaired[0].text, "e", "the accepted occurrence must retain OCR Unicode");
    assert!(repaired.iter().all(|o| o.decision == "repaired_from_document_donors"));
    let alternate_ids = ["s24", "s25", "s26"];
    assert_eq!(clearscan.report.reconstruction.observations.iter()
        .filter(|o| alternate_ids.contains(&o.symbol_id.as_str())).count(), 3);
    assert!(!prototype.members.iter().any(|id| alternate_ids.contains(&id.as_str())),
        "the alternate typeface was mixed into the main e prototype");
    assert!(!repaired.iter().any(|o| matches!(o.text.as_str(), "6" | "8" | "0" | "O")));

    let faithful_s00 = faithful.report.occurrences.iter().find(|o| o.symbol_id == "s00").unwrap();
    let clear_s00 = clearscan.report.occurrences.iter().find(|o| o.symbol_id == "s00").unwrap();
    assert_eq!(faithful_s00.owner, "invisible", "faithful must preserve damaged raster text");
    assert_eq!(clear_s00.owner, "visible_tounicode", "ClearScan must paint the selected vector prototype");
    let pdf = support::decoded_syntax(&clearscan.pdf_bytes);
    assert!(pdf.contains("/FontFile2"), "embedded TrueType font is required");
    assert_ne!(faithful.pdf_bytes, clearscan.pdf_bytes, "restoration must materially change the PDF");
}
