//! Visual-unit extraction: connected components grouped by OCR symbol geometry.
//! Connected-component count is NOT character count (SPEC §5.3): a unit owns all
//! components whose pixels fall inside the symbol observation polygon. Components
//! claimed by no symbol are counted as unowned (probe pages must have none).

use crate::mask::Segmentation;
use scanweave_core::ocr_page::OcrPage;
use std::collections::HashSet;

pub struct Unit {
    pub shape_key: String,
    pub span_id: String,
    pub symbol_id: String,
    pub semantic_text: String,
    /// bbox in pixel-edge coords [x0, y0, x1, y1]
    pub bbox_px: [f64; 4],
    /// crop size
    pub crop_w: usize,
    pub crop_h: usize,
    /// binary ink mask within the crop (row-major)
    pub mask: Vec<bool>,
}

impl Unit {
    pub fn height_px(&self) -> usize {
        self.crop_h
    }
}

fn polygon_bbox(poly: &[[f64; 2]]) -> [f64; 4] {
    let mut bb = [f64::MAX, f64::MAX, f64::MIN, f64::MIN];
    for [x, y] in poly {
        bb[0] = bb[0].min(*x);
        bb[1] = bb[1].min(*y);
        bb[2] = bb[2].max(*x);
        bb[3] = bb[3].max(*y);
    }
    bb
}

pub fn extract_units(
    seg: &Segmentation,
    w: u32,
    h: u32,
    page: &OcrPage,
) -> (Vec<Unit>, usize) {
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
    let num_labels = labels
        .pixels()
        .map(|p| p.0[0])
        .max()
        .unwrap_or(0) as usize;
    let mut comp_pixels: Vec<Vec<(usize, usize)>> = vec![Vec::new(); num_labels + 1];
    for y in 0..seg.height {
        for x in 0..seg.width {
            if seg.fg[y * seg.width + x] {
                let l = labels.get_pixel(x as u32, y as u32).0[0] as usize;
                comp_pixels[l].push((x, y));
            }
        }
    }

    let mut units = Vec::new();
    let mut claimed: HashSet<usize> = HashSet::new();
    for span in &page.spans {
        for sym in &span.symbols {
            let bb = polygon_bbox(&sym.polygon);
            let mut mask_pixels: Vec<(usize, usize)> = Vec::new();
            for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
                if pixels.is_empty() || claimed.contains(&li) {
                    continue;
                }
                // a component belongs to this unit when its centroid lies in the symbol bbox
                let cx = pixels.iter().map(|p| p.0).sum::<usize>() as f64 / pixels.len() as f64;
                let cy = pixels.iter().map(|p| p.1).sum::<usize>() as f64 / pixels.len() as f64;
                if cx >= bb[0] && cx <= bb[2] && cy >= bb[1] && cy <= bb[3] {
                    mask_pixels.extend(pixels.iter().copied());
                    claimed.insert(li);
                }
            }
            if mask_pixels.is_empty() {
                continue;
            }
            let x0 = mask_pixels.iter().map(|p| p.0).min().unwrap();
            let y0 = mask_pixels.iter().map(|p| p.1).min().unwrap();
            let x1 = mask_pixels.iter().map(|p| p.0).max().unwrap() + 1;
            let y1 = mask_pixels.iter().map(|p| p.1).max().unwrap() + 1;
            let cw = x1 - x0;
            let ch = y1 - y0;
            let mut mask = vec![false; cw * ch];
            for (x, y) in &mask_pixels {
                mask[(y - y0) * cw + (x - x0)] = true;
            }
            // shape key: hash of the normalized mask bits
            let packed: Vec<u8> = mask
                .chunks(8)
                .map(|c| c.iter().enumerate().fold(0u8, |acc, (i, b)| acc | ((*b as u8) << i)))
                .collect();
            let shape_key = scanweave_core::hash_hex(&packed);
            units.push(Unit {
                shape_key,
                span_id: span.id.clone(),
                symbol_id: sym.id.clone(),
                semantic_text: span.text[sym.text_range_utf8[0]..sym.text_range_utf8[1]]
                    .to_string(),
                // exact INK bbox: placement maps ink to ink (the OCR polygon may
                // include font padding and is only a hint)
                bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
                crop_w: cw,
                crop_h: ch,
                mask,
            });
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
            .map(|c| c.iter().enumerate().fold(0u8, |acc, (i, b)| acc | ((*b as u8) << i)))
            .collect();
        artwork_units.push(Unit {
            shape_key: scanweave_core::hash_hex(&packed),
            span_id: "unowned".to_string(),
            symbol_id: format!("unowned{li}"),
            semantic_text: String::new(), // empty => artwork, no text encoding
            bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
            crop_w: cw,
            crop_h: ch,
            mask,
        });
    }
    units.extend(artwork_units);

    (units, unowned_count)
}
