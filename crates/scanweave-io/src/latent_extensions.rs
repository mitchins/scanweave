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

/// Add only complete, connected proposals inside the existing tight unit box.
/// Any unsafe/dropped part declines the entire unit and leaves it unchanged.
pub(crate) fn apply(
    plan: &mut OwnershipPlan,
    seg: &Segmentation,
    coverage: &GrayImage,
    paper_veto: &GrayImage,
    eligible: &HashSet<String>,
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
        let x0 = u.bbox_px[0] as usize;
        let y0 = u.bbox_px[1] as usize;
        if x0 + u.crop_w > seg.width
            || y0 + u.crop_h > seg.height
            || u.mask.len() != u.crop_w * u.crop_h
        {
            continue;
        }
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
            ledger.rejected_veto += 1;
            decision(&mut ledger, u, extra.len(), "paper_veto_in_unit_footprint");
            continue;
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
        let unit = &mut plan.owned[ui].unit;
        ledger.symbols.insert(unit.symbol_id.clone());
        unit.mask = proposed;
        unit.shape_key = mask_identity_key(&unit.mask, unit.crop_w, unit.crop_h);
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
        for x in 5..=9 {
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
