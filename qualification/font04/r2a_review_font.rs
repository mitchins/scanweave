//! Research-only counterfactual font emitter using the frozen product serializer.
use scanweave_io::{glyph_sharing::font::{build, Instance}, glyphs::GlyphShape, units::StageMetrics};
use std::{collections::{BTreeMap, BTreeSet}, fs};
fn main() {
    let args: Vec<_> = std::env::args().collect();
    let request: serde_json::Value = serde_json::from_slice(&fs::read(&args[1]).unwrap()).unwrap();
    let default = fs::read(request["default_font"].as_str().unwrap()).unwrap();
    let mut canonicals = BTreeMap::new();
    for row in request["canonicals"].as_array().unwrap() {
        let path = kurbo::BezPath::from_svg(row["path"].as_str().unwrap()).unwrap();
        let points = path.elements().len()*3;
        let contours = path.elements().iter().filter(|e| matches!(e,kurbo::PathEl::ClosePath)).count();
        canonicals.insert(row["member"].as_u64().unwrap() as usize, GlyphShape {
            shape_key: "review-only".into(), path, num_contours: contours, num_points: points,
            bbox_fu: [0.;4], ink_span_fu: serde_json::from_value(row["ink_span"].clone()).unwrap(),
            anchor_bbox_fu: serde_json::from_value(row["anchor"].clone()).unwrap(),
            stages: StageMetrics {trace_max_px:0.,trace_p95_px:0.,curve_max_px:0.,quant_bound_px:0.}
        });
    }
    let instances:Vec<_>=request["instances"].as_array().unwrap().iter().map(|r|Instance{
        canonical:r["canonical"].as_u64().unwrap() as usize,
        original_gid:r["original_gid"].as_u64().unwrap() as u16,
        transform:serde_json::from_value(r["transform"].clone()).unwrap()
    }).collect();
    let shared=build(&default,&BTreeSet::new(),&canonicals,&instances,&[]).unwrap();
    fs::write(&args[2],shared.bytes).unwrap();
    fs::write(&args[3],serde_json::to_vec(&shared.instance_gids).unwrap()).unwrap();
}
