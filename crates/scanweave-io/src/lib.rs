//! scanweave-io: raster/OCR import, ownership planning, reconstruction,
//! font/PDF serialization. The single reconstruction implementation
//! (no second pipeline lives elsewhere).

pub mod baseline;
pub mod convert;
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
pub mod trace;
pub mod units;
pub mod visual_dict;

mod contour_topology;
mod curve_fit;

mod serialization;
mod tonal_image;

pub mod source_image;

#[doc(hidden)]
pub mod font04;
