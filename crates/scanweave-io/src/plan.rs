//! Region planning: text units are grouped into candidate regions (runs of
//! adjacent symbols sharing a line); each region carries a disposition
//! (vector reconstruction or raster fallback) with an explicit reason.
//!
//! Non-text contact rule (M1-A): if a component claimed by no symbol
//! (artwork: rules, stamps, barcodes, signatures, illustrations) touches or
//! comes within `contact_margin_px` of a candidate region's ink, the region
//! is retained as raster — text is never separated from the non-text element
//! by force unless the separation is exact (disjoint bounding boxes).

use crate::ownership::OwnershipPlan;

pub const CONTACT_MARGIN_PX: f64 = 4.0;

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub enum RegionKind {
    Text,
    Mixed,   // text + adjacent non-text
    NonText, // unrecognized ink only
}

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub enum RegionDisposition {
    Vector,
    Raster { reason: FallbackReason },
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub enum FallbackReason {
    /// caller/preset/source protection polygon (SPEC §4.4): pixels preserved
    Protected,
    /// the traced outline reproduces the source ink below the policy's
    /// min_ink_iou, so the unit is not vectorizable under that policy
    FidelityBelowPolicy,
    ContactNonText,
    ImageTouchingText,
    OwnershipUnresolved,
    TextureOrPattern,
    UnsupportedContent,
}

#[derive(Debug, Clone)]
pub struct Region {
    pub id: usize,
    pub kind: RegionKind,
    pub units: Vec<usize>,
    pub artwork: Vec<usize>,
    pub bbox_px: [f64; 4],
    pub disposition: RegionDisposition,
}

impl Region {
    pub fn reason(&self) -> Option<FallbackReason> {
        match &self.disposition {
            RegionDisposition::Raster { reason } => Some(reason.clone()),
            _ => None,
        }
    }
}

fn union_bbox(units: &[usize], plan: &OwnershipPlan) -> [f64; 4] {
    let mut bb = [f64::MAX, f64::MAX, f64::MIN, f64::MIN];
    for &ui in units {
        let u = &plan.owned[ui];
        for i in 0..4 {
            let v = [u.unit.bbox_px[0], u.unit.bbox_px[1], u.unit.bbox_px[2], u.unit.bbox_px[3]][i];
            match i {
                0 | 1 => bb[i] = bb[i].min(v),
                _ => bb[i] = bb[i].max(v),
            }
        }
    }
    if bb[0] > bb[2] {
        bb = [0.0, 0.0, 0.0, 0.0];
    }
    bb
}

fn union(a: [f64; 4], b: [f64; 4]) -> [f64; 4] {
    [a[0].min(b[0]), a[1].min(b[1]), a[2].max(b[2]), a[3].max(b[3])]
}

fn expand(bbox: &[f64; 4], m: f64) -> [f64; 4] {
    [bbox[0] - m, bbox[1] - m, bbox[2] + m, bbox[3] + m]
}

fn intersects(a: &[f64; 4], b: &[f64; 4]) -> bool {
    a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3]
}

// Research-only Euclidean proximity of source mask pixels. Bounding-box checks
// remain the default; neither OCR labels nor pixels outside the owned mask count.
fn research_pixel_contact(a: &crate::units::Unit, b: &crate::units::Unit) -> bool {
    let margin = CONTACT_MARGIN_PX as isize;
    let ax = a.bbox_px[0] as isize;
    let ay = a.bbox_px[1] as isize;
    let bx = b.bbox_px[0] as isize;
    let by = b.bbox_px[1] as isize;
    for (i, on) in a.mask.iter().enumerate() {
        if !*on { continue; }
        let x = ax + (i % a.crop_w) as isize;
        let y = ay + (i / a.crop_w) as isize;
        if x < bx - margin || y < by - margin || x >= bx + b.crop_w as isize + margin || y >= by + b.crop_h as isize + margin { continue; }
        for dy in -margin..=margin {
            for dx in -margin..=margin {
                if dx * dx + dy * dy > margin * margin { continue; }
                let xx = x + dx - bx;
                let yy = y + dy - by;
                if xx >= 0 && yy >= 0 && xx < b.crop_w as isize && yy < b.crop_h as isize && b.mask[yy as usize * b.crop_w + xx as usize] { return true; }
            }
        }
    }
    false
}

fn research_border_component(b: [f64;4], w: u32, h: u32) -> bool {
    let edges=(b[0]<=0.0) as u8+(b[1]<=0.0) as u8+(b[2]>=w as f64) as u8+(b[3]>=h as f64) as u8;
    edges>=2 && b[2]-b[0]>=0.8*w as f64 && b[3]-b[1]>=0.8*h as f64
}

pub(crate) fn research_contacts(plan: &OwnershipPlan, group: &[usize]) -> serde_json::Value {
    let probe = expand(&union_bbox(group, plan), CONTACT_MARGIN_PX);
    let hits: Vec<_> = plan.artwork_units.iter().enumerate().filter_map(|(ai, (art, components))| {
        if !intersects(&probe, &art.bbox_px) { return None; }
        let count = art.mask.iter().filter(|p| **p).count();
        let pixel_contact = group.iter().any(|&ui| research_pixel_contact(&plan.owned[ui].unit, art));
        Some(serde_json::json!({"artwork_index":ai,"component_ids":components,"bbox":art.bbox_px,
            "pixels":count,"bbox_fill_ratio":count as f64 / (art.crop_w * art.crop_h).max(1) as f64,
            "pixel_contact":pixel_contact}))
    }).collect();
    let suspects: Vec<_> = group.iter().filter_map(|&ui| {let u=&plan.owned[ui]; u.suspect.then(|| serde_json::json!({
        "unit_index":ui,"symbol":u.unit.symbol_id,"ink_bbox":u.unit.bbox_px,
        "slots":u.slots.iter().map(|s| serde_json::json!({"symbol":s.symbol_id,"bbox":s.bbox})).collect::<Vec<_>>(),
        "reason":"component ink bbox exceeded the original owning OCR slot bbox by more than 6 pixels on at least one side"}))}).collect();
    serde_json::json!({"bbox_contacts":hits,"suspects":suspects})
}

/// Group the plan's units into regions by line adjacency (sharing horizontal
/// overlap and vertical proximity within 1.5× median unit height) and assign
/// dispositions.
/// Regions follow the OCR's own reading order: one region per span that owns
/// units (plus any absorbed slots), in slot order. Proximity grouping would
/// scramble reading order (observed: a row crossing into the next line).
pub fn plan_regions(plan: &OwnershipPlan, protected: &[[f64; 4]]) -> Vec<Region> {
    plan_regions_for_research(plan, protected, None)
}

pub(crate) fn plan_regions_for_research(
    plan: &OwnershipPlan, protected: &[[f64; 4]], page_size: Option<(u32,u32)>,
) -> Vec<Region> {
    let mut regions = Vec::new();
    let mut uid = 0usize;

    // span order = minimum slot order of each unit (the OCR reading order)
    let mut order: Vec<(usize, usize)> = plan
        .owned
        .iter()
        .enumerate()
        .map(|(ui, u)| (ui, u.slots.iter().map(|s| s.order).min().unwrap_or(usize::MAX)))
        .collect();
    order.sort_by_key(|p| p.1);

    // one region per span (units sharing a span_id, contiguous by span order)
    let mut grouped: Vec<Vec<usize>> = Vec::new();
    for (ui, _) in order {
        let sid = plan.owned[ui].unit.span_id.clone();
        if let Some(last) = grouped.last_mut() {
            if plan.owned[last[0]].unit.span_id == sid {
                last.push(ui);
                continue;
            }
        }
        grouped.push(vec![ui]);
    }

    for group in grouped {
        let mut region_bbox = union_bbox(&group, plan);
        let mut touching_artwork: Vec<usize> = Vec::new();
        let probe = expand(&region_bbox, CONTACT_MARGIN_PX);
        for (ai, (au, _)) in plan.artwork_units.iter().enumerate() {
            let border_refinement = std::env::var_os("SCANWEAVE_HVC41B_BORDER_CONTACT").is_some()
                && page_size.is_some_and(|(w,h)| research_border_component(au.bbox_px,w,h));
            if intersects(&probe, &au.bbox_px)
                && ((std::env::var_os("SCANWEAVE_HVC41_PIXEL_CONTACT").is_none() && !border_refinement)
                    || group.iter().any(|&ui| research_pixel_contact(&plan.owned[ui].unit, au))) {
                touching_artwork.push(ai);
            }
        }
        // SPEC §4.4: protection polygons have priority. Any unit whose expanded
        // box meets a protected polygon forces the region to raster, and the
        // region box grows to cover the protected pixels so the fallback patch
        // reproduces them exactly.
        let mut touching_protected: Vec<[f64; 4]> = Vec::new();
        for pb in protected {
            if intersects(&probe, pb) {
                touching_protected.push(*pb);
                region_bbox = union(region_bbox, *pb);
            }
        }
        let has_suspect = group.iter().any(|&ui| plan.owned[ui].suspect);
        let (kind, disposition) = if !touching_protected.is_empty() {
            (
                RegionKind::Mixed,
                RegionDisposition::Raster {
                    reason: FallbackReason::Protected,
                },
            )
        } else if !touching_artwork.is_empty() || has_suspect {
            (
                RegionKind::Mixed,
                RegionDisposition::Raster {
                    reason: FallbackReason::ContactNonText,
                },
            )
        } else {
            (RegionKind::Text, RegionDisposition::Vector)
        };
        regions.push(Region {
            id: uid,
            kind,
            units: group,
            artwork: touching_artwork,
            bbox_px: region_bbox,
            disposition,
        });
        uid += 1;
    }

    // artwork not touching any text region → its own non-text region
    let mut claimed_art: std::collections::HashSet<usize> = std::collections::HashSet::new();
    for r in &regions {
        claimed_art.extend(r.artwork.iter().copied());
    }
    for (ai, (au, _)) in plan.artwork_units.iter().enumerate() {
        if claimed_art.contains(&ai) {
            continue;
        }
        regions.push(Region {
            id: uid,
            kind: RegionKind::NonText,
            units: Vec::new(),
            artwork: vec![ai],
            bbox_px: au.bbox_px,
            disposition: RegionDisposition::Vector,
        });
        uid += 1;
    }

    regions
}

#[cfg(test)]
mod research_contact_tests {
    use super::{research_border_component, research_pixel_contact};
    use crate::units::Unit;

    fn one_pixel(x: f64, y: f64) -> Unit {
        Unit {
            shape_key: String::new(), span_id: String::new(), symbol_id: String::new(),
            semantic_text: String::new(), bbox_px: [x, y, x + 1.0, y + 1.0],
            ocr_bbox_px: [x, y, x + 1.0, y + 1.0], crop_w: 1, crop_h: 1,
            mask: vec![true], gray_samples: None, gray_halo: None,
        }
    }

    #[test]
    fn border_definition_requires_two_edges_and_large_area_in_both_dimensions() {
        assert!(research_border_component([0.0,0.0,100.0,100.0],100,100));
        assert!(!research_border_component([1.0,1.0,99.0,99.0],100,100));
        assert!(!research_border_component([0.0,0.0,100.0,79.0],100,100));
        assert!(!research_border_component([0.0,1.0,90.0,99.0],100,100));
    }

    #[test]
    fn proximity_uses_euclidean_distance_between_actual_pixels() {
        let origin = one_pixel(10.0, 10.0);
        assert!(research_pixel_contact(&origin, &one_pixel(14.0, 10.0)));
        assert!(research_pixel_contact(&origin, &one_pixel(13.0, 12.0)));
        assert!(!research_pixel_contact(&origin, &one_pixel(15.0, 10.0)));
        assert!(!research_pixel_contact(&origin, &one_pixel(13.0, 13.0)));
    }
}
