//! Visual-unit extraction: connected components grouped by OCR symbol geometry.
//! Connected-component count is NOT character count (SPEC §5.3): a unit owns all
//! components whose pixels fall inside the symbol observation polygon. Components
//! claimed by no symbol are counted as unowned (probe pages must have none).

use crate::mask::Segmentation;

#[derive(Debug, Clone, serde::Serialize)]
pub struct StageMetrics {
    pub trace_max_px: f64,
    pub trace_p95_px: f64,
    pub curve_max_px: f64,
    pub quant_bound_px: f64,
}
use scanweave_core::ocr_page::OcrPage;
use std::collections::HashSet;

#[derive(Debug, Clone)]
pub struct Unit {
    pub shape_key: String,
    pub span_id: String,
    pub symbol_id: String,
    pub semantic_text: String,
    /// bbox in pixel-edge coords [x0, y0, x1, y1]
    pub bbox_px: [f64; 4],
    /// original OCR geometry, retained separately from the observed ink crop
    pub ocr_bbox_px: [f64; 4],
    /// crop size
    pub crop_w: usize,
    pub crop_h: usize,
    /// binary ink mask within the crop (row-major)
    pub mask: Vec<bool>,
    /// Original grayscale crop, retained only for selected reconstruction witnesses.
    pub gray_samples: Option<Vec<u8>>,
    /// Two source pixels around the crop, for witnessed antialias ownership.
    pub gray_halo: Option<Vec<u8>>,
}

impl Unit {
    pub(crate) fn retain_grayscale(&mut self, rgb: &[u8], page_w: u32, page_h: u32) {
        let (w, h) = (page_w as usize, page_h as usize);
        let x0 = self.bbox_px[0] as usize;
        let y0 = self.bbox_px[1] as usize;
        if rgb.len() != w * h * 3 || x0 + self.crop_w > w || y0 + self.crop_h > h {
            return;
        }
        self.gray_halo = Some(
            (0..self.crop_h + 4)
                .flat_map(|y| {
                    (0..self.crop_w + 4).map(move |x| {
                        let sx = x0 as isize + x as isize - 2;
                        let sy = y0 as isize + y as isize - 2;
                        if sx < 0 || sy < 0 || sx >= w as isize || sy >= h as isize {
                            return 255;
                        }
                        let at = (sy as usize * w + sx as usize) * 3;
                        (0.2126 * rgb[at] as f64
                            + 0.7152 * rgb[at + 1] as f64
                            + 0.0722 * rgb[at + 2] as f64)
                            .round() as u8
                    })
                })
                .collect(),
        );
        self.gray_samples = Some(
            (0..self.crop_h)
                .flat_map(|y| {
                    (0..self.crop_w).map(move |x| {
                        let at = ((y0 + y) * w + x0 + x) * 3;
                        (0.2126 * rgb[at] as f64
                            + 0.7152 * rgb[at + 1] as f64
                            + 0.0722 * rgb[at + 2] as f64)
                            .round() as u8
                    })
                })
                .collect(),
        );
    }

    pub fn height_px(&self) -> usize {
        self.crop_h
    }
}

pub fn polygon_bbox(poly: &[[f64; 2]]) -> [f64; 4] {
    let mut bb = [f64::MAX, f64::MAX, f64::MIN, f64::MIN];
    for [x, y] in poly {
        bb[0] = bb[0].min(*x);
        bb[1] = bb[1].min(*y);
        bb[2] = bb[2].max(*x);
        bb[3] = bb[3].max(*y);
    }
    bb
}

pub fn extract_units(seg: &Segmentation, w: u32, h: u32, page: &OcrPage) -> (Vec<Unit>, usize) {
    // connected components, 8-connectivity
    let fg_image = image::GrayImage::from_fn(w, h, |x, y| {
        if seg.fg[(y as usize) * seg.width + (x as usize)] {
            image::Luma([255u8])
        } else {
            image::Luma([0u8])
        }
    });
    let labels = imageproc::region_labelling::connected_components(
        &fg_image,
        imageproc::region_labelling::Connectivity::Eight,
        image::Luma([0u8]),
    );

    // collect component pixel sets + bboxes
    let num_labels = labels.pixels().map(|p| p.0[0]).max().unwrap_or(0) as usize;
    let mut comp_pixels: Vec<Vec<(usize, usize)>> = vec![Vec::new(); num_labels + 1];
    for y in 0..seg.height {
        for x in 0..seg.width {
            if seg.fg[y * seg.width + x] {
                let l = labels.get_pixel(x as u32, y as u32).0[0] as usize;
                comp_pixels[l].push((x, y));
            }
        }
    }

    // Ownership (SPEC §5.2: overlapping candidate regions resolve into disjoint
    // ownership): each component goes to the TIGHTEST symbol polygon containing
    // its centroid. Real OCR boxes overlap; greedy first-claim drops symbols
    // (measured: 5 characters lost on the real-tesseract page).
    let poly_areas: Vec<f64> = page
        .spans
        .iter()
        .flat_map(|sp| {
            sp.symbols.iter().map(|sym| {
                let bb = polygon_bbox(&sym.polygon);
                (bb[2] - bb[0]) * (bb[3] - bb[1])
            })
        })
        .collect();
    let mut units = Vec::new();
    // component index -> symbol slot (span_idx, sym_idx)
    let mut owner_of: Vec<Option<usize>> = vec![None; comp_pixels.len()];
    let mut slot = 0usize;
    for span in &page.spans {
        for sym in &span.symbols {
            let bb = polygon_bbox(&sym.polygon);
            for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
                if pixels.is_empty() {
                    continue;
                }
                let cx = pixels.iter().map(|p| p.0).sum::<usize>() as f64 / pixels.len() as f64;
                let cy = pixels.iter().map(|p| p.1).sum::<usize>() as f64 / pixels.len() as f64;
                if cx >= bb[0] && cx <= bb[2] && cy >= bb[1] && cy <= bb[3] {
                    match owner_of[li] {
                        None => owner_of[li] = Some(slot),
                        Some(prev) => {
                            if poly_areas[slot] < poly_areas[prev] {
                                owner_of[li] = Some(slot); // tighter box wins
                            }
                        }
                    }
                }
            }
            slot += 1;
        }
    }
    // group components per symbol slot
    let mut slot_pixels: Vec<Vec<(usize, usize)>> = vec![Vec::new(); slot];
    for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
        if let Some(s) = owner_of[li] {
            slot_pixels[s].extend(pixels.iter().copied());
        }
    }
    let mut claimed: HashSet<usize> = HashSet::new();
    for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
        if !pixels.is_empty() && owner_of[li].is_some() {
            claimed.insert(li);
        }
    }
    // Touching-character repair (M0-Q item 2): a symbol left empty by the
    // disjoint ownership (its ink fused into a neighbour's connected component)
    // is ABSORBED into the owning unit — the merged component becomes ONE
    // visual unit carrying MULTIPLE semantic characters (SPEC §3/§5.3). Image
    // ownership and Unicode text ownership are independent: no character is
    // dropped, nothing is double-painted, and the merged unit's ToUnicode
    // carries the concatenated text in symbol-box x order.
    let mut absorbed: std::collections::HashMap<usize, Vec<(usize, String)>> =
        std::collections::HashMap::new(); // owner slot -> (owning empty slot idx, text)
    let mut si = 0usize; // FLATTENED slot index (spans x symbols) — must match
    for span in &page.spans {
        for sym in &span.symbols {
            si += 1;
            let this_slot = si - 1;
            if !slot_pixels[this_slot].is_empty() {
                continue;
            }
            let bb = polygon_bbox(&sym.polygon);
            // component with the most pixels intersecting the empty symbol box
            let mut best: Option<(usize, usize)> = None; // (count, comp li)
            for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
                let inside = pixels
                    .iter()
                    .filter(|(x, y)| {
                        *x as f64 >= bb[0]
                            && *x as f64 <= bb[2]
                            && *y as f64 >= bb[1]
                            && *y as f64 <= bb[3]
                    })
                    .count();
                if inside > 0 && best.is_none_or(|(bc, _)| inside > bc) {
                    best = Some((inside, li));
                }
            }
            if let Some((_, li)) = best {
                match owner_of[li] {
                    Some(owner_slot) => {
                        let text =
                            span.text[sym.text_range_utf8[0]..sym.text_range_utf8[1]].to_string();
                        absorbed
                            .entry(owner_slot)
                            .or_default()
                            .push((this_slot, text));
                    }
                    None => eprintln!("DBG absorb FAILED: best comp {} has NO owner", li),
                }
            } else {
                eprintln!(
                    "DBG absorb FAILED: no component intersects empty {} box {:?}",
                    sym.id, bb
                );
            }
            let _ = si;
        }
    }
    let mut slot_idx = 0usize;
    for span in &page.spans {
        for sym in &span.symbols {
            let mask_pixels = &slot_pixels[slot_idx];
            let absorbed_here = absorbed.remove(&slot_idx).unwrap_or_default();
            slot_idx += 1;
            {
                if mask_pixels.is_empty() {
                    // unabsorbed empty symbol: its ink is not attributable to any
                    // component (should not happen; counted as unowned ink instead)
                    continue;
                }
                let x0 = mask_pixels.iter().map(|p| p.0).min().unwrap();
                let y0 = mask_pixels.iter().map(|p| p.1).min().unwrap();
                let x1 = mask_pixels.iter().map(|p| p.0).max().unwrap() + 1;
                let y1 = mask_pixels.iter().map(|p| p.1).max().unwrap() + 1;
                let cw = x1 - x0;
                let ch = y1 - y0;
                let mut mask = vec![false; cw * ch];
                for (x, y) in mask_pixels.iter() {
                    mask[(y - y0) * cw + (x - x0)] = true;
                }
                let shape_key = mask_identity_key(&mask, cw, ch);
                // semantic ownership: own text-range text plus absorbed touching-
                // character texts, ordered by the OCR slot index (reading sequence).
                // Polygon x0 must NOT be used: hOCR boxes overlap horizontally
                // (measured: 'w' and 'i' both at x0=258), which corrupts order.
                let mut semantics: Vec<(usize, String)> = vec![(
                    slot_idx,
                    span.text[sym.text_range_utf8[0]..sym.text_range_utf8[1]].to_string(),
                )];
                semantics.extend(absorbed_here);
                semantics.sort_by_key(|a| a.0);
                let semantic_text: String = semantics.into_iter().map(|(_, t)| t).collect();
                units.push(Unit {
                    shape_key,
                    span_id: span.id.clone(),
                    symbol_id: sym.id.clone(),
                    semantic_text,
                    // exact INK bbox: placement maps ink to ink (the OCR polygon may
                    // include font padding and is only a hint)
                    bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
                    ocr_bbox_px: polygon_bbox(&sym.polygon),
                    crop_w: cw,
                    crop_h: ch,
                    mask,
                    gray_samples: None,
                    gray_halo: None,
                });
            }
        }
    }

    // unowned ink becomes vector artwork (VS-05: preserve or fall back — never drop)
    let mut artwork_units = Vec::new();
    let mut unowned_count = 0usize;
    for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
        if pixels.is_empty() || claimed.contains(&li) {
            continue;
        }
        unowned_count += 1;
        let x0 = pixels.iter().map(|p| p.0).min().unwrap();
        let y0 = pixels.iter().map(|p| p.1).min().unwrap();
        let x1 = pixels.iter().map(|p| p.0).max().unwrap() + 1;
        let y1 = pixels.iter().map(|p| p.1).max().unwrap() + 1;
        let cw = x1 - x0;
        let ch = y1 - y0;
        let mut mask = vec![false; cw * ch];
        for (x, y) in pixels {
            mask[(y - y0) * cw + (x - x0)] = true;
        }
        let packed: Vec<u8> = mask
            .chunks(8)
            .map(|c| {
                c.iter()
                    .enumerate()
                    .fold(0u8, |acc, (i, b)| acc | ((*b as u8) << i))
            })
            .collect();
        artwork_units.push(Unit {
            shape_key: scanweave_core::hash_hex(&packed),
            span_id: "unowned".to_string(),
            symbol_id: format!("unowned{li}"),
            semantic_text: String::new(), // empty => artwork, no text encoding
            bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
            ocr_bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
            crop_w: cw,
            crop_h: ch,
            mask,
            gray_samples: None,
            gray_halo: None,
        });
    }
    units.extend(artwork_units);

    (units, unowned_count)
}

/// Exact binary mask identity: dimensions are part of the geometry, not
/// recoverable from the packed row-major bit stream.
pub(crate) fn mask_identity_key(mask: &[bool], width: usize, height: usize) -> String {
    let mut packed: Vec<u8> = Vec::with_capacity(8 + (mask.len() + 7) / 8);
    packed.extend_from_slice(&(width as u32).to_le_bytes());
    packed.extend_from_slice(&(height as u32).to_le_bytes());
    packed.extend(mask.chunks(8).map(|c| {
        c.iter()
            .enumerate()
            .fold(0u8, |acc, (i, b)| acc | ((*b as u8) << i))
    }));
    scanweave_core::hash_hex(&packed)
}

#[cfg(test)]
mod identity_tests {
    use super::mask_identity_key;

    #[test]
    fn exact_mask_identity_includes_shape_dimensions() {
        let bits = [true, false, false, true, false, false, true, false];
        assert_ne!(
            mask_identity_key(&bits, 2, 4),
            mask_identity_key(&bits, 4, 2)
        );
        assert_eq!(
            mask_identity_key(&bits, 2, 4),
            mask_identity_key(&bits, 2, 4)
        );
    }
}
