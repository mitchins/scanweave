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
