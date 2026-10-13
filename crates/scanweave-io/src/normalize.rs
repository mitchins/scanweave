//! Normalized-page builder: hOCR + image metadata (+ binding hashes) -> OcrPage.
//! The builder NEVER invents per-character geometry from word-only input and NEVER
//! guesses physical size (IN-05: absent DPI -> MissingPhysicalGeometry).

use crate::hocr::HocrDocument;
use scanweave_core::error::ScanWeaveError;
use scanweave_core::ocr_page::{
    Confidence, ConfidenceScale, Direction, Granularity, OrientationPolicy, OcrPage,
    Producer, ProtectedRegion, Provenance, ReadingOrderStatus, Role, Span, Symbol,
};
use scanweave_core::pixel_hash::CanonicalFormat;

#[derive(Debug, Clone, Copy)]
pub struct ImageMeta {
    pub width: u32,
    pub height: u32,
}

pub struct Binding {
    pub asset_path: String,
    pub file_sha256: String,
    pub pixel_sha256: String,
}

fn invalid(context: impl Into<String>) -> ScanWeaveError {
    ScanWeaveError::InvalidInput {
        context: context.into(),
    }
}

/// Build the normalized OCR page for one image-bound hOCR document.
/// `dpi` must come from reliable metadata or an explicit override; there is no default.
pub fn build_normalized_page(
    image: &ImageMeta,
    doc: &HocrDocument,
    dpi: Option<f64>,
    binding: &Binding,
) -> Result<OcrPage, ScanWeaveError> {
    let dpi = dpi.ok_or_else(|| ScanWeaveError::MissingPhysicalGeometry {
        context: "no DPI metadata and no explicit override; refusing to guess page size".into(),
    })?;
    if !(dpi.is_finite() && dpi > 0.0) {
        return Err(invalid("DPI override must be finite > 0"));
    }

    // Honest granularity: symbol only when every word has complete per-character coverage.
    let all_have_chars = !doc.words.is_empty()
        && doc.words.iter().all(|w| {
            !w.chars.is_empty()
                && w.chars.iter().map(|c| c.text.as_str()).collect::<String>() == w.text
        });

    let px_per_pt = dpi / 72.0;
    let width_pt = image.width as f64 / px_per_pt;
    let height_pt = image.height as f64 / px_per_pt;

    let mut spans: Vec<Span> = Vec::with_capacity(doc.words.len());
    let mut reading_order: Vec<String> = Vec::with_capacity(doc.words.len());
    for (idx, w) in doc.words.iter().enumerate() {
        let id = format!("w{idx:06}");
        // word polygon in pixel-edge coordinates (hOCR bbox edges are pixel edges)
        let polygon = vec![
            [w.bbox.0 as f64, w.bbox.1 as f64],
            [w.bbox.2 as f64, w.bbox.1 as f64],
            [w.bbox.2 as f64, w.bbox.3 as f64],
            [w.bbox.0 as f64, w.bbox.3 as f64],
        ];
        let symbols = if all_have_chars {
            let mut syms = Vec::with_capacity(w.chars.len());
            let mut byte_off = 0usize;
            for (ci, c) in w.chars.iter().enumerate() {
                let len = c.text.len();
                let end = byte_off + len;
                syms.push(Symbol {
                    id: format!("{id}s{ci:04}"),
                    text_range_utf8: [byte_off, end],
                    polygon: vec![
                        [c.bbox.0 as f64, c.bbox.1 as f64],
                        [c.bbox.2 as f64, c.bbox.1 as f64],
                        [c.bbox.2 as f64, c.bbox.3 as f64],
                        [c.bbox.0 as f64, c.bbox.3 as f64],
                    ],
                    confidence: Confidence {
                        value: c.confidence,
                        scale: ConfidenceScale::Range0To100,
                        calibrated: false,
                    },
                });
                byte_off = end;
            }
            syms
        } else {
            Vec::new()
        };
        // line-end separator when the next word starts a new line (or is the last word)
        let is_line_end = doc
            .words
            .get(idx + 1)
            .is_none_or(|next| next.line_index != w.line_index);
        spans.push(Span {
            id,
            text: w.text.clone(),
            separator_after: if is_line_end { "\n" } else { " " }.to_string(),
            polygon,
            direction: Direction::Ltr,
            role: Role::Body,
            language: None,
            confidence: Confidence {
                value: w.confidence,
                scale: ConfidenceScale::Range0To100,
                calibrated: false,
            },
            provenance: Provenance::Ocr,
            baseline: None,
            parent_span_id: None,
            symbols,
        });
        reading_order.push(format!("w{idx:06}"));
    }

    // stale-geometry guard: any word box beyond the raster is rejected before construction
    for w in &doc.words {
        let tol = 2.0f64;
        if (w.bbox.0 as f64) < -tol
            || (w.bbox.1 as f64) < -tol
            || (w.bbox.2 as f64) > image.width as f64 + tol
            || (w.bbox.3 as f64) > image.height as f64 + tol
        {
            return Err(ScanWeaveError::UnsupportedGeometry {
                context: format!(
                    "hOCR word bbox {:?} outside canonical raster {}x{} — stale crop/rotation mapping",
                    w.bbox, image.width, image.height
                ),
            });
        }
    }

    Ok(OcrPage {
        schema_version: scanweave_core::ocr_page::SchemaVersion::V1,
        page_id: "p000001".to_string(),
        raster: scanweave_core::ocr_page::RasterBinding {
            asset_path: binding.asset_path.clone(),
            file_sha256: binding.file_sha256.clone(),
            pixel_sha256: binding.pixel_sha256.clone(),
            width_px: image.width,
            height_px: image.height,
            canonical_format: CanonicalFormat::Rgb8,
            colour_tag: scanweave_core::pixel_hash::ColourTag::Srgb,
            icc_sha256: None,
            orientation_policy: OrientationPolicy::AppliedOnce,
            decoder_id: "scanweave-io normalized-page builder (hocr route)".to_string(),
            dpi_x: Some(dpi),
            dpi_y: Some(dpi),
        },
        page: scanweave_core::ocr_page::PageGeometry {
            width_pt,
            height_pt,
            raster_to_page_pt: [72.0 / dpi, 0.0, 0.0, -72.0 / dpi, 0.0, height_pt],
        },
        source_geometry: None,
        producer: Producer {
            name: "hocr-import".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            models: vec![],
            languages: vec![],
        },
        granularity: if all_have_chars {
            Granularity::Symbol
        } else {
            Granularity::Word
        },
        // hOCR document order is a layout heuristic, not an accessible order claim
        reading_order_status: ReadingOrderStatus::Inferred,
        reading_order,
        spans,
        protected_regions: Vec::<ProtectedRegion>::new(),
    })
}
