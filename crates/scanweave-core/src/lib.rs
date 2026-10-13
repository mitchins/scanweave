//! scanweave-core: validated geometry/types, hashing, policy limits, planning interfaces.
//! Owns NO filesystem, network or process access (SPEC §2).

pub mod bundle;
pub mod error;
pub mod json_util;
pub mod ocr_page;
pub mod pixel_hash;

pub use error::ScanWeaveError;

/// Policy limits for M0, mirroring defaults.toml [execution] and schema bounds.
/// These are limits/design targets, not measured throughput claims (SPEC §9).
#[derive(Debug, Clone)]
pub struct Limits {
    pub max_spans_per_page: usize,
    pub max_symbols_per_page: usize,
    pub max_span_utf8_bytes: usize,
    pub max_page_pixels: u64,
    pub max_page_dimension_px: u64,
    pub max_poly_vertices: usize,
    pub max_ocr_page_bytes: usize,
    pub max_producer_languages: usize,
    pub max_models: usize,
    /// Documented boundary tolerance in pixels for polygon containment (defaults.toml context_padding_px)
    pub boundary_tol_px: f64,
}

impl Limits {
    pub fn m0_defaults() -> Self {
        Limits {
            max_spans_per_page: 100_000,
            max_symbols_per_page: 500_000,
            max_span_utf8_bytes: 16_384,
            max_page_pixels: 80_000_000,
            max_page_dimension_px: 100_000,
            max_poly_vertices: 128,
            max_ocr_page_bytes: 16_777_216,
            max_producer_languages: 256,
            max_models: 256,
            boundary_tol_px: 2.0,
        }
    }
}

/// Lowercase hex of the SHA-256 of `bytes` (used for file_sha256 / ocr_page_sha256).
pub fn hash_hex(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(bytes);
    let out = h.finalize();
    let mut s = String::with_capacity(64);
    for b in out {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

/// ID pattern shared by page_id, span/symbol/protected ids, source ids:
/// `^[A-Za-z][A-Za-z0-9_.:-]{0,127}$`
pub fn is_valid_id(s: &str) -> bool {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) if c.is_ascii_alphabetic() => {}
        _ => return false,
    }
    let count = s.chars().count();
    if count == 0 || count > 128 {
        return false;
    }
    s.chars()
        .skip(1)
        .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | ':' | '-'))
}

/// `^[0-9a-f]{64}$`
pub fn is_sha256_hex(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
