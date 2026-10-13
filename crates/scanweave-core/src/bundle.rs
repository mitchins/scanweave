//! Document bundle manifest v1.0 — types mirroring schemas/bundle.schema.json plus
//! pairing verification (every referenced OCR page file must hash-match and belong
//! to the declared page; asset paths must be root-contained).

use crate::error::ScanWeaveError;
use crate::ocr_page::OcrPage;
use crate::{hash_hex, is_sha256_hex, is_valid_id, Limits};
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Bundle {
    pub schema_version: crate::ocr_page::SchemaVersion,
    pub document_id: String,
    pub sources: Vec<BundleSource>,
    pub pages: Vec<BundlePage>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BundleSource {
    pub source_id: String,
    pub asset_path: String,
    pub file_sha256: String,
    pub kind: BundleSourceKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
pub enum BundleSourceKind {
    #[serde(rename = "image")]
    Image,
    #[serde(rename = "pdf")]
    Pdf,
    #[serde(rename = "multipage_tiff")]
    MultipageTiff,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BundlePage {
    pub page_id: String,
    pub source_id: String,
    pub source_page_index: u32,
    pub ocr_page_path: String,
    pub ocr_page_sha256: String,
}

fn path_check(p: &str) -> Result<(), ScanWeaveError> {
    if !crate::ocr_page::path_is_contained(p) {
        return Err(ScanWeaveError::InvalidInput {
            context: format!("bundle path escapes bundle root or is invalid: {p:?}"),
        });
    }
    Ok(())
}

impl Bundle {
    pub fn parse_bytes(input: &[u8]) -> Result<Bundle, ScanWeaveError> {
        crate::json_util::assert_no_duplicate_keys(input)?;
        let b: Bundle = serde_json::from_slice(input).map_err(|e| ScanWeaveError::InvalidInput {
            context: format!("schema violation: {e}"),
        })?;
        b.check_ids()?;
        Ok(b)
    }

    fn check_ids(&self) -> Result<(), ScanWeaveError> {
        if !is_valid_id(&self.document_id) {
            return Err(ScanWeaveError::InvalidInput {
                context: "invalid document_id".into(),
            });
        }
        let mut src = std::collections::HashSet::new();
        for s in &self.sources {
            if !is_valid_id(&s.source_id) || !src.insert(s.source_id.as_str()) {
                return Err(ScanWeaveError::InvalidInput {
                    context: format!("invalid or duplicate source_id {:?}", s.source_id),
                });
            }
            if !is_sha256_hex(&s.file_sha256) {
                return Err(ScanWeaveError::InvalidInput {
                    context: format!("source {}: malformed file_sha256", s.source_id),
                });
            }
            path_check(&s.asset_path)?;
        }
        let mut pg = std::collections::HashSet::new();
        for p in &self.pages {
            if !is_valid_id(&p.page_id) || !pg.insert(p.page_id.as_str()) {
                return Err(ScanWeaveError::InvalidInput {
                    context: format!("invalid or duplicate page_id {:?}", p.page_id),
                });
            }
            if !is_sha256_hex(&p.ocr_page_sha256) {
                return Err(ScanWeaveError::InvalidInput {
                    context: format!("page {}: malformed ocr_page_sha256", p.page_id),
                });
            }
            path_check(&p.ocr_page_path)?;
            if !src.contains(p.source_id.as_str()) {
                return Err(ScanWeaveError::InvalidInput {
                    context: format!("page {}: unknown source_id {}", p.page_id, p.source_id),
                });
            }
        }
        Ok(())
    }

    /// Path-only containment validation (no filesystem access performed).
    pub fn check_paths(&self, _limits: &Limits) -> Result<(), ScanWeaveError> {
        self.check_ids()
    }

    /// Verify every referenced OCR page file exists, hashes to ocr_page_sha256, parses,
    /// declares the same page_id, and that each source asset hashes to file_sha256.
    /// `root` is the bundle root directory.
    pub fn verify_pairing(&self, root: &std::path::Path, limits: &Limits) -> Result<(), ScanWeaveError> {
        self.check_ids()?;
        // source assets
        for s in &self.sources {
            let asset = root.join(&s.asset_path);
            let bytes = std::fs::read(&asset).map_err(|e| ScanWeaveError::BindingMismatch {
                context: format!("source asset {}: {}", s.asset_path, e),
            })?;
            let got = hash_hex(&bytes);
            if got != s.file_sha256 {
                return Err(ScanWeaveError::BindingMismatch {
                    context: format!(
                        "source {}: file hash mismatch (declared {}, actual {got})",
                        s.source_id, s.file_sha256
                    ),
                });
            }
        }
        // OCR pages
        for p in &self.pages {
            let ocr_file = root.join(&p.ocr_page_path);
            let bytes = std::fs::read(&ocr_file).map_err(|e| ScanWeaveError::BindingMismatch {
                context: format!("page {}: missing OCR file {}: {}", p.page_id, p.ocr_page_path, e),
            })?;
            if bytes.len() > limits.max_ocr_page_bytes {
                return Err(ScanWeaveError::ResourceLimit {
                    limit: "max_ocr_page_bytes".into(),
                    context: format!("page {}", p.page_id),
                });
            }
            let got = hash_hex(&bytes);
            if got != p.ocr_page_sha256 {
                return Err(ScanWeaveError::BindingMismatch {
                    context: format!(
                        "page {}: OCR pairing mismatch — recorded sha256 {} but file hashes to {got}; wrong page pairing or stale OCR",
                        p.page_id, p.ocr_page_sha256
                    ),
                });
            }
            let parsed = OcrPage::parse_bytes(&bytes)?;
            if parsed.page_id != p.page_id {
                return Err(ScanWeaveError::BindingMismatch {
                    context: format!(
                        "page {}: OCR file declares page_id {} but bundle expects {}",
                        p.page_id, parsed.page_id, p.page_id
                    ),
                });
            }
            let source = self
                .sources
                .iter()
                .find(|s| s.source_id == p.source_id)
                .ok_or_else(|| ScanWeaveError::InvalidInput {
                    context: format!("page {}: unknown source {}", p.page_id, p.source_id),
                })?;
            if parsed.raster.asset_path == source.asset_path
                && parsed.raster.file_sha256 != source.file_sha256
            {
                return Err(ScanWeaveError::BindingMismatch {
                    context: format!(
                        "page {}: normalized page raster hash does not match bundle source record",
                        p.page_id
                    ),
                });
            }
            parsed.validate(limits)?;
        }
        Ok(())
    }
}
