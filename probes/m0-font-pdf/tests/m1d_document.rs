use m0_font_pdf::Policy;
use scanweave_io::convert::{Input, SpanInput, SymbolInput};
use scanweave_io::document::convert_document;
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize)]
struct Fixture {
    dpi: f64,
    pages: Vec<Page>,
}
#[derive(Deserialize)]
struct Page {
    page_id: String,
    image: String,
    truth_image: String,
    width: u32,
    height: u32,
    observations: Vec<Observation>,
    protected: Vec<[f64; 4]>,
}
#[derive(Deserialize)]
struct Observation {
    id: String,
    text: String,
    bbox: [f64; 4],
}

fn fixture(dpi: u32, pristine: bool) -> Vec<Input> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../");
    let manifest: Fixture = serde_json::from_slice(
        &std::fs::read(root.join(format!(
            "qualification/fixtures/m1d_document/document-{dpi}.json"
        )))
        .unwrap(),
    )
    .unwrap();
    assert_eq!(manifest.dpi, dpi as f64);
    manifest
        .pages
        .into_iter()
        .map(|p| {
            let image_path = if pristine { p.truth_image } else { p.image };
            let image = image::open(root.join(image_path)).unwrap().to_rgb8();
            let spans = p
                .observations
                .into_iter()
                .map(|o| {
                    let [x0, y0, x1, y1] = o.bbox;
                    let polygon = vec![[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
                    SpanInput {
                        id: o.id.clone(),
                        text: o.text.clone(),
                        separator_after: "".into(),
                        polygon: polygon.clone(),
                        symbols: vec![SymbolInput {
                            id: o.id,
                            range: (0, o.text.len()),
                            polygon,
                        }],
                    }
                })
                .collect();
            Input {
                rgb: image.as_raw().clone(),
                width: p.width,
                height: p.height,
                page_id: p.page_id,
                spans,
                protected_regions: p
                    .protected
                    .into_iter()
                    .enumerate()
                    .map(
                        |(i, [x0, y0, x1, y1])| scanweave_io::convert::ProtectedInput {
                            id: format!("protected-{i}"),
                            polygon: vec![[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                            reason: "financial_amount".into(),
                        },
                    )
                    .collect(),
                raster_to_page_pt: [
                    72.0 / dpi as f64,
                    0.0,
                    0.0,
                    -72.0 / dpi as f64,
                    0.0,
                    p.height as f64 * 72.0 / dpi as f64,
                ],
                pixel_sha256: None,
            }
        })
        .collect()
}

fn run_document(dpi: u32) {
    let inputs = fixture(dpi, false);
    let policy = Policy {
        profile: "clearscan".into(),
        glyph_dictionary: "visual".into(),
        min_ink_iou: 0.98,
        mode: "reconstruct".into(),
        ..Policy::default()
    };
    let out = convert_document(&format!("m1d-book-{dpi}"), &inputs, &policy).unwrap();
    let faithful = convert_document(
        &format!("m1d-book-faithful-{dpi}"),
        &inputs,
        &Policy {
            profile: "faithful".into(),
            glyph_dictionary: "off".into(),
            mode: "auto".into(),
            ..policy.clone()
        },
    )
    .unwrap();
    let pristine_inputs = fixture(dpi, true);
    let truth = convert_document(
        &format!("m1d-book-truth-{dpi}"),
        &pristine_inputs,
        &Policy {
            profile: "faithful".into(),
            glyph_dictionary: "off".into(),
            mode: "auto".into(),
            ..policy.clone()
        },
    )
    .unwrap();
    assert_eq!(out.report.pages, 12);
    assert_eq!(out.report.page_order.len(), 12);
    let first = &out.report.page_reports[0].reconstruction;
    let repaired: Vec<_> = first.occurrences.iter().filter(|o| o.repaired).collect();
    let expected = if dpi == 300 {
        vec!["e", "a"]
    } else {
        vec!["e", "a", "8"]
    };
    assert_eq!(repaired.iter().map(|o| o.text.as_str()).collect::<Vec<_>>(), expected,
        "only supported, visibly beneficial repairs should use sibling-page donors at {dpi} DPI: {repaired:?}");
    let eight_owner = out.report.page_reports[0]
        .occurrences
        .iter()
        .find(|o| o.symbol_id == "p00-s02")
        .unwrap();
    assert_eq!(
        eight_owner.owner,
        if dpi == 300 {
            "invisible"
        } else {
            "visible_tounicode"
        },
        "a rejected 300-DPI repair must preserve its exact raster source"
    );
    assert!(repaired.iter().all(|o| o.similarity.unwrap_or(1.0) < 0.96));
    assert!(repaired.iter().all(|o| o.prototype_id.is_some()));
    assert!(out
        .report
        .page_reports
        .iter()
        .all(|r| r.reconstruction.restoration_qualified));
    assert!(out.pdf_bytes.starts_with(b"%PDF-"));
    assert!(out.report.pdf_bytes > 0 && out.report.font_bytes > 0);
    for amount in [
        "p00-amount00",
        "p00-amount01",
        "p00-amount02",
        "p00-amount03",
        "p00-amount04",
        "p00-amount05",
        "p00-amount06",
    ] {
        let occurrence = out.report.page_reports[0]
            .occurrences
            .iter()
            .find(|o| o.symbol_id == amount)
            .unwrap();
        assert_eq!(
            occurrence.owner, "invisible",
            "protected financial text must remain source raster"
        );
    }
    let misrecognized = out.report.page_reports[11]
        .reconstruction
        .occurrences
        .iter()
        .find(|o| o.symbol_id == "p11-s06")
        .unwrap();
    assert_eq!(misrecognized.text, "c");
    assert!(
        !misrecognized.repaired,
        "OCR misrecognition cannot authorize a replacement"
    );

    let evidence = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(format!(
        "../../qualification/evidence/m1d_document/dpi{dpi}"
    ));
    std::fs::create_dir_all(&evidence).unwrap();
    std::fs::write(evidence.join("clearscan.pdf"), &out.pdf_bytes).unwrap();
    std::fs::write(evidence.join("faithful.pdf"), &faithful.pdf_bytes).unwrap();
    std::fs::write(evidence.join("truth.pdf"), &truth.raster_baseline_pdf_bytes).unwrap();
    std::fs::write(
        evidence.join("raster-baseline.pdf"),
        &out.raster_baseline_pdf_bytes,
    )
    .unwrap();
    std::fs::write(evidence.join("font.ttf"), &out.font_bytes).unwrap();
    std::fs::write(
        evidence.join("clearscan-report.json"),
        serde_json::to_vec_pretty(&out.report).unwrap(),
    )
    .unwrap();
    std::fs::write(
        evidence.join("faithful-report.json"),
        serde_json::to_vec_pretty(&faithful.report).unwrap(),
    )
    .unwrap();
}

#[test]
fn document_dictionary_repairs_across_pages_at_300_and_600_dpi() {
    run_document(300);
    run_document(600);
}
