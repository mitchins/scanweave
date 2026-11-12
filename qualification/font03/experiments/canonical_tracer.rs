use scanweave_io::{glyphs, trace, units};
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let data: serde_json::Value = serde_json::from_slice(&std::fs::read(&a[1]).unwrap()).unwrap();
    let mut shapes = Vec::new();
    let mut records = Vec::new();
    for item in data["templates"].as_array().unwrap() {
        let side = item["size"].as_u64().unwrap() as usize;
        let cov: Vec<f64> = item["coverage"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_f64().unwrap())
            .collect();
        assert_eq!(cov.len(), side * side);
        let ink: Vec<usize> = cov
            .iter()
            .enumerate()
            .filter_map(|(i, v)| if *v > 0.5 { Some(i) } else { None })
            .collect();
        let x0 = ink.iter().map(|i| i % side).min().unwrap();
        let y0 = ink.iter().map(|i| i / side).min().unwrap();
        let x1 = ink.iter().map(|i| i % side).max().unwrap() + 1;
        let y1 = ink.iter().map(|i| i / side).max().unwrap() + 1;
        let (w, h) = (x1 - x0, y1 - y0);
        let coverage: Vec<f64> = (y0..y1)
            .flat_map(|y| (x0..x1).map(move |x| (x, y)))
            .map(|(x, y)| cov[y * side + x])
            .collect();
        let key = item["key"].as_str().unwrap().to_string();
        let u = units::Unit {
            shape_key: key.clone(),
            span_id: key.clone(),
            symbol_id: key.clone(),
            semantic_text: item["character"].as_str().unwrap().to_string(),
            bbox_px: [0., 0., w as f64, h as f64],
            ocr_bbox_px: [0., 0., w as f64, h as f64],
            crop_w: w,
            crop_h: h,
            mask: coverage.iter().map(|v| *v > 0.5).collect(),
            gray_samples: Some(
                coverage
                    .iter()
                    .map(|v| ((1. - v.clamp(0., 1.)) * 255.).round() as u8)
                    .collect(),
            ),
            gray_halo: None,
        };
        match trace::trace_shape_clearscan(&u, &trace::Budget::from_m0_policy(), 16., None)
            .and_then(|mut t| {
                t.preserve_crop_frame = true;
                glyphs::build_glyph_shapes(&[t], 16., &trace::Budget::from_m0_policy())
            }) {
            Ok(mut g) => {
                let shape = g.remove(0);
                records.push(serde_json::json!({"key":key,"character":u.semantic_text,"origin":[x0,y0],"crop":[w,h],"gid":shapes.len()+1,"points":shape.num_points,"contours":shape.num_contours,"path_svg":shape.path.to_svg(),"bbox":shape.anchor_bbox_fu,"ink_span":shape.ink_span_fu}));
                shapes.push(shape);
            }
            Err(e) => {
                records.push(serde_json::json!({"key":key,"error":e}));
            }
        }
    }
    let enc: Vec<_> = shapes
        .iter()
        .enumerate()
        .map(|(i, _)| (i, "e".to_string()))
        .collect();
    let font = scanweave_io::fontbuild::build_font_with_bounds(
        &shapes,
        &enc,
        2048,
        Some([-100, -100, 2300, 2300]),
    )
    .unwrap();
    std::fs::write(format!("{}/templates.ttf", a[2]), font).unwrap();
    std::fs::write(
        format!("{}/template-outlines.json", a[2]),
        serde_json::to_vec_pretty(&records).unwrap(),
    )
    .unwrap();
}
