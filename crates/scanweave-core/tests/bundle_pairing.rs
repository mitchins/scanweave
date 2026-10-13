//! Bundle manifest validation and page pairing (wrong page pairing, path escape).

use scanweave_core::bundle::Bundle;
use scanweave_core::error::ScanWeaveError;
use scanweave_core::Limits;

fn fx(rel: &str) -> Vec<u8> {
    let p = format!(
        "{}/../../qualification/fixtures/{}",
        env!("CARGO_MANIFEST_DIR"),
        rel
    );
    std::fs::read(&p).unwrap_or_else(|e| panic!("fixture {p}: {e}"))
}

fn patched_ocr(ocr_bytes: &[u8], raster_file_sha: &str) -> Vec<u8> {
    // patch the normalized page's raster file hash to match the (pretend) asset bytes
    let mut v: serde_json::Value = serde_json::from_slice(ocr_bytes).unwrap();
    v["raster"]["file_sha256"] = serde_json::json!(raster_file_sha);
    serde_json::to_vec(&v).unwrap()
}

fn setup_bundle_dir(
    tag: &str,
    ocr_rel: &str,
    patched: &[u8],
    raster_file_sha: &str,
) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!("scanweave-m0-{tag}"));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(dir.join("ocr")).unwrap();
    std::fs::create_dir_all(dir.join("pages")).unwrap();
    let ocr_path = dir.join(ocr_rel);
    std::fs::create_dir_all(ocr_path.parent().unwrap()).unwrap();
    std::fs::write(ocr_path, patched).unwrap();
    std::fs::write(dir.join("pages/p000001.png"), b"pretend-png-bytes").unwrap();
    let _ = raster_file_sha;
    dir
}

#[test]
fn valid_bundle_pairs_with_matching_ocr_file() {
    let ocr = fx("positive/valid_page.json");
    let mut bundle: Bundle = Bundle::parse_bytes(&fx("bundle/valid_bundle.json")).unwrap();
    // fix the recorded file hash to the actual asset bytes so only OCR pairing is exercised
    let want = scanweave_core::hash_hex(b"pretend-png-bytes");
    bundle.sources[0].file_sha256 = want.clone();
    let patched = patched_ocr(&ocr, &want);
    let dir = setup_bundle_dir("valid", "ocr/p000001.json", &patched, &want);
    bundle.pages[0].ocr_page_sha256 = scanweave_core::hash_hex(&patched);
    bundle
        .verify_pairing(&dir, &Limits::m0_defaults())
        .expect("matching pairing must pass");
}

#[test]
fn wrong_page_pairing_rejected() {
    let ocr = fx("positive/valid_page.json");
    let mut bundle: Bundle = Bundle::parse_bytes(&fx("bundle/wrong_pairing_bundle.json")).unwrap();
    let want = scanweave_core::hash_hex(b"pretend-png-bytes");
    bundle.sources[0].file_sha256 = want.clone();
    let patched = patched_ocr(&ocr, &want);
    let dir = setup_bundle_dir("wrong", "ocr/p000001.json", &patched, &want);
    // recorded ocr_page_sha256 is "11"*32 but the file hashes to something else
    let e = bundle
        .verify_pairing(&dir, &Limits::m0_defaults())
        .unwrap_err();
    assert!(matches!(e, ScanWeaveError::BindingMismatch { .. }));
}

#[test]
fn path_escape_rejected() {
    // path containment is enforced at parse time (check_ids); the escape fixture must
    // never deserialize into a Bundle at all.
    let e = Bundle::parse_bytes(&fx("bundle/path_escape_bundle.json")).unwrap_err();
    assert!(matches!(e, ScanWeaveError::InvalidInput { .. }));
}
