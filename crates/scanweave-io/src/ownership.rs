//! Generalized ownership solver (M1-A).
//!
//! Replaces greedy one-to-one component assignment with an explicit
//! many-to-many ownership model:
//!
//!   1. one component → multiple semantic symbols (touching `rn`, `fi`, `ll`,
//!      kerned digits): the component becomes ONE visual unit carrying the
//!      concatenated (slot-ordered) text of every symbol its ink covers;
//!   2. multiple components → one symbol (dotted `i`/`j`, accents, kana
//!      dakuten/handakuten): the unit owns all of them;
//!   3. multiple components → multiple symbols: every component is assigned
//!      exactly once; a symbol's owned components may serve several symbols,
//!      whose texts concatenate in OCR slot order into the owning unit;
//!   4. overlapping OCR boxes resolve deterministically (tightest containing
//!      box wins; ties break on smaller polygon area, then lexical symbol id);
//!   5. components claimed by no symbol become non-text artwork (never dropped,
//!      never relabelled).
//!
//! Two invariants are preserved separately:
//!   * visual: every source ink component is owned exactly once (unit or
//!     artwork) — no unowned ink, no double painting;
//!   * semantic: every supplied OCR span keeps exactly one searchable owner
//!     (a unit carrying its full text); component count never determines
//!     character count.
//!
//! OCR geometry establishes candidate relationships; OCR labels never drive
//! visual shape equivalence.

use crate::mask::Segmentation;
use crate::units::{polygon_bbox, Unit};
use scanweave_core::ocr_page::OcrPage;
use std::collections::HashMap;

/// One semantic slot: a symbol observation from the supplied OCR.
#[derive(Debug, Clone, PartialEq)]
pub struct Slot {
    pub span_id: String,
    pub symbol_id: String,
    pub text: String,
    pub polygon: Vec<[f64; 2]>,
    pub bbox: [f64; 4],
    pub area: f64,
}

/// A component→unit assignment; slots owned by the unit (in slot order).
#[derive(Debug, Clone)]
pub struct OwnedUnit {
    pub unit: Unit,
    pub components: Vec<usize>,
    pub slots: Vec<SlotRef>,
    /// the unit's ink extends beyond the union of its symbol boxes by more than
    /// the contact margin (e.g. text raster-fused with a rule/stamp): the
    /// component cannot be attributed safely to text alone
    pub suspect: bool,
}

#[derive(Debug, Default, Clone)]
pub struct OwnershipPlan {
    pub owned: Vec<OwnedUnit>,
    pub artwork_units: Vec<(Unit, Vec<usize>)>,
    pub components_total: usize,
    pub components_owned: usize,
    pub components_artwork: usize,
    /// units whose ink cannot be safely attributed to the supplied symbols
    pub suspect_units: usize,
    /// invocation log (sorted for determinism)
    pub notes: Vec<String>,
}

impl OwnershipPlan {
    /// Visual invariant: every component is owned exactly once (unit or
    /// artwork) and no component is owned twice.
    pub fn visual_invariant_ok(&self) -> bool {
        if self.components_owned + self.components_artwork != self.components_total {
            return false;
        }
        let mut seen: Vec<usize> = Vec::new();
        for u in &self.owned {
            seen.extend(u.components.iter().copied());
        }
        for (_, comps) in &self.artwork_units {
            seen.extend(comps.iter().copied());
        }
        if seen.len() != self.components_total {
            return false;
        }
        let mut sorted = seen.clone();
        sorted.sort_unstable();
        sorted.windows(2).all(|w| w[0] != w[1])
    }

    /// Semantic invariant: the reading stream reassembled from all owning
    /// units' slots (ordered by OCR slot index, i.e. reading order) must equal
    /// the exact supplied OCR character stream — no addition, no omission,
    /// no duplication, no reordering. Unit/paint boundaries are presentation
    /// and must never change what the page says.
    pub fn semantic_invariant_ok(&self, page: &OcrPage) -> bool {
        let mut supplied = String::new();
        for span in &page.spans {
            for sym in &span.symbols {
                supplied.push_str(&span.text[sym.text_range_utf8[0]..sym.text_range_utf8[1]]);
            }
        }
        let mut pairs: Vec<(usize, &str)> = Vec::new();
        for u in &self.owned {
            for s in &u.slots {
                pairs.push((s.order, s.text.as_str()));
            }
        }
        pairs.sort_by_key(|p| p.0);
        let emitted: String = pairs.iter().map(|p| p.1).collect();
        supplied == emitted
    }

    /// component id → owning unit index (for the transactional fallback)
    pub fn unit_of_component(&self) -> HashMap<usize, usize> {
        let mut map = HashMap::new();
        for (ui, u) in self.owned.iter().enumerate() {
            for c in &u.components {
                map.insert(*c, ui);
            }
        }
        map
    }
}

impl OwnedUnit {
    /// the unit's semantic text: all owned slots' texts in slot (reading) order
    pub fn semantic_text(&self) -> String {
        let mut parts: Vec<&SlotRef> = self.slots.iter().collect::<Vec<&SlotRef>>();
        parts.sort_by_key(|s| s.order);
        parts.iter().map(|s| s.text.as_str()).collect()
    }
}

/// Slot reference into the plan's slot registry (order-stable identity).
#[derive(Debug, Clone, PartialEq)]
pub struct SlotRef {
    pub order: usize,
    pub text: String,
    pub symbol_id: String,
    pub bbox: [f64; 4],
}

/// Build the ownership plan for a page.
///
/// `components` index occupies label `li - 1` in the plan (labels are 1-based
/// in imageproc and are normalized here).
pub fn build_plan(
    seg: &Segmentation,
    w: u32,
    h: u32,
    page: &OcrPage,
) -> (OwnershipPlan, (Vec<Unit>, usize)) {
    // Construct the explicit ownership plan once. The former extract_units
    // call computed and discarded another complete component assignment.
    use image::GrayImage;
    use image::Luma;
    use imageproc::region_labelling::connected_components;
    use imageproc::region_labelling::Connectivity;

    let fg_image = GrayImage::from_fn(w, h, |x, y| {
        if seg.fg[(y as usize) * seg.width + (x as usize)] {
            Luma([255u8])
        } else {
            Luma([0u8])
        }
    });
    let labels = connected_components(&fg_image, Connectivity::Eight, Luma([0u8]));
    let num = labels.pixels().map(|p| p.0[0]).max().unwrap_or(0) as usize;
    let mut comp_pixels: Vec<Vec<(usize, usize)>> = vec![Vec::new(); num + 1];
    for y in 0..seg.height {
        for x in 0..seg.width {
            if seg.fg[y * seg.width + x] {
                let l = labels.get_pixel(x as u32, y as u32).0[0] as usize;
                comp_pixels[l].push((x, y));
            }
        }
    }

    // slots in reading order (span order = OCR order; symbols in span order)
    let mut slots: Vec<Slot> = Vec::new();
    let mut order = 0usize;
    for span in &page.spans {
        for sym in &span.symbols {
            let bb = polygon_bbox(&sym.polygon);
            slots.push(Slot {
                span_id: span.id.clone(),
                symbol_id: sym.id.clone(),
                text: span.text[sym.text_range_utf8[0]..sym.text_range_utf8[1]].to_string(),
                polygon: sym.polygon.clone(),
                bbox: bb,
                area: (bb[2] - bb[0]) * (bb[3] - bb[1]),
            });
            let _ = order;
            order += 1;
        }
    }

    // Assignment: every component → tightest containing slot; unassigned →
    // artwork. Deterministic tie-break: smaller area, then symbol id.
    let mut owner_of: Vec<Option<usize>> = vec![None; comp_pixels.len()];
    for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
        if pixels.is_empty() {
            continue;
        }
        let cx = pixels.iter().map(|p| p.0).sum::<usize>() as f64 / pixels.len() as f64;
        let cy = pixels.iter().map(|p| p.1).sum::<usize>() as f64 / pixels.len() as f64;
        // find best slot: tightest containing; unowned if none contains
        // (ambiguity: if the component overlaps several slots, the tightest
        // containing wins; on ties, the lower-order slot)
        let mut best: Option<(usize, f64, String)> = None;
        for (si, slot) in slots.iter().enumerate() {
            if cx >= slot.bbox[0] && cx <= slot.bbox[2] && cy >= slot.bbox[1] && cy <= slot.bbox[3]
            {
                let cand = (si, slot.area, slot.symbol_id.clone());
                best = match best {
                    None => Some(cand),
                    Some((bsi, barea, bid)) => {
                        if cand.1 < barea || (cand.1 == barea && cand.2 < bid) {
                            Some(cand)
                        } else {
                            Some((bsi, barea, bid))
                        }
                    }
                };
            }
        }
        if let Some((si, _, _)) = best {
            owner_of[li] = Some(si);
        }
    }

    // Units: per slot, gather its owned components
    let mut slot_comps: Vec<Vec<usize>> = vec![Vec::new(); slots.len()];
    for (li, o) in owner_of.iter().enumerate().skip(1) {
        if let Some(si) = o {
            slot_comps[*si].push(li);
        }
    }

    let mut plan = OwnershipPlan::default();
    let mut units_out: Vec<Unit> = Vec::new();
    plan.components_total = comp_pixels.iter().skip(1).filter(|p| !p.is_empty()).count();

    // Text units: one per slot that owns at least one component. A unit whose
    // slot has NO components is absorbed into the slot-owning unit that shares
    // the most pixels of its ink (touching characters): that component's unit
    // then carries both characters in slot order.
    let mut unit_of_slot: HashMap<usize, usize> = HashMap::new();
    let mut ui = 0usize;
    for (si, comps) in slot_comps.iter().enumerate() {
        if comps.is_empty() {
            continue;
        }
        let mut mask_pixels: Vec<(usize, usize)> = Vec::new();
        for &c in comps {
            mask_pixels.extend(comp_pixels[c].iter().copied());
        }
        let u = make_unit(&mask_pixels, page, &slots[si], si);
        let suspect = unit_ink_exceeds_slots(&comp_pixels, comps, &slots[si], 6.0);
        unit_of_slot.insert(si, ui);
        plan.owned.push(OwnedUnit {
            slots: vec![SlotRef {
                order: si,
                text: slots[si].text.clone(),
                symbol_id: slots[si].symbol_id.clone(),
                bbox: slots[si].bbox,
            }],
            components: comps.clone(),
            unit: u.clone(),
            suspect,
        });
        units_out.push(u);
        ui += 1;
    }
    plan.components_owned = plan.owned.iter().map(|u| u.components.len()).sum();

    // Absorption: empty slots join the unit whose component intersects the
    // empty slot's box the most (deterministic: most intersecting pixels, then
    // lowest unit index).
    for (si, comps) in slot_comps.iter().enumerate() {
        if !comps.is_empty() || unit_of_slot.contains_key(&si) {
            continue;
        }
        let bb = slots[si].bbox;
        let mut best: Option<(usize, usize)> = None;
        for (cui, ou) in plan.owned.iter().enumerate() {
            let mut inside = 0usize;
            for &c in &ou.components {
                for (x, y) in &comp_pixels[c] {
                    if *x as f64 >= bb[0]
                        && *x as f64 <= bb[2]
                        && *y as f64 >= bb[1]
                        && *y as f64 <= bb[3]
                    {
                        inside += 1;
                    }
                }
            }
            if inside > 0 && best.is_none_or(|(_, best_inside)| inside > best_inside) {
                best = Some((cui, inside));
            }
        }
        if let Some((cui, _)) = best {
            plan.owned[cui].slots.push(SlotRef {
                order: si,
                text: slots[si].text.clone(),
                symbol_id: slots[si].symbol_id.clone(),
                bbox: slots[si].bbox,
            });
            let text_all = plan.owned[cui].semantic_text();
            plan.owned[cui].unit.semantic_text = text_all;
        } else {
            // no ink attributable: the OCR symbol remains a text caller with no
            // visual marker — record and keep (its text is still transported by
            // the region-owner text layer in the pipeline).
            plan.notes.push(format!(
                "slot {} ({}): no source ink attributable; text retained via region owner",
                si, slots[si].symbol_id
            ));
        }
    }

    // Artwork: components owned by no slot and not absorbed
    for (li, pixels) in comp_pixels.iter().enumerate().skip(1) {
        if pixels.is_empty() || owner_of[li].is_some() {
            continue;
        }
        let u = make_artwork_unit(pixels);
        plan.artwork_units.push((u, vec![li]));
        plan.components_artwork += 1;
    }

    plan.suspect_units = plan.owned.iter().filter(|u| u.suspect).count();
    plan.notes.sort();
    let n_art = plan.components_artwork;
    (plan, (units_out, n_art))
}

/// true when the unit's component ink extends beyond the union of its symbol
/// boxes (expanded by `margin`) — i.e. the ink cannot be safely attributed to
/// the supplied text symbols (e.g. fused with a rule/stamp/barcode).
fn unit_ink_exceeds_slots(
    comp_pixels: &[Vec<(usize, usize)>],
    comps: &[usize],
    slot: &Slot,
    margin: f64,
) -> bool {
    let (mut ix0, mut iy0, mut ix1, mut iy1) = (usize::MAX, usize::MAX, 0usize, 0usize);
    for &c in comps {
        for (x, y) in &comp_pixels[c] {
            ix0 = ix0.min(*x);
            iy0 = iy0.min(*y);
            ix1 = ix1.max(*x + 1);
            iy1 = iy1.max(*y + 1);
        }
    }
    (ix0 as f64) < slot.bbox[0] - margin
        || (iy0 as f64) < slot.bbox[1] - margin
        || (ix1 as f64) > slot.bbox[2] + margin
        || (iy1 as f64) > slot.bbox[3] + margin
}

fn make_unit(mask_pixels: &[(usize, usize)], _page: &OcrPage, slot: &Slot, _si: usize) -> Unit {
    let x0 = mask_pixels.iter().map(|p| p.0).min().unwrap();
    let y0 = mask_pixels.iter().map(|p| p.1).min().unwrap();
    let x1 = mask_pixels.iter().map(|p| p.0).max().unwrap() + 1;
    let y1 = mask_pixels.iter().map(|p| p.1).max().unwrap() + 1;
    let cw = x1 - x0;
    let ch = y1 - y0;
    let mut mask = vec![false; cw * ch];
    for (x, y) in mask_pixels {
        mask[(y - y0) * cw + (x - x0)] = true;
    }
    Unit {
        shape_key: crate::units::mask_identity_key(&mask, cw, ch),
        span_id: slot.span_id.clone(),
        symbol_id: slot.symbol_id.clone(),
        semantic_text: slot.text.clone(),
        bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
        ocr_bbox_px: slot.bbox,
        crop_w: cw,
        crop_h: ch,
        mask,
        gray_samples: None,
        gray_halo: None,
    }
}

fn make_artwork_unit(pixels: &[(usize, usize)]) -> Unit {
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
    Unit {
        shape_key: crate::units::mask_identity_key(&mask, cw, ch),
        span_id: "unowned".to_string(),
        symbol_id: "artwork".to_string(),
        semantic_text: String::new(),
        bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
        ocr_bbox_px: [x0 as f64, y0 as f64, x1 as f64, y1 as f64],
        crop_w: cw,
        crop_h: ch,
        mask,
        gray_samples: None,
        gray_halo: None,
    }
}
