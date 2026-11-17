//! Research-only component extensions. The original component map stays fixed.
use crate::{mask::Segmentation, ownership::OwnershipPlan, units::mask_identity_key};
use image::{GrayImage, Luma};
use imageproc::region_labelling::{connected_components, Connectivity};
use std::collections::{BTreeMap, HashMap, HashSet};

#[derive(Default, Debug, serde::Serialize)]
pub(crate) struct ExtensionLedger {
    /// Original component ID -> page-linear indices, never original foreground.
    pub pixels: BTreeMap<usize, Vec<usize>>,
    pub symbols: std::collections::BTreeSet<String>,
    pub attempted: usize,
    pub accepted: usize,
    pub rejected_neighbour: usize,
    pub rejected_disconnected: usize,
    pub rejected_overlap: usize,
    pub rejected_box: usize,
    pub rejected_veto: usize,
    pub decisions: Vec<UnitDecision>,
}

#[derive(Debug, serde::Serialize)]
pub(crate) struct UnitDecision {
    pub symbol_id: String,
    pub bbox: [f64; 4],
    pub original_ink_pixels: usize,
    pub proposed_pixels: usize,
    pub decision: &'static str,
}
fn decision(
    ledger: &mut ExtensionLedger,
    unit: &crate::units::Unit,
    count: usize,
    reason: &'static str,
) {
    ledger.decisions.push(UnitDecision {
        symbol_id: unit.symbol_id.clone(),
        bbox: unit.bbox_px,
        original_ink_pixels: unit.mask.iter().filter(|&&x| x).count(),
        proposed_pixels: count,
        decision: reason,
    });
}

fn labels(seg: &Segmentation) -> image::ImageBuffer<Luma<u32>, Vec<u32>> {
    let image = GrayImage::from_fn(seg.width as u32, seg.height as u32, |x, y| {
        Luma([if seg.fg[y as usize * seg.width + x as usize] {
            255
        } else {
            0
        }])
    });
    connected_components(&image, Connectivity::Eight, Luma([0u8]))
}

/// Validate every owned mask pixel against original IDs or a registered extension.
/// This is additional to, and never replaces, the original component-ID gate.
pub(crate) fn validate(plan: &OwnershipPlan, seg: &Segmentation, ledger: &ExtensionLedger) -> bool {
    if !plan.visual_invariant_ok() {
        return false;
    }
    let original = labels(seg);
    let owners = plan.unit_of_component();
    let mut extension_owner: HashMap<usize, usize> = HashMap::new();
    for (&component, pixels) in &ledger.pixels {
        let Some(&owner) = owners.get(&component) else {
            return false;
        };
        for &p in pixels {
            if p >= seg.fg.len() || seg.fg[p] || extension_owner.insert(p, owner).is_some() {
                return false;
            }
        }
    }
    let mut used = HashSet::new();
    for (ui, owned) in plan.owned.iter().enumerate() {
        let u = &owned.unit;
        let x0 = u.bbox_px[0] as usize;
        let y0 = u.bbox_px[1] as usize;
        if u.mask.len() != u.crop_w * u.crop_h
            || x0 + u.crop_w > seg.width
            || y0 + u.crop_h > seg.height
        {
            return false;
        }
        for (i, &ink) in u.mask.iter().enumerate() {
            if !ink {
                continue;
            }
            let x = x0 + i % u.crop_w;
            let y = y0 + i / u.crop_w;
            let p = y * seg.width + x;
            if !used.insert(p) {
                return false;
            }
            let label = original.get_pixel(x as u32, y as u32)[0] as usize;
            if label == 0 {
                if extension_owner.get(&p) != Some(&ui) {
                    return false;
                }
            } else if owners.get(&label) != Some(&ui) {
                return false;
            }
        }
    }
    // All registered pixels must have actually appeared in their unit mask.
    extension_owner.keys().all(|p| used.contains(p))
}

/// Expand only the experimental crop to the OCR glyph box plus a 2px PSF
/// margin. Original component labels and membership remain unchanged.
fn expanded_crop(
    u: &crate::units::Unit,
    width: usize,
    height: usize,
) -> Option<crate::units::Unit> {
    let b = u.ocr_bbox_px;
    if !b.iter().all(|x| x.is_finite()) || b[2] <= b[0] || b[3] <= b[1] {
        return None;
    }
    let ox = u.bbox_px[0] as usize;
    let oy = u.bbox_px[1] as usize;
    if ox + u.crop_w > width || oy + u.crop_h > height || u.mask.len() != u.crop_w * u.crop_h {
        return None;
    }
    let x0 = (b[0].floor() as isize - 2).max(0) as usize;
    let y0 = (b[1].floor() as isize - 2).max(0) as usize;
    let x1 = (b[2].ceil() as usize).saturating_add(2).min(width);
    let y1 = (b[3].ceil() as usize).saturating_add(2).min(height);
    let x0 = x0.min(ox);
    let y0 = y0.min(oy);
    let x1 = x1.max(ox + u.crop_w);
    let y1 = y1.max(oy + u.crop_h);
    if x1 <= x0 || y1 <= y0 || x1 > width || y1 > height {
        return None;
    }
    let mut expanded = u.clone();
    expanded.crop_w = x1 - x0;
    expanded.crop_h = y1 - y0;
    expanded.bbox_px = [x0 as f64, y0 as f64, x1 as f64, y1 as f64];
    expanded.mask = vec![false; expanded.crop_w * expanded.crop_h];
    for y in 0..u.crop_h {
        for x in 0..u.crop_w {
            expanded.mask[(y + oy - y0) * expanded.crop_w + x + ox - x0] = u.mask[y * u.crop_w + x];
        }
    }
    expanded.gray_samples = None;
    expanded.gray_halo = None;
    Some(expanded)
}

/// Add only complete, connected proposals inside the OCR glyph box and PSF margin.
/// Any unsafe/dropped part declines the entire unit and leaves it unchanged.
pub(crate) fn apply(
    plan: &mut OwnershipPlan,
    seg: &Segmentation,
    coverage: &GrayImage,
    paper_veto: &GrayImage,
    eligible: &HashSet<String>,
) -> ExtensionLedger {
    apply_inner(plan, seg, coverage, paper_veto, eligible, None)
}

/// Only the measurement wrapper may enable this: it must render the resulting
/// PDF and retry failed symbols with the stock path before publishing output.
pub(crate) fn apply_with_pdf_verifier(
    plan: &mut OwnershipPlan,
    seg: &Segmentation,
    coverage: &GrayImage,
    paper_veto: &GrayImage,
    eligible: &HashSet<String>,
    raw: &GrayImage,
) -> ExtensionLedger {
    apply_inner(plan, seg, coverage, paper_veto, eligible, Some(raw))
}
fn apply_inner(
    plan: &mut OwnershipPlan,
    seg: &Segmentation,
    coverage: &GrayImage,
    paper_veto: &GrayImage,
    eligible: &HashSet<String>,
    raw: Option<&GrayImage>,
) -> ExtensionLedger {
    let original = labels(seg);
    let owners = plan.unit_of_component();
    let mut ledger = ExtensionLedger::default();
    let mut claimed = HashSet::new();
    for ui in 0..plan.owned.len() {
        let owned = &plan.owned[ui];
        let u = &owned.unit;
        if owned.components.is_empty()
            || u.crop_w == 0
            || u.crop_h == 0
            || !eligible.contains(&u.symbol_id)
        {
            continue;
        }
        let Some(expanded) = expanded_crop(u, seg.width, seg.height) else {
            continue;
        };
        let u = &expanded;
        let x0 = u.bbox_px[0] as usize;
        let y0 = u.bbox_px[1] as usize;
        let mut proposed = u.mask.clone();
        let mut extra = Vec::new();
        for y in 0..u.crop_h {
            for x in 0..u.crop_w {
                let i = y * u.crop_w + x;
                let p = (y + y0) * seg.width + x + x0;
                if !u.mask[i] && coverage.get_pixel((x + x0) as u32, (y + y0) as u32)[0] >= 128 {
                    proposed[i] = true;
                    extra.push(p);
                }
            }
        }
        if extra.is_empty() {
            decision(&mut ledger, u, 0, "no_new_pixels");
            continue;
        }
        ledger.attempted += 1;
        // Reserve one pixel for the trace's subpixel contour excursion, plus
        // the two-pixel PSF footprint; affected units retain stock raster.
        let vetoed = (y0.saturating_sub(3)..(y0 + u.crop_h + 3).min(seg.height)).any(|y| {
            (x0.saturating_sub(3)..(x0 + u.crop_w + 3).min(seg.width))
                .any(|x| paper_veto.get_pixel(x as u32, y as u32)[0] != 0)
        });
        if vetoed {
            let Some(raw) = raw else {
                ledger.rejected_veto += 1;
                decision(
                    &mut ledger,
                    u,
                    extra.len(),
                    "paper_veto_needs_pdf_verification",
                );
                continue;
            };
            // Removing the veto cannot split a proposed connected stroke, nor
            // may it erase an original foreground pixel. The verifier checks
            // the final rendered PDF separately, after actual glyph tracing.
            let mut before = GrayImage::new(u.crop_w as u32, u.crop_h as u32);
            let mut after = GrayImage::new(u.crop_w as u32, u.crop_h as u32);
            let mut veto_original = false;
            for yy in 0..u.crop_h {
                for xx in 0..u.crop_w {
                    let i = yy * u.crop_w + xx;
                    let x = (x0 + xx) as u32;
                    let y = (y0 + yy) as u32;
                    let veto = paper_veto.get_pixel(x, y)[0] != 0;
                    veto_original |= veto && u.mask[i];
                    let b = u.mask[i] || raw.get_pixel(x, y)[0] >= 128;
                    before.put_pixel(xx as u32, yy as u32, Luma([if b { 255 } else { 0 }]));
                    after.put_pixel(
                        xx as u32,
                        yy as u32,
                        Luma([if proposed[i] && !veto { 255 } else { 0 }]),
                    );
                    if veto {
                        proposed[i] = false;
                    }
                }
            }
            extra.retain(|&p| {
                paper_veto.get_pixel((p % seg.width) as u32, (p / seg.width) as u32)[0] == 0
            });
            let count = |im: &GrayImage| {
                connected_components(im, Connectivity::Eight, Luma([0u8]))
                    .pixels()
                    .map(|p| p[0])
                    .max()
                    .unwrap_or(0)
            };
            if veto_original || count(&after) > count(&before) || extra.is_empty() {
                ledger.rejected_veto += 1;
                decision(&mut ledger, u, extra.len(), "paper_veto_disconnects_ink");
                continue;
            }
        }
        // If a candidate stroke continues immediately outside the tight unit
        // box, clipping it could break that glyph: retain the stock unit.
        let mut clipped = false;
        for y in 0..u.crop_h {
            for x in 0..u.crop_w {
                if !proposed[y * u.crop_w + x] {
                    continue;
                }
                let px = x0 + x;
                let py = y0 + y;
                for yy in py.saturating_sub(1)..=(py + 1).min(seg.height - 1) {
                    for xx in px.saturating_sub(1)..=(px + 1).min(seg.width - 1) {
                        if (xx < x0 || xx >= x0 + u.crop_w || yy < y0 || yy >= y0 + u.crop_h)
                            && coverage.get_pixel(xx as u32, yy as u32)[0] >= 128
                            && !seg.fg[yy * seg.width + xx]
                        {
                            clipped = true;
                        }
                    }
                }
            }
        }
        if clipped {
            ledger.rejected_box += 1;
            decision(&mut ledger, u, extra.len(), "candidate_crosses_unit_box");
            continue;
        }
        let mut bad = extra.iter().any(|&p| seg.fg[p]);
        // Guard the whole proposed region, not only its new pixels.
        for (i, &is_candidate) in proposed.iter().enumerate() {
            if !is_candidate {
                continue;
            }
            let x = x0 + i % u.crop_w;
            let y = y0 + i / u.crop_w;
            for yy in y.saturating_sub(2)..=(y + 2).min(seg.height - 1) {
                for xx in x.saturating_sub(2)..=(x + 2).min(seg.width - 1) {
                    let id = original.get_pixel(xx as u32, yy as u32)[0] as usize;
                    if id != 0 && owners.get(&id) != Some(&ui) {
                        bad = true;
                    }
                }
            }
            if bad {
                break;
            }
        }
        if bad {
            ledger.rejected_neighbour += 1;
            decision(
                &mut ledger,
                u,
                extra.len(),
                "other_component_within_two_pixels",
            );
            continue;
        }
        if extra.iter().any(|p| {
            let x = p % seg.width;
            let y = p / seg.width;
            (y.saturating_sub(2)..=(y + 2).min(seg.height - 1)).any(|yy| {
                (x.saturating_sub(2)..=(x + 2).min(seg.width - 1))
                    .any(|xx| claimed.contains(&(yy * seg.width + xx)))
            })
        }) {
            ledger.rejected_overlap += 1;
            decision(
                &mut ledger,
                u,
                extra.len(),
                "other_extension_within_two_pixels",
            );
            continue;
        }
        let mask = GrayImage::from_fn(u.crop_w as u32, u.crop_h as u32, |x, y| {
            Luma([if proposed[y as usize * u.crop_w + x as usize] {
                255
            } else {
                0
            }])
        });
        let components = connected_components(&mask, Connectivity::Eight, Luma([0u8]));
        let mut anchors: HashMap<u32, usize> = HashMap::new();
        for y in 0..u.crop_h {
            for x in 0..u.crop_w {
                let i = y * u.crop_w + x;
                if !u.mask[i] {
                    continue;
                }
                let c = components.get_pixel(x as u32, y as u32)[0];
                let old = original.get_pixel((x + x0) as u32, (y + y0) as u32)[0] as usize;
                if old == 0 || owners.get(&old) != Some(&ui) {
                    bad = true;
                    continue;
                }
                anchors
                    .entry(c)
                    .and_modify(|v| *v = (*v).min(old))
                    .or_insert(old);
            }
        }
        let mut pending = Vec::new();
        for &p in &extra {
            let x = p % seg.width - x0;
            let y = p / seg.width - y0;
            let c = components.get_pixel(x as u32, y as u32)[0];
            if let Some(&anchor) = anchors.get(&c) {
                pending.push((anchor, p));
            } else {
                bad = true;
                break;
            }
        }
        if bad {
            ledger.rejected_disconnected += 1;
            decision(
                &mut ledger,
                u,
                extra.len(),
                "candidate_disconnected_from_owned_component",
            );
            continue;
        }
        for (component, p) in pending {
            ledger.pixels.entry(component).or_default().push(p);
            claimed.insert(p);
        }
        decision(&mut ledger, u, extra.len(), "accepted");
        let mut unit = expanded;
        ledger.symbols.insert(unit.symbol_id.clone());
        unit.mask = proposed;
        unit.shape_key = mask_identity_key(&unit.mask, unit.crop_w, unit.crop_h);
        plan.owned[ui].unit = unit;
        ledger.accepted += 1;
    }
    ledger
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ownership::OwnedUnit, units::Unit};
    fn unit(symbol: &str, bbox: [f64; 4], mask: Vec<bool>) -> Unit {
        let w = (bbox[2] - bbox[0]) as usize;
        let h = (bbox[3] - bbox[1]) as usize;
        Unit {
            shape_key: symbol.into(),
            span_id: symbol.into(),
            symbol_id: symbol.into(),
            semantic_text: String::new(),
            bbox_px: bbox,
            ocr_bbox_px: bbox,
            crop_w: w,
            crop_h: h,
            mask,
            gray_samples: None,
            gray_halo: None,
        }
    }
    fn fixture(artwork: bool) -> (Segmentation, OwnershipPlan, GrayImage) {
        let (w, h) = (12, 12);
        let mut fg = vec![false; w * h];
        fg[5 * w + 4] = true;
        if artwork {
            fg[5 * w + 8] = true;
        }
        let mut mask = vec![false; 6 * 5];
        mask[2 * 6 + 1] = true;
        let mut plan = OwnershipPlan {
            owned: vec![OwnedUnit {
                unit: unit("x", [3., 3., 9., 8.], mask),
                components: vec![1],
                slots: vec![],
                suspect: false,
            }],
            components_total: if artwork { 2 } else { 1 },
            components_owned: 1,
            components_artwork: if artwork { 1 } else { 0 },
            ..Default::default()
        };
        if artwork {
            plan.artwork_units
                .push((unit("art", [8., 5., 9., 6.], vec![true]), vec![2]));
        }
        let mut coverage = GrayImage::new(w as u32, h as u32);
        coverage.put_pixel(5, 5, Luma([255]));
        coverage.put_pixel(6, 5, Luma([255]));
        (
            Segmentation {
                width: w,
                height: h,
                fg,
                paper: [255; 3],
                ink: [0; 3],
            },
            plan,
            coverage,
        )
    }
    #[test]
    fn connected_extension_is_recorded_and_validated() {
        let (seg, mut plan, c) = fixture(false);
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &GrayImage::new(seg.width as u32, seg.height as u32),
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 1);
        assert_eq!(ledger.pixels.get(&1).unwrap().len(), 2);
        assert!(validate(&plan, &seg, &ledger));
        plan.owned[0].unit.mask[0] = true;
        assert!(!validate(&plan, &seg, &ledger));
    }
    #[test]
    fn artwork_near_extension_declines_unchanged() {
        let (seg, mut plan, c) = fixture(true);
        let before = plan.owned[0].unit.mask.clone();
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &GrayImage::new(seg.width as u32, seg.height as u32),
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 0);
        assert_eq!(plan.owned[0].unit.mask, before);
        assert!(validate(&plan, &seg, &ledger));
        plan.owned[0].unit.mask[2 * 6 + 5] = true;
        assert!(!validate(&plan, &seg, &ledger));
    }
    #[test]
    fn other_text_component_within_two_pixels_declines() {
        let (seg, mut plan, c) = fixture(true);
        let (other, ids) = plan.artwork_units.pop().unwrap();
        plan.owned.push(OwnedUnit {
            unit: other,
            components: ids,
            slots: vec![],
            suspect: false,
        });
        plan.components_owned = 2;
        plan.components_artwork = 0;
        let before = plan.owned[0].unit.mask.clone();
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &GrayImage::new(seg.width as u32, seg.height as u32),
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 0);
        assert_eq!(ledger.rejected_neighbour, 1);
        assert_eq!(before, plan.owned[0].unit.mask);
        assert!(validate(&plan, &seg, &ledger));
    }
    #[test]
    fn candidate_continuing_outside_unit_box_declines() {
        let (seg, mut plan, mut c) = fixture(false);
        for x in 5..=11 {
            c.put_pixel(x, 5, Luma([255]));
        }
        let before = plan.owned[0].unit.mask.clone();
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &GrayImage::new(seg.width as u32, seg.height as u32),
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 0);
        assert_eq!(ledger.rejected_box, 1);
        assert_eq!(before, plan.owned[0].unit.mask);
    }
    #[test]
    fn proposed_pixel_outside_component_crop_but_inside_ocr_margin_is_allowed() {
        let (seg, mut plan, mut c) = fixture(false);
        for x in 5..=9 {
            c.put_pixel(x, 5, Luma([255]));
        }
        let original_bbox = plan.owned[0].unit.bbox_px;
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &GrayImage::new(seg.width as u32, seg.height as u32),
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 1);
        assert!(plan.owned[0].unit.bbox_px[2] > original_bbox[2]);
        assert!(validate(&plan, &seg, &ledger));
    }
    #[test]
    fn paper_veto_in_psf_footprint_declines_unchanged() {
        let (seg, mut plan, c) = fixture(false);
        let before = plan.owned[0].unit.mask.clone();
        let mut veto = GrayImage::new(seg.width as u32, seg.height as u32);
        veto.put_pixel(7, 6, Luma([255]));
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &veto,
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 0);
        assert_eq!(ledger.rejected_veto, 1);
        assert_eq!(before, plan.owned[0].unit.mask);
        assert!(validate(&plan, &seg, &ledger));
    }
    #[test]
    fn verifier_can_propose_when_veto_nearby_without_dropping_ink() {
        let (seg, mut plan, c) = fixture(false);
        let mut veto = GrayImage::new(seg.width as u32, seg.height as u32);
        veto.put_pixel(6, 6, Luma([255]));
        let ledger = apply_with_pdf_verifier(
            &mut plan,
            &seg,
            &c,
            &veto,
            &["x".to_string()].into_iter().collect(),
            &c,
        );
        assert_eq!(ledger.accepted, 1);
        assert!(validate(&plan, &seg, &ledger));
    }
    #[test]
    fn verifier_declines_if_removing_veto_splits_proposal() {
        let (seg, mut plan, mut c) = fixture(false);
        c.put_pixel(6, 5, Luma([0]));
        c.put_pixel(7, 5, Luma([255]));
        let mut raw = c.clone();
        raw.put_pixel(6, 5, Luma([255]));
        let mut veto = GrayImage::new(seg.width as u32, seg.height as u32);
        veto.put_pixel(6, 5, Luma([255]));
        let before = plan.owned[0].unit.mask.clone();
        let ledger = apply_with_pdf_verifier(
            &mut plan,
            &seg,
            &c,
            &veto,
            &["x".to_string()].into_iter().collect(),
            &raw,
        );
        assert_eq!(ledger.accepted, 0);
        assert_eq!(ledger.rejected_veto, 1);
        assert_eq!(plan.owned[0].unit.mask, before);
    }
    #[test]
    fn disconnected_proposal_declines_unchanged() {
        let (seg, mut plan, mut c) = fixture(false);
        c.put_pixel(5, 5, Luma([0]));
        c.put_pixel(6, 5, Luma([0]));
        c.put_pixel(8, 7, Luma([255]));
        let before = plan.owned[0].unit.mask.clone();
        let ledger = apply(
            &mut plan,
            &seg,
            &c,
            &GrayImage::new(seg.width as u32, seg.height as u32),
            &["x".to_string()].into_iter().collect(),
        );
        assert_eq!(ledger.accepted, 0);
        assert_eq!(ledger.rejected_disconnected, 1);
        assert_eq!(plan.owned[0].unit.mask, before);
    }
}
