use scanweave_io::convert::{convert_parts, Input, Policy, ProtectedInput, SpanInput, SymbolInput};

fn input(protected: bool) -> Input {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../qualification/fixtures/m1d_damage");
    let image = image::open(root.join("source.png")).unwrap().to_rgb8();
    let data: serde_json::Value =
        serde_json::from_slice(&std::fs::read(root.join("positions.json")).unwrap()).unwrap();
    let polygon = |b: [f64; 4]| vec![[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]];
    let spans = data["observations"]
        .as_array()
        .unwrap()
        .iter()
        .map(|observation| {
            let id = observation["id"].as_str().unwrap().to_string();
            let text = observation["text"].as_str().unwrap().to_string();
            let values = observation["bbox"].as_array().unwrap();
            let mut bbox = [0.0; 4];
            for (value, out) in values.iter().zip(&mut bbox) {
                *out = value.as_f64().unwrap();
            }
            if id == "s02" {
                // Extend the OCR box without changing its ink: the selected donor
                // is rejected by the existing page-geometry gate.
                bbox[2] += 20.0;
            }
            let polygon = polygon(bbox);
            SpanInput {
                id: id.clone(),
                text: text.clone(),
                separator_after: " ".into(),
                polygon: polygon.clone(),
                symbols: vec![SymbolInput {
                    id,
                    range: (0, text.len()),
                    polygon,
                }],
            }
        })
        .collect();
    let protected_regions = if protected {
        vec![ProtectedInput {
            id: "protect-s02".into(),
            polygon: polygon([38.0, 41.0, 91.0, 73.0]),
            reason: "test".into(),
        }]
    } else {
        vec![]
    };
    Input {
        rgb: image.as_raw().clone(),
        width: image.width(),
        height: image.height(),
        page_id: "geometry-fallback".into(),
        spans,
        protected_regions,
        raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, image.height() as f64 * 0.24],
        pixel_sha256: None,
    }
}

#[test]
fn raster_rejected_geometry_has_no_trace_or_font_reference() {
    let policy = Policy {
        profile: "clearscan".into(),
        glyph_dictionary: "visual".into(),
        ..Policy::default()
    };
    for protected in [false, true] {
        let (parts, report) = convert_parts(&input(protected), &policy).unwrap();
        let record = report
            .reconstruction
            .occurrences
            .iter()
            .find(|o| o.symbol_id == "s02")
            .unwrap();
        assert_eq!(record.decision, "rejected_donor_geometry");
        let local = format!("__source_geometry:s02:{}", record.source_shape_key);
        let local_index = parts
            .shapes
            .iter()
            .position(|shape| shape.shape_key == local);
        if protected {
            assert!(
                local_index.is_none(),
                "raster-owned source must not be traced"
            );
            assert!(!parts.occurrences.iter().any(|occ| occ.4 == "s02"));
            let owner = report
                .occurrences
                .iter()
                .find(|o| o.symbol_id == "s02")
                .unwrap();
            assert_eq!(owner.owner, "invisible");
            // Both visible CIDs and invisible owner CIDs index the same encoding
            // table; each encoding maps only to an existing, non-skipped shape.
            for (shape, _) in &parts.encodings {
                assert_ne!(parts.shapes[*shape].shape_key, local);
            }
            for occ in &parts.occurrences {
                assert_eq!(parts.encodings[occ.1 as usize].0, occ.0);
                assert_ne!(parts.shapes[occ.0].shape_key, local);
            }
            for owner in &parts.owners {
                for character in &owner.characters {
                    let shape = parts.encodings[(character.cid - 1) as usize].0;
                    assert_ne!(parts.shapes[shape].shape_key, local);
                }
            }
        } else {
            assert!(
                local_index.is_some(),
                "vector-eligible source must still be traced"
            );
        }
    }
}
