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

/// Group the plan's units into regions by line adjacency (sharing horizontal
/// overlap and vertical proximity within 1.5× median unit height) and assign
/// dispositions.
/// Regions follow the OCR's own reading order: one region per span that owns
/// units (plus any absorbed slots), in slot order. Proximity grouping would
/// scramble reading order (observed: a row crossing into the next line).
pub fn plan_regions(
    plan: &OwnershipPlan,
    protected: &[[f64; 4]],
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
            if intersects(&probe, &au.bbox_px) {
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
