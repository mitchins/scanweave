//! scanweave-io: image and OCR import, bundle validation adapters, font/PDF serialization.
//! Filesystem access is allowed here (adapter crate), never in scanweave-core.

pub mod hocr;
pub mod normalize;
