//! scanweave-io: raster/OCR import, ownership planning, reconstruction,
//! font/PDF serialization. The single reconstruction implementation
//! (no second pipeline lives elsewhere).

pub mod baseline;
pub mod document;
pub mod encoding;
pub mod fontbuild;
pub mod glyphs;
pub mod hocr;
pub mod mask;
pub mod normalize;
pub mod ownership;
pub mod page_pdf;
pub mod pdf;
pub mod plan;
pub mod convert;
pub mod visual_dict;
pub mod trace;
pub mod units;
