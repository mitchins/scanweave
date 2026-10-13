//! Canonical pixel hash v1 (SPEC Appendix A).
//! Preimage: `SWRASTER1\n{format}\n{width}\n{height}\n{colour_tag}\n{icc_hash_or_dash}\n`
//! followed by packed, row-major, top-to-bottom, padding-free sample bytes.

use crate::error::ScanWeaveError;
use serde::Deserialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
pub enum CanonicalFormat {
    #[serde(rename = "mono1_msb")]
    Mono1Msb,
    #[serde(rename = "gray8")]
    Gray8,
    #[serde(rename = "gray16be")]
    Gray16Be,
    #[serde(rename = "rgb8")]
    Rgb8,
    #[serde(rename = "rgb16be")]
    Rgb16Be,
    #[serde(rename = "rgba8")]
    Rgba8,
    #[serde(rename = "rgba16be")]
    Rgba16Be,
}

impl CanonicalFormat {
    pub fn as_str(&self) -> &'static str {
        match self {
            CanonicalFormat::Mono1Msb => "mono1_msb",
            CanonicalFormat::Gray8 => "gray8",
            CanonicalFormat::Gray16Be => "gray16be",
            CanonicalFormat::Rgb8 => "rgb8",
            CanonicalFormat::Rgb16Be => "rgb16be",
            CanonicalFormat::Rgba8 => "rgba8",
            CanonicalFormat::Rgba16Be => "rgba16be",
        }
    }

    /// Expected packed sample byte length for width*height, padding-free except the
    /// final partial byte of each mono1_msb row.
    pub fn sample_len(&self, width: u64, height: u64) -> u64 {
        match self {
            CanonicalFormat::Mono1Msb => (width.div_ceil(8)) * height,
            CanonicalFormat::Gray8 => width * height,
            CanonicalFormat::Gray16Be => 2 * width * height,
            CanonicalFormat::Rgb8 => 3 * width * height,
            CanonicalFormat::Rgb16Be => 6 * width * height,
            CanonicalFormat::Rgba8 => 4 * width * height,
            CanonicalFormat::Rgba16Be => 8 * width * height,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
pub enum ColourTag {
    #[serde(rename = "srgb")]
    Srgb,
    #[serde(rename = "gray_gamma22")]
    GrayGamma22,
    #[serde(rename = "icc")]
    Icc,
}

impl ColourTag {
    pub fn as_str(&self) -> &'static str {
        match self {
            ColourTag::Srgb => "srgb",
            ColourTag::GrayGamma22 => "gray_gamma22",
            ColourTag::Icc => "icc",
        }
    }
}

/// Compute the canonical pixel hash v1 over the given canonical decoded samples.
pub fn pixel_hash(
    format: CanonicalFormat,
    width: u64,
    height: u64,
    colour_tag: ColourTag,
    icc_sha256: Option<&str>,
    samples: &[u8],
) -> Result<String, ScanWeaveError> {
    if width == 0 || height == 0 {
        return Err(ScanWeaveError::InvalidInput {
            context: "pixel hash requires nonzero dimensions".into(),
        });
    }
    let want = format.sample_len(width, height);
    if samples.len() as u64 != want {
        return Err(ScanWeaveError::InvalidInput {
            context: format!(
                "sample length {} does not match {} {width}x{height} expectation {want}",
                samples.len(),
                format.as_str()
            ),
        });
    }
    let icc = match colour_tag {
        ColourTag::Icc => {
            let h = icc_sha256.ok_or_else(|| ScanWeaveError::InvalidInput {
                context: "colour_tag=icc requires a non-null icc_sha256".into(),
            })?;
            if !crate::is_sha256_hex(h) {
                return Err(ScanWeaveError::InvalidInput {
                    context: "icc_sha256 must be lowercase 64-hex".into(),
                });
            }
            h
        }
        _ => {
            if icc_sha256.is_some() {
                return Err(ScanWeaveError::InvalidInput {
                    context: "non-icc colour_tag must carry null icc_sha256".into(),
                });
            }
            "-"
        }
    };
    let header = format!(
        "SWRASTER1\n{}\n{width}\n{height}\n{}\n{icc}\n",
        format.as_str(),
        colour_tag.as_str()
    );
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(header.as_bytes());
    h.update(samples);
    let digest = h.finalize();
    Ok(digest.iter().map(|b| format!("{b:02x}")).collect())
}
