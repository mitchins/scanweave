//! FONT-04 discovery adapter. No call is made by the default converter.
use crate::{document::DocumentPage, glyphs::GlyphShape, trace, units::Unit};
use serde_json::{json, Value};

fn unit(item: &Value) -> Result<Unit, String> {
    let width = item["width"].as_u64().ok_or("missing width")? as usize;
    let height = item["height"].as_u64().ok_or("missing height")? as usize;
    if width == 0 || height == 0 || width > 4096 || height > 4096 || width * height > 1_048_576 {
        return Err("research crop exceeds bounds".into());
    }
    let cov: Vec<f64> =
        serde_json::from_value(item["coverage"].clone()).map_err(|e| e.to_string())?;
    if cov.len() != width * height
        || cov
            .iter()
            .any(|v| !v.is_finite() || !(0.0..=1.0).contains(v))
    {
        return Err("invalid research coverage".into());
    }
    let mask = if item["mask"].is_array() {
        serde_json::from_value(item["mask"].clone()).map_err(|e| e.to_string())?
    } else {
        cov.iter().map(|v| *v > 0.5).collect::<Vec<bool>>()
    };
    if mask.len() != cov.len() {
        return Err("invalid research mask".into());
    }
    let gray = if item["gray"].is_array() {
        serde_json::from_value(item["gray"].clone()).map_err(|e| e.to_string())?
    } else {
        cov.iter()
            .map(|v| ((1.0 - v) * 255.0).round() as u8)
            .collect::<Vec<u8>>()
    };
    if gray.len() != cov.len() {
        return Err("invalid research gray".into());
    }
    let key = item["key"]
        .as_str()
        .ok_or("missing research key")?
        .to_owned();
    Ok(Unit {
        shape_key: key.clone(),
        span_id: key.clone(),
        symbol_id: key,
        semantic_text: item["character"]
            .as_str()
            .ok_or("missing character")?
            .into(),
        bbox_px: [0., 0., width as f64, height as f64],
        ocr_bbox_px: [0., 0., width as f64, height as f64],
        crop_w: width,
        crop_h: height,
        mask,
        gray_samples: Some(gray),
        gray_halo: None,
    })
}

pub fn trace_batch(request: &Value) -> Result<(Value, Vec<GlyphShape>, Vec<u8>), String> {
    let budget = trace::Budget::from_m0_policy();
    let mut shapes = Vec::new();
    let mut records = Vec::new();
    let mut enc = Vec::new();
    for item in request["items"].as_array().ok_or("missing trace items")? {
        let u = unit(item)?;
        let cov: Vec<f64> =
            serde_json::from_value(item["coverage"].clone()).map_err(|e| e.to_string())?;
        let floor = item["floor"]
            .as_bool()
            .unwrap_or(false)
            .then_some((&u, 0.98));
        let target = item["local"]
            .as_bool()
            .unwrap_or(false)
            .then_some(cov.as_slice());
        let cap = if item["raised_cap"].as_bool().unwrap_or(false) {
            1_048_576
        } else {
            16_384
        };
        let traced =
            trace::trace_shape_clearscan_with_options(&u, &budget, 16., floor, target, cap);
        match traced.and_then(|mut t| {
            t.preserve_crop_frame = item["preserve_frame"].as_bool().unwrap_or(true);
            crate::glyphs::build_glyph_shapes(&[t], 16., &budget)
        }) {
            Ok(mut result) => {
                let shape = result.remove(0);
                let coverage =
                    crate::convert::reconstructed_glyph_coverage(&shape, u.crop_w, u.crop_h);
                records.push(json!({"key":u.shape_key,"character":u.semantic_text,"gid":shapes.len()+1,
                    "width":u.crop_w,"height":u.crop_h,"coverage":coverage,"points":shape.num_points,
                    "path":shape.path.to_svg(),"anchor":shape.anchor_bbox_fu,"span":shape.ink_span_fu}));
                enc.push((shapes.len(), u.semantic_text));
                shapes.push(shape);
            }
            Err(error) => records.push(json!({"key":u.shape_key,"error":error})),
        }
    }
    let font = crate::fontbuild::build_font_with_bounds(
        &shapes,
        &enc,
        2048,
        Some([-100, -100, 32760, 32760]),
    )?;
    Ok((json!({"records":records}), shapes, font))
}

/// Snapshot only source observations and emitted glyphs, never oracle metadata.
pub fn snapshot(pages: &[DocumentPage], donors: &[Vec<Unit>]) -> Value {
    let scope = std::env::var("FONT04_SCOPE").unwrap_or_else(|_| "B1".into());
    let mut frequencies = std::collections::BTreeMap::<String, usize>::new();
    for page in pages {
        for o in &page.parts.occurrences {
            *frequencies.entry(o.5.clone()).or_default() += 1;
        }
    }
    let mut rows = Vec::new();
    for (pi, page) in pages.iter().enumerate() {
        let p = &page.parts;
        for (oi, o) in p.occurrences.iter().enumerate().filter(|(_, o)| {
            if scope == "B2" {
                frequencies[&o.5] >= 10
            } else {
                o.5 == "e"
            }
        }) {
            let source = donors[pi]
                .iter()
                .find(|u| u.symbol_id == o.4 && u.semantic_text == o.5)
                .cloned()
                .map(|mut u| {
                    u.retain_grayscale(&p.source_rgb, p.source_w as u32, p.source_h as u32);
                    u
                });
            let line = p.lines.iter().find(|line| line.spans.contains(&o.3));
            let line_units: Vec<Value> = donors[pi]
                .iter()
                .filter(|u| line.is_some_and(|l| l.spans.contains(&u.span_id)))
                .map(|u| json!({"text":u.semantic_text,"bbox":u.bbox_px}))
                .collect();
            let g = &p.shapes[o.0];
            let source=source.map(|u|json!({"bbox":u.bbox_px,"ocr_bbox":u.ocr_bbox_px,
                "width":u.crop_w,"height":u.crop_h,"mask":u.mask,"gray":u.gray_samples,"halo":u.gray_halo}));
            rows.push(
                json!({"index":rows.len(),"page":pi,"occurrence":oi,"id":o.4,"span_id":o.3,
                "character":o.5,"bbox":o.2,"shape_key":g.shape_key,"path":g.path.to_svg(),
                "anchor":g.anchor_bbox_fu,"ink_span":g.ink_span_fu,"points":g.num_points,
                "dpi":p.dpi,"page_width":p.page_w_pt,"page_height":p.page_h_pt,
                "source":source,"paper":p.paper,"line_units":line_units}),
            );
        }
    }
    json!({"schema":"font04-source-snapshot-v1","rows":rows})
}

pub fn apply(
    pages: &mut [DocumentPage],
    plan: &Value,
    shapes: &[GlyphShape],
) -> Result<(), String> {
    for row in plan["assignments"]
        .as_array()
        .ok_or("missing assignments")?
    {
        let pi = row["page"].as_u64().ok_or("missing page")? as usize;
        let oi = row["occurrence"].as_u64().ok_or("missing occurrence")? as usize;
        let si = row["shape"].as_u64().ok_or("missing canonical")? as usize;
        let shape = shapes.get(si).ok_or("canonical out of bounds")?;
        let p = &mut pages.get_mut(pi).ok_or("page out of bounds")?.parts;
        let o = p.occurrences.get(oi).ok_or("occurrence out of bounds")?;
        if row["character"].as_str().unwrap_or("e") != o.5
            || row["id"].as_str() != Some(o.4.as_str())
        {
            return Err("label/identity mismatch".into());
        }
        let bbox: [f64; 4] =
            serde_json::from_value(row["bbox"].clone()).map_err(|e| e.to_string())?;
        if bbox.iter().any(|v| !v.is_finite()) || bbox[2] <= bbox[0] || bbox[3] <= bbox[1] {
            return Err("invalid fitted bbox".into());
        }
        let character = o.5.clone();
        let local_shape = p.shapes.len();
        p.shapes.push(shape.clone());
        let cid = p.encodings.len() as u32;
        p.encodings.push((local_shape, character));
        let o = &mut p.occurrences[oi];
        o.0 = local_shape;
        o.1 = cid;
        o.2 = bbox;
    }
    Ok(())
}
