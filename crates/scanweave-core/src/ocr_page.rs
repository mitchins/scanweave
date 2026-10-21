//! Normalized OCR page v1.0 — serde types mirroring schemas/ocr-page.schema.json,
//! plus the semantic validator layer (JSON Schema is only the first validation layer).

use crate::error::ScanWeaveError;
use crate::pixel_hash::{CanonicalFormat, ColourTag};
use crate::{is_sha256_hex, is_valid_id, Limits};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum SchemaVersion {
    #[serde(rename = "1.0")]
    V1,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum Granularity {
    #[serde(rename = "symbol")]
    Symbol,
    #[serde(rename = "cluster")]
    Cluster,
    #[serde(rename = "word")]
    Word,
    #[serde(rename = "line")]
    Line,
    #[serde(rename = "mixed")]
    Mixed,
    #[serde(rename = "none")]
    None,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum ReadingOrderStatus {
    #[serde(rename = "supplied")]
    Supplied,
    #[serde(rename = "inferred")]
    Inferred,
    #[serde(rename = "unknown")]
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum Direction {
    #[serde(rename = "ltr")]
    Ltr,
    #[serde(rename = "rtl")]
    Rtl,
    #[serde(rename = "ttb")]
    Ttb,
    #[serde(rename = "unknown")]
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum Role {
    #[serde(rename = "body")]
    Body,
    #[serde(rename = "heading")]
    Heading,
    #[serde(rename = "table_cell")]
    TableCell,
    #[serde(rename = "ruby")]
    Ruby,
    #[serde(rename = "footnote")]
    Footnote,
    #[serde(rename = "marginalia")]
    Marginalia,
    #[serde(rename = "other")]
    Other,
    #[serde(rename = "unknown")]
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum Provenance {
    #[serde(rename = "ocr")]
    Ocr,
    #[serde(rename = "human_correction")]
    HumanCorrection,
    #[serde(rename = "source_generated")]
    SourceGenerated,
    #[serde(rename = "unknown")]
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum OrientationPolicy {
    #[serde(rename = "applied_once")]
    AppliedOnce,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum SourceKind {
    #[serde(rename = "image")]
    Image,
    #[serde(rename = "pdf")]
    Pdf,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum ProtectedOrigin {
    #[serde(rename = "caller")]
    Caller,
    #[serde(rename = "preset")]
    Preset,
    #[serde(rename = "source_generated")]
    SourceGenerated,
}

#[derive(Debug, Clone, Copy, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Confidence {
    pub value: Option<f64>,
    pub scale: ConfidenceScale,
    pub calibrated: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum ConfidenceScale {
    #[serde(rename = "range_0_100")]
    Range0To100,
    #[serde(rename = "probability")]
    Probability,
    #[serde(rename = "logit")]
    Logit,
    #[serde(rename = "engine_specific")]
    EngineSpecific,
    #[serde(rename = "unknown")]
    Unknown,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RasterBinding {
    pub asset_path: String,
    pub file_sha256: String,
    pub pixel_sha256: String,
    pub width_px: u32,
    pub height_px: u32,
    pub canonical_format: CanonicalFormat,
    pub colour_tag: ColourTag,
    pub icc_sha256: Option<String>,
    pub orientation_policy: OrientationPolicy,
    pub decoder_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dpi_x: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dpi_y: Option<f64>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PageGeometry {
    pub width_pt: f64,
    pub height_pt: f64,
    pub raster_to_page_pt: [f64; 6],
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceGeometry {
    pub source_kind: SourceKind,
    pub source_page_index: u32,
    pub media_box: Option<[f64; 4]>,
    pub crop_box: Option<[f64; 4]>,
    pub rotate_degrees: Option<RotateDegrees>,
    pub user_unit: Option<f64>,
    pub raster_to_source_user: Option<[f64; 6]>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub enum RotateDegrees {
    #[serde(rename = "0")]
    D0,
    #[serde(rename = "90")]
    D90,
    #[serde(rename = "180")]
    D180,
    #[serde(rename = "270")]
    D270,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelInfo {
    pub name: String,
    pub sha256: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Producer {
    pub name: String,
    pub version: String,
    pub models: Vec<ModelInfo>,
    pub languages: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Symbol {
    pub id: String,
    pub text_range_utf8: [usize; 2],
    pub polygon: Vec<[f64; 2]>,
    pub confidence: Confidence,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Span {
    pub id: String,
    pub text: String,
    pub separator_after: String,
    pub polygon: Vec<[f64; 2]>,
    pub direction: Direction,
    pub role: Role,
    pub language: Option<String>,
    pub confidence: Confidence,
    pub provenance: Provenance,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub baseline: Option<Vec<[f64; 2]>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_span_id: Option<String>,
    pub symbols: Vec<Symbol>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProtectedRegion {
    pub id: String,
    pub polygon: Vec<[f64; 2]>,
    pub reason: String,
    pub origin: ProtectedOrigin,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct OcrPage {
    pub schema_version: SchemaVersion,
    pub page_id: String,
    pub raster: RasterBinding,
    pub page: PageGeometry,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_geometry: Option<SourceGeometry>,
    pub producer: Producer,
    pub granularity: Granularity,
    pub reading_order_status: ReadingOrderStatus,
    pub reading_order: Vec<String>,
    pub spans: Vec<Span>,
    pub protected_regions: Vec<ProtectedRegion>,
}

impl OcrPage {
    /// Parse a normalized OCR page document: duplicate-key pre-scan, then typed
    /// deserialization with `deny_unknown_fields` at every level. NaN/Infinity and
    /// unknown schema versions are rejected.
    pub fn parse_bytes(input: &[u8]) -> Result<OcrPage, ScanWeaveError> {
        crate::json_util::assert_no_duplicate_keys(input)?;
        serde_json::from_slice::<OcrPage>(input).map_err(|e| ScanWeaveError::InvalidInput {
            context: format!("schema violation: {e}"),
        })
    }

    /// Recompute the canonical pixel hash from the binding's declared format/dimensions/
    /// colour policy and the provided canonical decoded samples (SPEC §4.2).
    pub fn verify_binding(&self, canonical_samples: &[u8]) -> Result<(), ScanWeaveError> {
        let computed = crate::pixel_hash::pixel_hash(
            self.raster.canonical_format,
            self.raster.width_px as u64,
            self.raster.height_px as u64,
            self.raster.colour_tag,
            self.raster.icc_sha256.as_deref(),
            canonical_samples,
        )?;
        if computed != self.raster.pixel_sha256 {
            return Err(ScanWeaveError::BindingMismatch {
                context: format!(
                    "pixel hash mismatch for page {}: declared {}, computed {}",
                    self.page_id, self.raster.pixel_sha256, computed
                ),
            });
        }
        Ok(())
    }

    /// Semantic validation (SPEC §4.3, Appendix A). Schema-level rejection already
    /// happened at parse time; this enforces the cross-field rules JSON Schema cannot.
    pub fn validate(&self, limits: &Limits) -> Result<(), ScanWeaveError> {
        let v = Validator { limits };
        v.run(self)
    }
}

struct Validator<'a> {
    limits: &'a Limits,
}

impl<'a> Validator<'a> {
    fn run(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        self.budgets(page)?;
        self.ids(page)?;
        self.raster(page)?;
        self.geometry(page)?;
        self.producer(page)?;
        self.spans(page)?;
        self.reading_order(page)?;
        self.protected(page)?;
        Ok(())
    }

    fn budgets(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        if page.spans.len() > self.limits.max_spans_per_page {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_spans_per_page".into(),
                context: format!("page {}: {}", page.page_id, page.spans.len()),
            });
        }
        let symbols: usize = page.spans.iter().map(|s| s.symbols.len()).sum();
        if symbols > self.limits.max_symbols_per_page {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_symbols_per_page".into(),
                context: format!("page {}: {symbols}", page.page_id),
            });
        }
        if page.protected_regions.len() > self.limits.max_spans_per_page {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_protected_regions".into(),
                context: format!("page {}: {}", page.page_id, page.protected_regions.len()),
            });
        }
        Ok(())
    }

    fn ids(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        if !is_valid_id(&page.page_id) {
            return Err(self.bad(format!("invalid page_id {:?}", page.page_id)));
        }
        let mut seen = std::collections::HashSet::new();
        for s in &page.spans {
            if !is_valid_id(&s.id) {
                return Err(self.bad(format!("invalid span id {:?}", s.id)));
            }
            if !seen.insert(&s.id) {
                return Err(self.bad(format!("duplicate span id {:?}", s.id)));
            }
            for sym in &s.symbols {
                if !is_valid_id(&sym.id) {
                    return Err(self.bad(format!("invalid symbol id {:?}", sym.id)));
                }
            }
            // symbol ids must be unique page-wide (importer validates unique IDs)
            let mut syms = std::collections::HashSet::new();
            for sym in &s.symbols {
                if !syms.insert(&sym.id) {
                    return Err(self.bad(format!("duplicate symbol id {:?}", sym.id)));
                }
            }
        }
        // symbol ids must also be unique ACROSS spans (page-wide)
        let mut all_syms = std::collections::HashSet::new();
        for s in &page.spans {
            for sym in &s.symbols {
                if !all_syms.insert(&sym.id) {
                    return Err(self.bad(format!("duplicate symbol id {:?}", sym.id)));
                }
            }
        }
        for p in &page.protected_regions {
            if !is_valid_id(&p.id) {
                return Err(self.bad(format!("invalid protected id {:?}", p.id)));
            }
        }
        Ok(())
    }

    fn raster(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        let r = &page.raster;
        if !is_sha256_hex(&r.file_sha256) || !is_sha256_hex(&r.pixel_sha256) {
            return Err(self.bad("raster hashes must be lowercase 64-hex"));
        }
        if r.asset_path.is_empty() || r.asset_path.len() > 4096 || !path_is_contained(&r.asset_path)
        {
            return Err(self.bad(format!("invalid asset_path {:?}", r.asset_path)));
        }
        if r.decoder_id.is_empty() || r.decoder_id.len() > 256 {
            return Err(self.bad("decoder_id must be 1..=256 chars"));
        }
        match r.colour_tag {
            ColourTag::Icc => {
                let icc = r.icc_sha256.as_deref().ok_or_else(|| {
                    self.bad("colour_tag=icc requires icc_sha256 (null is invalid)")
                })?;
                if !is_sha256_hex(icc) {
                    return Err(self.bad("icc_sha256 must be lowercase 64-hex"));
                }
            }
            _ => {
                if r.icc_sha256.is_some() {
                    return Err(self.bad("non-icc colour_tag must have null icc_sha256"));
                }
            }
        }
        if let Some(d) = r.dpi_x {
            if !(d.is_finite() && d > 0.0) {
                return Err(self.bad("dpi_x must be finite > 0"));
            }
        }
        if let Some(d) = r.dpi_y {
            if !(d.is_finite() && d > 0.0) {
                return Err(self.bad("dpi_y must be finite > 0"));
            }
        }
        if (r.width_px as u64) > self.limits.max_page_dimension_px
            || (r.height_px as u64) > self.limits.max_page_dimension_px
        {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_page_dimension_px".into(),
                context: format!("{}x{}", r.width_px, r.height_px),
            });
        }
        let pixels = r.width_px as u64 * r.height_px as u64;
        if pixels > self.limits.max_page_pixels {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_page_pixels".into(),
                context: format!("{pixels}"),
            });
        }
        Ok(())
    }

    fn geometry(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        let g = &page.page;
        if !(g.width_pt.is_finite() && g.width_pt > 0.0) {
            return Err(self.bad(format!("width_pt must be finite > 0, got {}", g.width_pt)));
        }
        if !(g.height_pt.is_finite() && g.height_pt > 0.0) {
            return Err(self.bad(format!("height_pt must be finite > 0, got {}", g.height_pt)));
        }
        let [a, b, c, d, e, f] = g.raster_to_page_pt;
        for v in [a, b, c, d, e, f] {
            if !v.is_finite() {
                return Err(self.bad("raster_to_page_pt must be finite (no NaN/Inf)"));
            }
        }
        let det = a * d - b * c;
        if !det.is_finite() || det.abs() < 1e-12 {
            return Err(ScanWeaveError::UnsupportedGeometry {
                context: format!(
                    "raster_to_page_pt is numerically non-invertible (det={det})"
                ),
            });
        }
        // transformed raster extent must match declared physical extent
        let w = page.raster.width_px as f64;
        let h = page.raster.height_px as f64;
        let corners = [(0.0, 0.0), (w, 0.0), (0.0, h), (w, h)];
        let mut xs = [0.0f64; 4];
        let mut ys = [0.0f64; 4];
        for (i, (x, y)) in corners.iter().enumerate() {
            xs[i] = a * x + c * y + e;
            ys[i] = b * x + d * y + f;
        }
        let (xmin, xmax) = (xs.iter().cloned().fold(f64::INFINITY, f64::min), xs.iter().cloned().fold(f64::NEG_INFINITY, f64::max));
        let (ymin, ymax) = (ys.iter().cloned().fold(f64::INFINITY, f64::min), ys.iter().cloned().fold(f64::NEG_INFINITY, f64::max));
        let tol = 1e-6;
        let w_ok = ((xmax - xmin) - g.width_pt).abs() <= tol * g.width_pt.max(1.0);
        let h_ok = ((ymax - ymin) - g.height_pt).abs() <= tol * g.height_pt.max(1.0);
        if !w_ok || !h_ok {
            return Err(ScanWeaveError::UnsupportedGeometry {
                context: format!(
                    "transformed raster extent ({:.4}x{:.4}pt) does not match declared physical extent ({:.4}x{:.4}pt)",
                    xmax - xmin,
                    ymax - ymin,
                    g.width_pt,
                    g.height_pt
                ),
            });
        }
        Ok(())
    }

    fn producer(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        let p = &page.producer;
        if p.name.is_empty() || p.name.len() > 256 || p.version.len() > 256 {
            return Err(self.bad("producer name/version length violation"));
        }
        if p.models.len() > self.limits.max_models {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_models".into(),
                context: format!("{}", p.models.len()),
            });
        }
        for m in &p.models {
            if m.name.is_empty() || m.name.len() > 256 || !is_sha256_hex(&m.sha256) {
                return Err(self.bad("producer model entry invalid"));
            }
        }
        if p.languages.len() > self.limits.max_producer_languages {
            return Err(ScanWeaveError::ResourceLimit {
                limit: "max_languages".into(),
                context: format!("{}", p.languages.len()),
            });
        }
        for l in &p.languages {
            if l.is_empty() || l.len() > 64 {
                return Err(self.bad("producer language tag length violation"));
            }
        }
        Ok(())
    }

    fn spans(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        let r = &page.raster;
        for span in &page.spans {
            if span.text.len() > self.limits.max_span_utf8_bytes {
                return Err(ScanWeaveError::ResourceLimit {
                    limit: "max_span_utf8_bytes".into(),
                    context: format!("span {}", span.id),
                });
            }
            if !span.separator_after.chars().all(char::is_whitespace) {
                return Err(self.bad(format!(
                    "span {}: separator_after must be whitespace-only",
                    span.id
                )));
            }
            if span.language.as_deref().is_some_and(|l| l.len() > 64) {
                return Err(self.bad(format!("span {}: language tag too long", span.id)));
            }
            self.confidence(&span.confidence, &format!("span {}", span.id))?;
            self.polygon(&span.polygon, r, &format!("span {}", span.id))?;
            if let Some(base) = &span.baseline {
                for pt in base {
                    for v in pt {
                        if !v.is_finite() || v.abs() > 10_000_000.0 {
                            return Err(self.bad(format!("span {}: baseline out of range", span.id)));
                        }
                    }
                }
            }
            self.symbol_ranges(span)?;
            for sym in &span.symbols {
                self.confidence(&sym.confidence, &format!("symbol {}", sym.id))?;
                self.polygon(&sym.polygon, r, &format!("symbol {}", sym.id))?;
            }
        }
        self.span_parents(page)
    }

    fn span_parents(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        // parent references: must exist, not self, no cycles
        let ids: std::collections::HashSet<&str> = page.spans.iter().map(|s| s.id.as_str()).collect();
        for span in &page.spans {
            if let Some(pid) = &span.parent_span_id {
                if !ids.contains(pid.as_str()) {
                    return Err(self.bad(format!(
                        "span {}: parent_span_id {pid} does not exist",
                        span.id
                    )));
                }
                // cycle check by walking parents
                let mut cur = pid.as_str();
                let mut steps = 0;
                while steps <= page.spans.len() {
                    if cur == span.id {
                        return Err(
                            self.bad(format!("span {}: parent reference cycle detected", span.id))
                        );
                    }
                    let parent = page.spans.iter().find(|s| s.id == cur);
                    match parent.and_then(|s| s.parent_span_id.as_deref()) {
                        Some(next) => cur = next,
                        None => break,
                    }
                    steps += 1;
                }
            }
        }
        Ok(())
    }

    fn symbol_ranges(&self, span: &Span) -> Result<(), ScanWeaveError> {
        let text = span.text.as_bytes();
        let mut ranges: Vec<(usize, usize)> = Vec::with_capacity(span.symbols.len());
        for sym in &span.symbols {
            let (start, end) = (sym.text_range_utf8[0], sym.text_range_utf8[1]);
            if start >= end {
                return Err(ScanWeaveError::ValidationFailed {
                    context: format!(
                        "symbol {}: byte range [{start},{end}) is empty or inverted",
                        sym.id
                    ),
                });
            }
            if end > text.len() {
                return Err(self.bad(format!(
                    "symbol {}: byte range [{start},{end}) exceeds text length {}",
                    sym.id,
                    text.len()
                )));
            }
            if !span.text.is_char_boundary(start) || !span.text.is_char_boundary(end) {
                return Err(ScanWeaveError::ValidationFailed {
                    context: format!(
                        "symbol {}: byte range [{start},{end}) splits a Unicode scalar",
                        sym.id
                    ),
                });
            }
            // extended-grapheme integrity: a range must not split a grapheme cluster
            for (gstart, grapheme) in
                unicode_segmentation::UnicodeSegmentation::grapheme_indices(
                    span.text.as_str(),
                    true,
                )
            {
                let gend = gstart + grapheme.len();
                let splits = (gstart < start && start < gend) || (gstart < end && end < gend);
                if splits {
                    return Err(ScanWeaveError::ValidationFailed {
                        context: format!(
                            "symbol {}: byte range [{start},{end}) splits an extended grapheme sequence [{gstart},{gend})",
                            sym.id
                        ),
                    });
                }
            }
            ranges.push((start, end));
        }
        ranges.sort();
        let mut max_end = 0usize;
        for (start, end) in &ranges {
            if *start < max_end {
                return Err(ScanWeaveError::ValidationFailed {
                    context: format!(
                        "span {}: symbol byte ranges overlap illegally at [{start},{end})",
                        span.id
                    ),
                });
            }
            max_end = *end;
        }
        Ok(())
    }

    fn confidence(&self, c: &Confidence, ctx: &str) -> Result<(), ScanWeaveError> {
        match c.scale {
            ConfidenceScale::Unknown => {
                if c.value.is_some() {
                    return Err(self.bad(format!("{ctx}: scale=unknown requires null value")));
                }
            }
            ConfidenceScale::Range0To100 => {
                let v = c.value.ok_or_else(|| {
                    self.bad(format!("{ctx}: range_0_100 requires a numeric value"))
                })?;
                if !v.is_finite() || !(0.0..=100.0).contains(&v) {
                    return Err(self.bad(format!("{ctx}: range_0_100 value {v} out of range")));
                }
            }
            ConfidenceScale::Probability => {
                let v = c
                    .value
                    .ok_or_else(|| self.bad(format!("{ctx}: probability requires a numeric value")))?;
                if !v.is_finite() || !(0.0..=1.0).contains(&v) {
                    return Err(self.bad(format!("{ctx}: probability value {v} out of range")));
                }
            }
            ConfidenceScale::Logit | ConfidenceScale::EngineSpecific => {
                if let Some(v) = c.value {
                    if !v.is_finite() {
                        return Err(self.bad(format!("{ctx}: confidence value must be finite")));
                    }
                }
            }
        }
        Ok(())
    }

    fn polygon(
        &self,
        poly: &[[f64; 2]],
        raster: &RasterBinding,
        ctx: &str,
    ) -> Result<(), ScanWeaveError> {
        if poly.len() < 3 {
            return Err(ScanWeaveError::UnsupportedGeometry {
                context: format!("{ctx}: polygon has {} vertices (minimum 3)", poly.len()),
            });
        }
        if poly.len() > self.limits.max_poly_vertices {
            return Err(ScanWeaveError::UnsupportedGeometry {
                context: format!("{ctx}: polygon has {} vertices", poly.len()),
            });
        }
        let tol = self.limits.boundary_tol_px;
        let max_x = raster.width_px as f64 + tol;
        let max_y = raster.height_px as f64 + tol;
        for [x, y] in poly {
            if !x.is_finite() || !y.is_finite() {
                return Err(self.bad(format!("{ctx}: polygon contains non-finite coordinate")));
            }
            if x.abs() > 10_000_000.0 || y.abs() > 10_000_000.0 {
                return Err(self.bad(format!("{ctx}: polygon coordinate out of range")));
            }
            // Stale crop/rotation detection (IN-03): OCR geometry outside the canonical
            // raster is rejected, never silently shifted or clipped.
            if *x < -tol || *y < -tol || *x > max_x || *y > max_y {
                return Err(ScanWeaveError::UnsupportedGeometry {
                    context: format!(
                        "{ctx}: polygon outside canonical raster bounds ({},{} vs {}x{}) — stale crop/rotation or unsupported mapping",
                        x, y, raster.width_px, raster.height_px
                    ),
                });
            }
        }
        Ok(())
    }

    fn reading_order(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        let span_ids: std::collections::HashSet<&str> =
            page.spans.iter().map(|s| s.id.as_str()).collect();
        let mut seen = std::collections::HashSet::new();
        for id in &page.reading_order {
            if !span_ids.contains(id.as_str()) {
                return Err(self.bad(format!("reading_order references unknown span {id}")));
            }
            if !seen.insert(id.as_str()) {
                return Err(self.bad(format!("reading_order duplicates span {id}")));
            }
        }
        // completeness when an order is claimed
        if page.reading_order_status != ReadingOrderStatus::Unknown
            && seen.len() != span_ids.len()
        {
            return Err(self.bad(format!(
                "reading_order_status={:?} requires a complete, nonduplicated reference set ({} of {} covered)",
                page.reading_order_status, seen.len(), span_ids.len()
            )));
        }
        Ok(())
    }

    fn protected(&self, page: &OcrPage) -> Result<(), ScanWeaveError> {
        for p in &page.protected_regions {
            self.polygon(&p.polygon, &page.raster, &format!("protected {}", p.id))?;
            if p.reason.is_empty() || p.reason.len() > 256 {
                return Err(self.bad(format!("protected {}: reason length violation", p.id)));
            }
        }
        Ok(())
    }

    fn bad(&self, context: impl Into<String>) -> ScanWeaveError {
        ScanWeaveError::InvalidInput {
            context: context.into(),
        }
    }
}

/// Root-contained relative path check (SPEC Appendix A: no traversal, no URI scheme).
pub fn path_is_contained(p: &str) -> bool {
    if p.is_empty() || p.len() > 4096 {
        return false;
    }
    if p.starts_with('/') || p.starts_with('\\') {
        return false;
    }
    if p.contains("://") || p.contains('\\') {
        return false;
    }
    let components = p.split('/');
    for c in components {
        if c == ".." {
            return false;
        }
    }
    true
}
