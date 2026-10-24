use scanweave_io::glyph_sharing::{hard_checks, warp};
#[test]
fn frozen_safety_regressions() {
    let f: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/glyph-sharing-regressions.json")).unwrap();
    for c in f["cases"].as_array().unwrap() {
        let field = |name: &str| {
            let mut a = vec![0.; 4096];
            for pair in c[name].as_array().unwrap() {
                a[pair[0].as_u64().unwrap() as usize] = pair[1].as_f64().unwrap();
            }
            a
        };
        let p: [f64; 3] = serde_json::from_value(c["parameters"].clone()).unwrap();
        let got = hard_checks(&field("reference"), &warp(&field("candidate"), p));
        let expected: Vec<String> =
            serde_json::from_value(c["expected_hard_reasons"].clone()).unwrap();
        for component in c["owned_components"].as_array().into_iter().flatten() {
            assert_eq!(
                scanweave_io::glyph_sharing::owned_component_fires(
                    component["owned_area"].as_u64().unwrap() as usize,
                    component["detached_in_ownership_halo"].as_bool().unwrap(),
                    component["area"].as_u64().unwrap() as usize,
                    component["mass"].as_f64().unwrap()
                ),
                component["fires"].as_bool().unwrap()
            );
        }
        assert_eq!(got, expected, "{} member {}", c["source"], c["member"]);
    }
}

#[test]
fn source_frame_and_trace_parity() {
    use scanweave_io::{glyph_sharing::source, units::Unit};
    let cases: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/glyph-sharing-source.json")).unwrap();
    for r in cases.as_array().unwrap() {
        let s = &r["source"];
        let unit = Unit {
            shape_key: "source".into(),
            span_id: "source".into(),
            symbol_id: "source".into(),
            semantic_text: r["character"].as_str().unwrap().into(),
            bbox_px: serde_json::from_value(s["bbox"].clone()).unwrap(),
            ocr_bbox_px: serde_json::from_value(s["ocr_bbox"].clone()).unwrap(),
            crop_w: s["width"].as_u64().unwrap() as usize,
            crop_h: s["height"].as_u64().unwrap() as usize,
            mask: serde_json::from_value(s["mask"].clone()).unwrap(),
            gray_samples: serde_json::from_value(s["gray"].clone()).unwrap(),
            gray_halo: serde_json::from_value(s["halo"].clone()).unwrap(),
        };
        let line: Vec<(&str, [f64; 4])> = r["line_units"]
            .as_array()
            .unwrap()
            .iter()
            .map(|u| {
                (
                    u["text"].as_str().unwrap(),
                    serde_json::from_value(u["bbox"].clone()).unwrap(),
                )
            })
            .collect();
        let (field, _) = source::frame(
            &unit,
            serde_json::from_value(r["paper"].clone()).unwrap(),
            &line,
        )
        .unwrap();
        let mut expected = vec![0.; 4096];
        for pair in r["field"].as_array().unwrap() {
            expected[pair[0].as_u64().unwrap() as usize] = pair[1].as_f64().unwrap();
        }
        let delta = field
            .iter()
            .zip(&expected)
            .map(|(a, b)| (a - b).abs())
            .fold(0., f64::max);
        assert!(delta < 1e-12, "frame member {} delta {delta}", r["index"]);
        let canonical = source::trace(
            r["index"].as_u64().unwrap() as usize,
            r["character"].as_str().unwrap(),
            &field,
        )
        .unwrap();
        assert_eq!(
            canonical.shape.path.to_svg(),
            r["outline"]["path"].as_str().unwrap(),
            "trace member {}",
            r["index"]
        );
    }
}

#[test]
fn composite_metrics_and_quantization() {
    use scanweave_io::{
        fontbuild,
        glyph_sharing::{
            font::{build, Instance},
            source,
        },
    };
    use std::collections::{BTreeMap, BTreeSet};
    use write_fonts::{
        read::{
            tables::glyf::{Anchor, Glyph},
            FontRef, TableProvider,
        },
        types::GlyphId,
    };
    let mut field = vec![0.; 4096];
    for y in 20..48 {
        for x in 25..38 {
            field[y * 64 + x] = 1.;
        }
    }
    let canonical = source::trace(0, "a", &field).unwrap();
    let shapes = vec![canonical.shape.clone(); 3];
    let encodings = vec![(0, "a".into()), (1, "a".into()), (2, "a".into())];
    let original = fontbuild::build_font(&shapes, &encodings, 2048).unwrap();
    let canonicals = BTreeMap::from([(0, canonical.shape)]);
    let instance = Instance {
        canonical: 0,
        original_gid: 1,
        transform: [1., 0., 0., 1., 2.5, -3.5],
    };
    let shared = build(
        &original,
        &BTreeSet::new(),
        &canonicals,
        &[instance.clone(), instance],
        &encodings,
    )
    .unwrap();
    assert_eq!(shared.instance_gids[0], shared.instance_gids[1]);
    assert_eq!(shared.retired, 3);
    assert_eq!(shared.canonical_gids.len(), 1);
    let base = FontRef::new(&original).unwrap();
    let font = FontRef::new(&shared.bytes).unwrap();
    let gid = GlyphId::new(shared.instance_gids[0] as u32);
    assert_eq!(
        base.hmtx().unwrap().advance(GlyphId::new(1)),
        font.hmtx().unwrap().advance(gid)
    );
    let loca = font.loca(None).unwrap();
    let glyf = font.glyf().unwrap();
    let Glyph::Composite(stub) = loca.get_glyf(gid, &glyf).unwrap().unwrap() else {
        panic!("expected composite")
    };
    let c = stub.components().next().unwrap();
    assert_eq!(c.anchor, Anchor::Offset { x: 2, y: -4 });
    assert!(c.flags.bits() & 4 != 0);
    assert!(c.flags.bits() & 0x1000 != 0);
    if let Some(path) = std::env::var_os("FONT04_TEST_FONT_OUT") {
        std::fs::write(path, shared.bytes).unwrap();
    }
}
