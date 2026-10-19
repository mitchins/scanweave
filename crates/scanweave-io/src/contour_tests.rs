use super::*;
fn rect(x0: f64, y0: f64, x1: f64, y1: f64) -> Vec<[f64; 2]> {
    let p = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]];
    let mut out = vec![p[0]];
    for w in p.windows(2) {
        out.push([
            w[0][0] + (w[1][0] - w[0][0]) / 3.0,
            w[0][1] + (w[1][1] - w[0][1]) / 3.0,
        ]);
        out.push([
            w[0][0] + 2.0 * (w[1][0] - w[0][0]) / 3.0,
            w[0][1] + 2.0 * (w[1][1] - w[0][1]) / 3.0,
        ]);
        out.push(w[1]);
    }
    out
}
fn ring() -> TracedShape {
    TracedShape {
        shape_key: "ring".into(),
        crop_w_px: 12,
        crop_h_px: 12,
        preserve_crop_frame: false,
        compact_curves: false,
        contour_fit: None,
        polylines: Vec::new(),
        layers: vec![(rect(1., 1., 11., 11.), vec![rect(4., 4., 8., 8.)])],
        stage: StageRaw {
            trace_max_px: 0.,
            trace_p95_px: 0.,
        },
    }
}
fn area(c: &[[f64; 2]]) -> f64 {
    sample_spline(c, 8)
        .windows(2)
        .map(|w| w[0][0] * w[1][1] - w[1][0] * w[0][1])
        .sum::<f64>()
        .abs()
        * 0.5
}
#[test]
fn zero_offset_preserves_existing_pdf_frame_without_rescaling() {
    let t = ring();
    let b = Budget::from_m0_policy();
    let k = 70.;
    let a = crate::glyphs::build_glyph_shapes(&[t.clone()], k, &b)
        .unwrap()
        .remove(0);
    let z = crate::glyphs::build_glyph_shapes(&[offset_coverage_contour(&t, 0.)], k, &b)
        .unwrap()
        .remove(0);
    let ca = crate::convert::reconstructed_glyph_coverage(&a, 12, 12);
    let cz = crate::convert::reconstructed_glyph_coverage(&z, 12, 12);
    assert!(ca.iter().zip(cz).all(|(a, b)| (a - b).abs() < 1e-8));
    assert_eq!(a.ink_span_fu, z.ink_span_fu);
}
#[test]
fn inset_reduces_ink_and_expands_the_counter() {
    let a = ring();
    let b = offset_coverage_contour(&a, 0.15);
    assert!(area(&b.layers[0].0) < area(&a.layers[0].0));
    assert!(area(&b.layers[0].1[0]) > area(&a.layers[0].1[0]));
    assert!(crate::contour_topology::valid(&b.layers));
}
#[test]
fn topology_rejects_hole_outside_its_parent() {
    let mut t = ring();
    t.layers[0].1[0] = rect(15., 15., 18., 18.);
    assert!(!crate::contour_topology::valid(&t.layers));
}
#[test]
fn topology_keeps_disconnected_punctuation_components() {
    let mut t = ring();
    t.layers.push((rect(15., 1., 16., 3.), vec![]));
    assert!(crate::contour_topology::valid(&t.layers));
}
#[test]
fn topology_rejects_crossed_counters() {
    let mut t = ring();
    t.layers[0].1.push(rect(7., 5., 10., 9.));
    assert!(!crate::contour_topology::valid(&t.layers));
}
#[test]
fn faithful_trace_does_not_consume_grayscale_refinements() {
    let mut u = crate::units::Unit {
        shape_key: "box".into(),
        span_id: "s".into(),
        symbol_id: "s".into(),
        semantic_text: "a".into(),
        bbox_px: [0., 0., 4., 4.],
        ocr_bbox_px: [0., 0., 4., 4.],
        crop_w: 4,
        crop_h: 4,
        mask: vec![true; 16],
        gray_samples: None,
        gray_halo: None,
    };
    let b = Budget::from_m0_policy();
    let a = trace_shape(&u, &b, 64.).unwrap();
    u.gray_samples = Some(vec![255; 16]);
    let z = trace_shape(&u, &b, 64.).unwrap();
    assert_eq!(a.layers, z.layers);
    assert!(!z.preserve_crop_frame);
    assert!(z.contour_fit.is_none());
}

#[test]
fn grayscale_fit_never_uses_the_ocr_label() {
    let mut u = crate::units::Unit {
        shape_key: "coverage".into(),
        span_id: "s".into(),
        symbol_id: "s".into(),
        semantic_text: "e".into(),
        bbox_px: [0., 0., 6., 8.],
        ocr_bbox_px: [0., 0., 6., 8.],
        crop_w: 6,
        crop_h: 8,
        mask: vec![false; 48],
        gray_samples: Some(vec![254; 48]),
        gray_halo: None,
    };
    for y in 1..7 {
        for x in 1..5 {
            u.mask[y * 6 + x] = true;
            u.gray_samples.as_mut().unwrap()[y * 6 + x] = if x == 1 || x == 4 { 120 } else { 20 };
        }
    }
    let b = Budget::from_m0_policy();
    let a = trace_shape_clearscan(&u, &b, 64., None).unwrap();
    u.semantic_text = "8".into();
    let z = trace_shape_clearscan(&u, &b, 64., None).unwrap();
    assert_eq!(a.layers, z.layers);
    if let Some(fit) = a.contour_fit {
        assert!(fit.selected_gray_mse <= fit.baseline_gray_mse);
    }
}

#[test]
fn local_fit_preserves_the_existing_source_gate() {
    let mut u = crate::units::Unit {
        shape_key: "local".into(),
        span_id: "s".into(),
        symbol_id: "s".into(),
        semantic_text: "e".into(),
        bbox_px: [0., 0., 8., 10.],
        ocr_bbox_px: [0., 0., 8., 10.],
        crop_w: 8,
        crop_h: 10,
        mask: vec![false; 80],
        gray_samples: Some(vec![254; 80]),
        gray_halo: None,
    };
    for y in 1..9 {
        for x in 1..7 {
            u.mask[y * 8 + x] = true;
            u.gray_samples.as_mut().unwrap()[y * 8 + x] = if x == 1 || x == 6 { 180 } else { 20 };
        }
    }
    let b = Budget::from_m0_policy();
    let base = trace_shape(&u, &b, 64.).unwrap();
    let fit = trace_shape_clearscan(&u, &b, 64., Some((&u, 0.98))).unwrap();
    let glyph = |t| {
        crate::glyphs::build_glyph_shapes(&[t], 64., &b)
            .unwrap()
            .remove(0)
    };
    let iou = |g| crate::convert::reconstructed_glyph_ink_iou(&g, 8, 10, &u.mask);
    assert!(iou(glyph(fit)) + 1e-12 >= iou(glyph(base)).min(0.98));
}

#[test]
fn invisible_owner_frame_is_independent_of_reconstructed_contours() {
    let owner = crate::glyphs::semantic_owner_shape(2048.);
    assert_eq!(owner.shape_key, "__semantic_owner_frame");
    assert_eq!(owner.bbox_fu, [0., 0., 1022., 2048.]);
    assert_eq!(owner.ink_span_fu, [1022., 2048.]);
    // Source glyph transformations must never be used to place this label.
    let mutated = offset_coverage_contour(&ring(), 0.15);
    let b = Budget::from_m0_policy();
    let observed = crate::glyphs::build_glyph_shapes(&[mutated], 64., &b).unwrap();
    assert_ne!(observed[0].bbox_fu, owner.bbox_fu);
    assert_eq!(crate::glyphs::semantic_owner_shape(2048.).path, owner.path);
}

#[test]
fn compact_font_frame_preserves_coverage_and_matches_serialized_bounds() {
    let mut t = ring();
    t.preserve_crop_frame = true;
    let budget = Budget::from_m0_policy();
    let original = crate::glyphs::build_glyph_shapes(&[t.clone()], 64., &budget)
        .unwrap()
        .pop()
        .unwrap();
    t.compact_curves = true;
    let compact = crate::glyphs::build_glyph_shapes(&[t], 64., &budget)
        .unwrap()
        .pop()
        .unwrap();
    assert_eq!(compact.anchor_bbox_fu[0], 0.);
    assert_eq!(
        crate::convert::reconstructed_glyph_coverage(&original, 12, 12),
        crate::convert::reconstructed_glyph_coverage(&compact, 12, 12)
    );
    let b = write_fonts::tables::glyf::SimpleGlyph::from_bezpath(&compact.path)
        .unwrap()
        .bbox;
    assert_eq!(
        compact.bbox_fu,
        [
            b.x_min as f64,
            b.y_min as f64,
            b.x_max as f64,
            b.y_max as f64
        ]
    );
}

#[test]
fn semantic_owner_tracks_the_font_construction_scale() {
    let full = crate::glyphs::semantic_owner_shape(2048.);
    let compact = crate::glyphs::semantic_owner_shape(1024.);
    assert_eq!(full.bbox_fu, [0., 0., 1022., 2048.]);
    assert_eq!(compact.bbox_fu, [0., 0., 510., 1024.]);
    assert_eq!((full.ink_span_fu[0] + 2.) / 2., compact.ink_span_fu[0] + 2.);
    assert_eq!(full.shape_key, compact.shape_key);
}
