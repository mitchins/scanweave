use scanweave_io::glyph_sharing::{fit::register, hard_checks, mse};
use std::{
    fs,
    io::{self, Read},
};
fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    let req: serde_json::Value = serde_json::from_str(&input).unwrap();
    let load = |name: &str| {
        fs::read(req[name].as_str().unwrap())
            .unwrap()
            .chunks_exact(8)
            .map(|b| f64::from_le_bytes(b.try_into().unwrap()))
            .collect::<Vec<_>>()
    };
    let fields = load("fields");
    let candidates = load("candidates");
    if req["plan"].as_bool() == Some(true) {
        let rows: Vec<scanweave_io::glyph_sharing::group::Member> = req["rows"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| scanweave_io::glyph_sharing::group::Member {
                label: r["character"].as_str().unwrap().into(),
                shape_key: r["shape_key"].as_str().unwrap().into(),
                band: 0,
            })
            .collect();
        let a: Vec<_> = fields.chunks_exact(4096).map(|f| f.to_vec()).collect();
        let b: Vec<_> = candidates
            .chunks_exact(4096)
            .map(|f| {
                if f.iter().any(|&v| v != 0.) {
                    Some(f.to_vec())
                } else {
                    None
                }
            })
            .collect();
        let plan = scanweave_io::glyph_sharing::plan::plan(&rows, &a, &b, 2.).unwrap();
        println!(
            "{}",
            serde_json::json!({"fits":plan.fits,"groups":plan.groups.iter().map(|g|serde_json::json!({"canonical":g.canonical,"members":g.members})).collect::<Vec<_>>(),"floors":plan.floors,"bands":plan.bands,"hygiene":plan.hygiene})
        );
        return;
    }
    if let Some(cases) = req["source_cases"].as_array() {
        let mut result = Vec::new();
        for r in cases {
            let s = &r["source"];
            let u = scanweave_io::units::Unit {
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
                .map(|v| {
                    (
                        v["text"].as_str().unwrap(),
                        serde_json::from_value(v["bbox"].clone()).unwrap(),
                    )
                })
                .collect();
            let (f, _) = scanweave_io::glyph_sharing::source::frame(
                &u,
                serde_json::from_value(r["paper"].clone()).unwrap(),
                &line,
            )
            .unwrap();
            let c = scanweave_io::glyph_sharing::source::trace(
                r["index"].as_u64().unwrap() as usize,
                r["character"].as_str().unwrap(),
                &f,
            )
            .unwrap();
            result.push(serde_json::json!({"member":r["index"],"field":f,"candidate":c.coverage,"path":c.shape.path.to_svg(),"origin":c.origin,"width":c.width,"height":c.height}));
        }
        println!("{}", serde_json::to_string(&result).unwrap());
        return;
    }
    let mut result = Vec::new();
    for pair in req["pairs"].as_array().unwrap() {
        let i = pair[0].as_u64().unwrap() as usize;
        let j = pair[1].as_u64().unwrap() as usize;
        let a = &fields[i * 4096..(i + 1) * 4096];
        let b = &candidates[j * 4096..(j + 1) * 4096];
        let (p, aligned) = register(a, b);
        result.push(serde_json::json!({"member":i,"canonical":j,"parameters":p,"error":mse(a,&aligned),"reasons":hard_checks(a,&aligned)}));
    }
    println!("{}", serde_json::to_string(&result).unwrap());
}
