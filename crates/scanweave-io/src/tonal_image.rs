//! Bounded whole-page tonal representation. Never used for native exceptions.
//! Fixed source-feature checks supplement independently inspected real pages.

pub(crate) const QUALITY: u8 = 100;

fn luminance(rgb: &[u8]) -> f64 {
    (54.0 * rgb[0] as f64 + 183.0 * rgb[1] as f64 + 19.0 * rgb[2] as f64) / 256.0
}

pub(crate) fn eligible(samples: &[u8], width: u32, height: u32, colors: u8) -> bool {
    if width < 512
        || height < 512
        || width as u64 * height as u64 > 16_000_000
        || ![1, 3].contains(&colors)
        || (width as usize)
            .checked_mul(height as usize)
            .and_then(|n| n.checked_mul(colors as usize))
            != Some(samples.len())
    {
        return false;
    }
    let mut levels = [false; 256];
    for p in samples.chunks_exact(colors as usize) {
        levels[if colors == 1 {
            p[0]
        } else {
            luminance(p).round() as u8
        } as usize] = true;
    }
    levels.iter().filter(|&&v| v).count() >= 64
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
