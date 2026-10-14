//! M0 probe library: exposed for integration testing (transport regression,
//! unit ownership). The binary in main.rs is a thin CLI over these modules.

pub mod baseline;
pub mod encoding;
pub mod glyphs;
pub mod fontbuild;
pub mod mask;
pub mod pdf;
pub mod trace;
pub mod units;

#[derive(Debug, Clone, serde::Serialize)]
pub struct StageMetrics {
    pub trace_max_px: f64,
    pub trace_p95_px: f64,
    pub curve_max_px: f64,
    pub quant_bound_px: f64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GlyphRecord {
    pub shape_key: String,
    pub label_text: String,
    pub gid: usize,
    pub cids: Vec<usize>,
    pub semantic_strings: Vec<String>,
    pub contours: usize,
    pub points: usize,
    pub em_px: f64,
    pub units_per_px: f64,
    pub stages: StageMetrics,
    pub budget_ok: bool,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct OccurrenceRecord {
    pub page_id: String,
    pub span_id: String,
    pub symbol_id: String,
    pub semantic_text: String,
    pub cid: usize,
    pub bbox_px: [f64; 4],
    /// SPEC §6.2 semantic owner (probe subset: visible_tounicode | unmapped)
    pub owner: String,
}

#[derive(Debug, Default, serde::Serialize)]
pub struct TraceLog {
    pub page_id: String,
    pub glyphs: Vec<GlyphRecord>,
    pub occurrences: Vec<OccurrenceRecord>,
    pub unowned_components: usize,
    pub em_px: f64,
    pub notes: Vec<String>,
}

