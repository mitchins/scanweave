//! ClearScan residual image encoding. Whole pages may use 200-DPI JPEG85 with
//! 4:2:0 chroma; tonal native exceptions retain full resolution and 4:4:4 JPEG90.
//! The caller selects actual byte savings; faithful and legacy Q100 stay separate.

pub(crate) const QUALITY: u8 = 100;
const COMPACT_QUALITY: u8 = 85;
const NATIVE_QUALITY: u8 = 90;

fn optimized_jpeg(
    samples: &[u8],
    width: u32,
    height: u32,
    colors: u8,
    quality: u8,
    sampling: jpeg_encoder::SamplingFactor,
) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    let mut encoder = jpeg_encoder::Encoder::new(&mut bytes, quality);
    encoder.set_sampling_factor(sampling);
    encoder.set_optimized_huffman_tables(true);
    // Optimized baseline RGB uses separate sequential scans that our current
    // JPEG decoder does not reliably reconstruct. Progressive scans preserve
    // the quantized coefficients and round-trip through that decoder correctly.
    if colors == 3 {
        encoder.set_progressive(true);
    }
    encoder
        .encode(
            samples,
            u16::try_from(width).map_err(|_| "JPEG width exceeds 16-bit dimensions")?,
            u16::try_from(height).map_err(|_| "JPEG height exceeds 16-bit dimensions")?,
            if colors == 1 {
                jpeg_encoder::ColorType::Luma
            } else {
                jpeg_encoder::ColorType::Rgb
            },
        )
        .map_err(|error| error.to_string())?;
    Ok(bytes)
}

/// Native-size candidate, retaining ACR-01 if the optional encoder fails/grows.
pub(crate) fn encode_compact(
    samples: &[u8],
    width: u32,
    height: u32,
    colors: u8,
) -> Result<Option<Vec<u8>>, String> {
    if !eligible(samples, width, height, colors) {
        return Ok(None);
    }
    let mut legacy = Vec::new();
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut legacy, COMPACT_QUALITY)
        .encode(
            samples,
            width,
            height,
            if colors == 1 {
                image::ExtendedColorType::L8
            } else {
                image::ExtendedColorType::Rgb8
            },
        )
        .map_err(|error| error.to_string())?;
    if let Ok(compact) = optimized_jpeg(
        samples,
        width,
        height,
        colors,
        COMPACT_QUALITY,
        jpeg_encoder::SamplingFactor::R_4_2_0,
    ) {
        if compact.len() < legacy.len() {
            return Ok(Some(compact));
        }
    }
    Ok(Some(legacy))
}

/// Sample dimensions are independent of the unchanged PDF placement transform.
pub(crate) struct CompactImage {
    pub bytes: Vec<u8>,
    pub width: u32,
    pub height: u32,
}

fn resized_samples(
    samples: &[u8],
    width: u32,
    height: u32,
    colors: u8,
    w: u32,
    h: u32,
) -> Result<Vec<u8>, String> {
    let filter = image::imageops::FilterType::Lanczos3;
    if colors == 1 {
        let image = image::GrayImage::from_raw(width, height, samples.to_vec())
            .ok_or("invalid grayscale residual")?;
        Ok(image::imageops::resize(&image, w, h, filter).into_raw())
    } else {
        let image = image::RgbImage::from_raw(width, height, samples.to_vec())
            .ok_or("invalid RGB residual")?;
        Ok(image::imageops::resize(&image, w, h, filter).into_raw())
    }
}

/// Qualified whole-page residual. Never upscale; require 5% encoded savings for
/// reducing resolution. Native exceptions and verified source JPEGs do not enter.
pub(crate) fn encode_residual(
    samples: &[u8],
    width: u32,
    height: u32,
    colors: u8,
    page_width_pt: f32,
    page_height_pt: f32,
) -> Result<Option<CompactImage>, String> {
    let Some(bytes) = encode_compact(samples, width, height, colors)? else {
        return Ok(None);
    };
    let native = CompactImage {
        bytes,
        width,
        height,
    };
    if !page_width_pt.is_finite()
        || !page_height_pt.is_finite()
        || page_width_pt <= 0.0
        || page_height_pt <= 0.0
    {
        return Ok(Some(native));
    }
    let scale = (200.0 * f64::from(page_width_pt) / (72.0 * f64::from(width)))
        .min(200.0 * f64::from(page_height_pt) / (72.0 * f64::from(height)))
        .min(1.0);
    let w = (f64::from(width) * scale).round().max(1.0) as u32;
    let h = (f64::from(height) * scale).round().max(1.0) as u32;
    if w == width && h == height {
        return Ok(Some(native));
    }
    let samples = resized_samples(samples, width, height, colors, w, h)?;
    match optimized_jpeg(
        &samples,
        w,
        h,
        colors,
        COMPACT_QUALITY,
        jpeg_encoder::SamplingFactor::R_4_2_0,
    ) {
        Ok(bytes) if (bytes.len() as f64) < native.bytes.len() as f64 * 0.95 => {
            Ok(Some(CompactImage {
                bytes,
                width: w,
                height: h,
            }))
        }
        _ => Ok(Some(native)),
    }
}

/// Source-resolution tonal exception only. Binary ink and tiny resources retain
/// Flate; callers separately require a material encoded-size saving.
pub(crate) fn native_candidate(samples: &[u8], width: u32, height: u32, colors: u8) -> bool {
    width >= 16
        && height >= 16
        && width <= u16::MAX as u32
        && height <= u16::MAX as u32
        && tonal_samples(samples, width, height, colors)
}

pub(crate) fn encode_native(
    samples: &[u8],
    width: u32,
    height: u32,
    colors: u8,
) -> Result<Option<Vec<u8>>, String> {
    if !native_candidate(samples, width, height, colors) {
        return Ok(None);
    }
    // Fine coloured edges are not subsampled in native exception crops.
    optimized_jpeg(
        samples,
        width,
        height,
        colors,
        NATIVE_QUALITY,
        jpeg_encoder::SamplingFactor::R_4_4_4,
    )
    .map(Some)
}

fn luminance(rgb: &[u8]) -> f64 {
    (54.0 * rgb[0] as f64 + 183.0 * rgb[1] as f64 + 19.0 * rgb[2] as f64) / 256.0
}

pub(crate) fn eligible(samples: &[u8], width: u32, height: u32, colors: u8) -> bool {
    width >= 512 && height >= 512 && tonal_samples(samples, width, height, colors)
}

fn tonal_samples(samples: &[u8], width: u32, height: u32, colors: u8) -> bool {
    if width as u64 * height as u64 > 16_000_000
        || ![1, 3].contains(&colors)
        || (width as usize)
            .checked_mul(height as usize)
            .and_then(|n| n.checked_mul(colors as usize))
            != Some(samples.len())
    {
        return false;
    }
    let mut levels = [false; 256];
    for pixel in samples.chunks_exact(colors as usize) {
        levels[if colors == 1 {
            pixel[0]
        } else {
            luminance(pixel).round() as u8
        } as usize] = true;
    }
    levels.iter().filter(|&&present| present).count() >= 64
}

/// Inspect every source pixel, including faint isolated dark/light ridges and thin
/// horizontal/vertical marks. No OCR rectangles or glyph assumptions are used.
pub(crate) fn preserves_details(
    original: &[u8],
    decoded: &[u8],
    width: u32,
    height: u32,
    colors: u8,
) -> bool {
    if width < 3
        || height < 3
        || width as u64 * height as u64 > 16_000_000
        || ![1, 3].contains(&colors)
        || original.len() != decoded.len()
        || original.len() != width as usize * height as usize * colors as usize
        || original
            .iter()
            .zip(decoded)
            .any(|(&a, &b)| a.abs_diff(b) > 12)
    {
        return false;
    }
    let stride = colors as usize;
    let gray = |samples: &[u8], x: usize, y: usize| {
        let at = (y * width as usize + x) * stride;
        if colors == 1 {
            samples[at] as f64
        } else {
            luminance(&samples[at..at + 3])
        }
    };
    for y in 1..height as usize - 1 {
        for x in 1..width as usize - 1 {
            let a = gray(original, x, y);
            let b = gray(decoded, x, y);
            for (p, q) in [((x - 1, y), (x + 1, y)), ((x, y - 1), (x, y + 1))] {
                let op = gray(original, p.0, p.1);
                let oq = gray(original, q.0, q.1);
                let dp = gray(decoded, p.0, p.1);
                let dq = gray(decoded, q.0, q.1);
                for (contrast, retained) in [
                    (op.min(oq) - a, dp.min(dq) - b),
                    (a - op.max(oq), b - dp.max(dq)),
                ] {
                    if !ridge_preserved(contrast, retained) {
                        return false;
                    }
                }
            }
        }
    }
    true
}

// Keep the strict comparisons and arithmetic shared by dark and light ridges.
fn ridge_preserved(contrast: f64, retained: f64) -> bool {
    if contrast < 8.0 {
        return true;
    }
    let minimum = if contrast >= 12.0 {
        contrast * 0.5 - 1.0
    } else {
        2.0
    };
    if retained < minimum {
        return false;
    }
    true
}

pub(crate) fn encode(
    samples: &[u8],
    width: u32,
    height: u32,
    colors: u8,
) -> Result<Option<Vec<u8>>, String> {
    if !eligible(samples, width, height, colors) {
        return Ok(None);
    }
    let mut jpeg = Vec::new();
    let color = if colors == 1 {
        image::ExtendedColorType::L8
    } else {
        image::ExtendedColorType::Rgb8
    };
    // image 0.25 encodes all RGB SOF sampling factors as 1x1 (4:4:4).
    // A regression checks emitted factors, independently of its stale doc comment.
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, QUALITY)
        .encode(samples, width, height, color)
        .map_err(|e| e.to_string())?;
    let decoded = image::load_from_memory_with_format(&jpeg, image::ImageFormat::Jpeg)
        .map_err(|e| e.to_string())?;
    let data = if colors == 1 {
        decoded.to_luma8().into_raw()
    } else {
        decoded.to_rgb8().into_raw()
    };
    if decoded.width() != width
        || decoded.height() != height
        || !preserves_details(samples, &data, width, height, colors)
    {
        return Ok(None);
    }
    Ok(Some(jpeg))
}

#[cfg(test)]
mod tests {
    #[test]
    fn compact_encoder_keeps_native_dimensions_sampling_and_thin_dark_details() {
        let (w, h) = (512usize, 512usize);
        let mut rgb = Vec::with_capacity(w * h * 3);
        for y in 0..h {
            for x in 0..w {
                let background = ((x + y) % 128 + 128) as u8;
                let ink = (y == 250 && (100..400).contains(&x))
                    || ((280..283).contains(&y) && (310..313).contains(&x));
                rgb.extend(if ink { [20; 3] } else { [background; 3] });
            }
        }
        let encoded = encode_compact(&rgb, w as u32, h as u32, 3)
            .unwrap()
            .unwrap();
        assert_eq!(
            encoded,
            encode_compact(&rgb, w as u32, h as u32, 3)
                .unwrap()
                .unwrap()
        );
        let decoded = image::load_from_memory(&encoded).unwrap().to_rgb8();
        assert_eq!(decoded.dimensions(), (512, 512));
        for x in 110..390 {
            assert!(decoded.get_pixel(x, 250)[0] < 80, "thin rule lost at {x}");
        }
        assert!(
            decoded.get_pixel(311, 281)[0] < 80,
            "decimal-sized mark lost"
        );
        let at = encoded.windows(2).position(|w| w == [0xff, 0xc2]).unwrap();
        let sof = &encoded[at + 2..];
        assert_eq!(sof[7], 3);
        assert_eq!(sof[9], 0x22);
        assert_eq!(sof[12], 0x11);
        assert_eq!(sof[15], 0x11);
    }

    #[test]
    fn progressive_native_colour_roundtrips_partial_mcu_edges() {
        let (w, h) = (63usize, 79usize);
        let mut samples = Vec::new();
        for y in 0..h {
            for x in 0..w {
                samples.extend(if (25..28).contains(&x) && (20..60).contains(&y) {
                    [20, 85, 150]
                } else if (40..55).contains(&x) && (45..65).contains(&y) {
                    [160, 25, 30]
                } else if (8..20).contains(&x) && (8..20).contains(&y) {
                    [250; 3]
                } else {
                    [(128 + (x + y) % 128) as u8; 3]
                });
            }
        }
        let jpeg = encode_native(&samples, w as u32, h as u32, 3)
            .unwrap()
            .unwrap();
        assert_eq!(
            jpeg,
            encode_native(&samples, w as u32, h as u32, 3)
                .unwrap()
                .unwrap()
        );
        let image = image::load_from_memory(&jpeg).unwrap().to_rgb8();
        assert_eq!(image.dimensions(), (63, 79));
        assert!(image.get_pixel(14, 14).0.iter().all(|&v| v > 240));
        let blue = image.get_pixel(26, 35).0;
        assert!(blue[2] > blue[0] + 80 && blue[1] > blue[0] + 30);
        let red = image.get_pixel(48, 55).0;
        assert!(red[0] > red[1] + 80);
    }

    #[test]
    fn native_exception_rejects_binary_tiny_and_malformed_samples() {
        assert!(encode_native(&[255; 32 * 32], 32, 32, 1).unwrap().is_none());
        assert!(encode_native(&[0; 3], 16, 16, 3).unwrap().is_none());
        assert!(encode_native(&[], u32::MAX, 32, 3).unwrap().is_none());
        assert!(encode_native(&[0; 8 * 8 * 3], 8, 8, 3).unwrap().is_none());
    }

    #[test]
    fn residual_resolution_uses_page_points_and_never_upscales() {
        let samples: Vec<_> = (0..512 * 512).map(|i| (i % 256) as u8).collect();
        let high = encode_residual(&samples, 512, 512, 1, 72., 72.)
            .unwrap()
            .unwrap();
        assert_eq!((high.width, high.height), (200, 200));
        let low = encode_residual(&samples, 512, 512, 1, 512., 512.)
            .unwrap()
            .unwrap();
        assert_eq!((low.width, low.height), (512, 512));
        let invalid = encode_residual(&samples, 512, 512, 1, f32::NAN, 72.)
            .unwrap()
            .unwrap();
        assert_eq!((invalid.width, invalid.height), (512, 512));
    }

    #[test]
    fn compact_encoder_rejects_invalid_bitonal_and_patch_sized_inputs() {
        assert!(encode_compact(&[], 512, 512, 3).unwrap().is_none());
        assert!(encode_compact(&vec![255; 512 * 512], 512, 512, 1)
            .unwrap()
            .is_none());
        assert!(encode_compact(&vec![128; 32 * 32 * 3], 32, 32, 3)
            .unwrap()
            .is_none());
        assert!(encode_compact(&[], u32::MAX, 1, 3).unwrap().is_none());
    }

    #[test]
    fn ridge_rule_retains_strict_boundary_and_float_behavior() {
        for contrast in [
            f64::NEG_INFINITY,
            -1.0,
            7.999,
            8.0,
            11.999,
            12.0,
            255.0,
            f64::INFINITY,
            f64::NAN,
        ] {
            for retained in [-1.0, 1.999, 2.0, 4.999, 5.0, 126.5, f64::NAN] {
                let expected = if contrast < 8.0 {
                    true
                } else {
                    let minimum = if contrast >= 12.0 {
                        contrast * 0.5 - 1.0
                    } else {
                        2.0
                    };
                    !matches!(
                        retained.partial_cmp(&minimum),
                        Some(std::cmp::Ordering::Less)
                    )
                };
                assert_eq!(super::ridge_preserved(contrast, retained), expected);
            }
        }
    }

    use super::*;
    #[test]
    fn invalid_buffers_bitonal_and_oversized_pages_stay_lossless() {
        assert!(!eligible(&[], 512, 512, 3));
        assert!(!eligible(&[0; 12], u32::MAX, u32::MAX, 3));
        assert!(!preserves_details(&[], &[], 0, 0, 1));
        assert!(!preserves_details(&[0], &[0], 3, 3, 1));
        let samples = vec![255; 512 * 512];
        assert!(!eligible(&samples, 512, 512, 1));
        assert!(encode(&samples, 512, 512, 1).unwrap().is_none());
        assert!(!eligible(&[], 4000, 4001, 3));
    }
    #[test]
    fn faint_dark_and_light_marks_cannot_disappear_inside_the_error_cap() {
        for value in [116, 140] {
            let mut original = vec![128; 9 * 9];
            original[4 * 9 + 4] = value;
            let erased = vec![128; 9 * 9];
            assert!(!preserves_details(&original, &erased, 9, 9, 1));
            assert!(preserves_details(&original, &original, 9, 9, 1));
        }
    }
    #[test]
    fn thin_rules_are_protected_and_minor_tonal_change_is_allowed() {
        let mut original = vec![180; 9 * 9];
        for x in 0..9 {
            original[4 * 9 + x] = 168;
        }
        assert!(!preserves_details(&original, &vec![180; 81], 9, 9, 1));
        let shifted: Vec<_> = original.iter().map(|v| v + 1).collect();
        assert!(preserves_details(&original, &shifted, 9, 9, 1));
    }
    #[test]
    fn encoder_uses_full_chroma_sampling_and_is_deterministic() {
        let mut samples = Vec::new();
        for y in 0..512 {
            for x in 0..512 {
                samples.extend([
                    ((x / 2) % 256) as u8,
                    ((y / 2) % 256) as u8,
                    ((x + y) / 4) as u8,
                ]);
            }
        }
        let jpeg = encode(&samples, 512, 512, 3).unwrap().unwrap();
        assert_eq!(jpeg, encode(&samples, 512, 512, 3).unwrap().unwrap());
        let at = jpeg.windows(2).position(|w| w == [0xff, 0xc0]).unwrap();
        let sof = &jpeg[at + 2..];
        assert_eq!(sof[7], 3);
        for c in 0..3 {
            assert_eq!(sof[9 + c * 3], 0x11, "chroma subsampling changed");
        }
    }
}
