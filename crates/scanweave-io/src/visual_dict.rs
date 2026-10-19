//! Document-scoped visual glyph dictionary.
//!
//! Clustering is visual only: OCR labels play no part. Candidate merges are
//! checked at the source-mask level and then revalidated against the same
//! traced outline fidelity gate used for any vectorized glyph.

use std::collections::BTreeMap;

use crate::ownership::OwnershipPlan;

pub fn apply_legacy(
    plan: &mut OwnershipPlan,
    policy: &crate::convert::Policy,
    units_per_px: f64,
    budget: &crate::trace::Budget,
) {
    let n = plan.owned.len();
    if n < 2 {
        return;
    }

    // Gather per-unit topological descriptors.
    type Desc = (usize, usize, usize, usize, f64);
    let mut descs: Vec<Desc> = Vec::with_capacity(n);
    for u in &plan.owned {
        let m = &u.unit.mask;
        let (w, h) = (u.unit.crop_w, u.unit.crop_h);
        let (cc, holes) = topology(m, w, h);
        let ink = m.iter().filter(|b| **b).count();
        let density = ink as f64 / m.len().max(1) as f64;
        descs.push((w, h, cc, holes, density));
    }

    // Union-find over visually compatible units.
    let mut parent: Vec<usize> = (0..n).collect();
    #[allow(clippy::needless_range_loop)]
    fn find(parent: &mut [usize], x: usize) -> usize {
        let mut r = x;
        while parent[r] != r {
            parent[r] = parent[parent[r]];
            r = parent[r];
        }
        r
    }
    for i in 0..n {
        for j in (i + 1)..n {
            if !compatible(
                &descs[i],
                &descs[j],
                &plan.owned[i].unit.mask,
                &plan.owned[j].unit.mask,
                policy,
            ) {
                continue;
            }
            let (ri, rj) = (find(&mut parent, i), find(&mut parent, j));
            if ri != rj {
                parent[ri] = rj;
            }
        }
    }

    // Group indices by union-find root.
    let mut groups: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for i in 0..n {
        groups.entry(find(&mut parent, i)).or_default().push(i);
    }

    // Validate each multi-unit group before remapping.
    for (_root, members) in groups {
        if members.len() < 2
            || members
                .iter()
                .map(|&i| plan.owned[i].unit.shape_key.clone())
                .collect::<std::collections::BTreeSet<_>>()
                .len()
                < 2
        {
            continue;
        }
        // representative = highest minimum mask-IoU to peers
        let mut representative = members[0];
        let mut best_score = f64::MIN;
        for &i in &members {
            let min_iou = members
                .iter()
                .filter(|&&j| j != i)
                .map(|&j| mask_iou(&plan.owned[i].unit.mask, &plan.owned[j].unit.mask))
                .fold(f64::MAX, f64::min);
            if min_iou >= best_score {
                best_score = min_iou;
                representative = i;
            }
        }

        // Trace the representative; if it fails, do not merge.
        let traced =
            match crate::trace::trace_shape(&plan.owned[representative].unit, budget, units_per_px)
            {
                Ok(t) => t,
                Err(_) => continue,
            };
        let glyphs = match crate::glyphs::build_glyph_shapes(&[traced], units_per_px, budget) {
            Ok(mut g) if !g.is_empty() => g.swap_remove(0),
            _ => continue,
        };

        // Revalidate every member through the same fidelity gate.
        let mut acceptable = true;
        for &m in &members {
            let u = &plan.owned[m].unit;
            let accepted_min = policy.min_ink_iou.max(0.98);
            if crate::convert::glyph_ink_iou(&glyphs, u.crop_w, u.crop_h, &u.mask) < accepted_min {
                acceptable = false;
                break;
            }
        }
        if !acceptable {
            continue;
        }

        let new_key = plan.owned[representative].unit.shape_key.clone();
        for &m in &members {
            plan.owned[m].unit.shape_key = new_key.clone();
        }
    }
}

fn compatible(
    desc_a: &(usize, usize, usize, usize, f64),
    desc_b: &(usize, usize, usize, usize, f64),
    ma: &[bool],
    mb: &[bool],
    policy: &crate::convert::Policy,
) -> bool {
    let (wa, ha, ca, ha_h, da) = *desc_a;
    let (wb, hb, cb, hb_h, db) = *desc_b;
    if wa == 0 || wb == 0 || wa != wb || ha != hb {
        return false;
    }
    if ca != cb || ha_h != hb_h {
        return false;
    }
    if (da - db).abs() > 0.03 {
        return false;
    }
    if mask_iou(ma, mb) < 0.96 {
        return false;
    }
    let _ = policy;
    true
}

fn topology(mask: &[bool], w: usize, h: usize) -> (usize, usize) {
    // foreground components and holes (background components not touching border)
    let mut grid = vec![0u8; w * h];
    for (i, b) in mask.iter().enumerate() {
        grid[i] = if *b { 1 } else { 0 };
    }
    let fg = count_components(grid.as_slice(), w, h, 1);
    let holes = count_holes(grid.as_slice(), w, h);
    (fg, holes)
}

fn count_components(grid: &[u8], w: usize, h: usize, target: u8) -> usize {
    let mut seen = vec![false; grid.len()];
    let mut comps = 0usize;
    for idx in 0..grid.len() {
        if grid[idx] != target || seen[idx] {
            continue;
        }
        comps += 1;
        let mut stack = vec![idx];
        seen[idx] = true;
        while let Some(i) = stack.pop() {
            let (x, y) = (i % w, i / w);
            for dy in -1i32..=1 {
                for dx in -1i32..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let nx = x as i32 + dx;
                    let ny = y as i32 + dy;
                    if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                        continue;
                    }
                    let j = ny as usize * w + nx as usize;
                    if grid[j] == target && !seen[j] {
                        seen[j] = true;
                        stack.push(j);
                    }
                }
            }
        }
    }
    comps
}

fn count_holes(grid: &[u8], w: usize, h: usize) -> usize {
    let mut seen = vec![false; grid.len()];
    let mut holes = 0usize;
    for idx in 0..grid.len() {
        if grid[idx] != 0 || seen[idx] {
            continue;
        }
        // flood; if touches border then not a hole
        let mut stack = vec![idx];
        seen[idx] = true;
        let mut touches_border = false;
        while let Some(i) = stack.pop() {
            let (x, y) = (i % w, i / w);
            if x == 0 || y == 0 || x + 1 == w || y + 1 == h {
                touches_border = true;
            }
            for dy in -1i32..=1 {
                for dx in -1i32..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let nx = x as i32 + dx;
                    let ny = y as i32 + dy;
                    if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                        continue;
                    }
                    let j = ny as usize * w + nx as usize;
                    if grid[j] == 0 && !seen[j] {
                        seen[j] = true;
                        stack.push(j);
                    }
                }
            }
        }
        if !touches_border {
            holes += 1;
        }
    }
    holes
}

fn mask_iou(a: &[bool], b: &[bool]) -> f64 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let mut inter = 0usize;
    let mut union = 0usize;
    for i in 0..a.len() {
        if a[i] || b[i] {
            union += 1;
        }
        if a[i] && b[i] {
            inter += 1;
        }
    }
    if union == 0 {
        0.0
    } else {
        inter as f64 / union as f64
    }
}

// M1-D reconstruction records keep observations, reusable prototypes, and
// page occurrences separate. The OCR hypothesis only narrows comparisons.
#[derive(Debug, Clone, serde::Serialize, Default)]
pub struct Reconstruction {
    pub observations: Vec<GlyphObservation>,
    pub prototypes: Vec<GlyphPrototype>,
    pub occurrences: Vec<GlyphOccurrence>,
    pub restoration_qualified: bool,
    pub canonical_geometry: Vec<CanonicalGeometry>,
    #[serde(skip)]
    pub prototype_units: BTreeMap<String, crate::units::Unit>,
    #[serde(skip)]
    pub repaired_symbols: std::collections::BTreeSet<String>,
    #[serde(skip)]
    pub reused_symbols: std::collections::BTreeSet<String>,
    #[serde(skip)]
    pub rejected_symbols: std::collections::BTreeSet<String>,
}

/// Auditable pre-trace mask and actual emitted font path in their construction frame.
#[derive(Debug, Clone, serde::Serialize)]
pub struct CanonicalGeometry {
    pub prototype_id: String,
    pub witness_symbol_id: String,
    pub witness_bbox_px: [f64; 4],
    pub width: usize,
    pub height: usize,
    pub mask: Vec<bool>,
    pub grayscale: Option<Vec<u8>>,
    pub path_svg: String,
    pub anchor_bbox_fu: [f64; 4],
    pub ink_span_fu: [f64; 2],
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GlyphObservation {
    pub symbol_id: String,
    pub text_hypothesis: String,
    pub shape_key: String,
    pub bbox_px: [f64; 4],
    pub width: usize,
    pub height: usize,
    pub ink_pixels: usize,
    pub components: usize,
    pub holes: usize,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GlyphPrototype {
    pub prototype_id: String,
    pub representative_symbol_id: String,
    pub members: Vec<String>,
    pub outline_threshold_luma: u8,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GlyphOccurrence {
    pub symbol_id: String,
    pub text: String,
    pub source_shape_key: String,
    pub prototype_id: Option<String>,
    pub similarity: Option<f64>,
    pub source_mask_iou: Option<f64>,
    pub replacement_bbox_px: Option<[f64; 4]>,
    pub prototype_trace_iou: Option<f64>,
    pub repaired: bool,
    pub reused: bool,
    pub restoration_evidence_passed: bool,
    pub decision: String,
}

#[derive(Debug, Clone)]
struct ShapeEvidence {
    aspect: f64,
    density: f64,
    components: usize,
    holes: usize,
}

/// Build a per-page dictionary and map damaged occurrences to an observed
/// representative only when a coherent donor cohort supports the same shape.
/// Prototypes are returned independently so the tracing caller always traces
/// the selected donor, even when the damaged occurrence appears first.
pub fn reconstruct(
    plan: &mut crate::ownership::OwnershipPlan,
    policy: &crate::convert::Policy,
    rgb: &[u8],
    page_w: u32,
    page_h: u32,
) -> Reconstruction {
    use std::collections::BTreeMap;
    let mut out = Reconstruction::default();
    let n = plan.owned.len();
    if n == 0 || policy.profile != "clearscan" || policy.glyph_dictionary != "visual" {
        return out;
    }
    let evidence: Vec<ShapeEvidence> = plan
        .owned
        .iter()
        .map(|owned| {
            let u = &owned.unit;
            let (components, holes) = mask_topology(&u.mask, u.crop_w, u.crop_h);
            ShapeEvidence {
                aspect: u.crop_w as f64 / u.crop_h.max(1) as f64,
                density: u.mask.iter().filter(|b| **b).count() as f64 / u.mask.len().max(1) as f64,
                components,
                holes,
            }
        })
        .collect();
    out.observations = plan
        .owned
        .iter()
        .enumerate()
        .map(|(i, owned)| {
            let u = &owned.unit;
            GlyphObservation {
                symbol_id: u.symbol_id.clone(),
                text_hypothesis: u.semantic_text.clone(),
                shape_key: u.shape_key.clone(),
                bbox_px: u.bbox_px,
                width: u.crop_w,
                height: u.crop_h,
                ink_pixels: u.mask.iter().filter(|b| **b).count(),
                components: evidence[i].components,
                holes: evidence[i].holes,
            }
        })
        .collect();

    // A first-pass cohort requires direct pairwise similarity to its medoid;
    // there is no similarity-chain union. OCR labels only bound candidate work.
    let mut buckets: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for (i, owned) in plan.owned.iter().enumerate() {
        let e = &evidence[i];
        let key = format!(
            "{}:{}:{}",
            owned.unit.semantic_text,
            (e.aspect * 8.0).round() as i32,
            (e.density * 12.0).round() as i32
        );
        buckets.entry(key).or_default().push(i);
    }
    let mut cohorts: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for bucket in buckets.values() {
        let candidates: Vec<usize> = bucket.iter().copied().take(64).collect();
        for &seed in &candidates {
            let mut members: Vec<usize> = candidates
                .iter()
                .copied()
                .filter(|&other| {
                    other != seed
                        && style_compatible(&evidence[seed], &evidence[other])
                        && normalized_iou(&plan.owned[seed].unit, &plan.owned[other].unit) >= 0.78
                })
                .collect();
            members.push(seed);
            if members.len() < 3 {
                continue;
            }
            let mut rep = seed;
            let mut best = f64::MIN;
            for &candidate in &members {
                let avg = members
                    .iter()
                    .copied()
                    .filter(|&j| j != candidate)
                    .map(|j| normalized_iou(&plan.owned[candidate].unit, &plan.owned[j].unit))
                    .sum::<f64>()
                    / (members.len() - 1) as f64;
                // Choose the most central observed sample. Density is used to
                // reject damaged outliers above, never as a proxy for quality.
                let quality = avg;
                if quality > best {
                    best = quality;
                    rep = candidate;
                }
            }
            let replace = cohorts
                .get(&rep)
                .map(|old| members.len() > old.len())
                .unwrap_or(true);
            if replace {
                members.sort_unstable();
                members.dedup();
                cohorts.insert(rep, members);
            }
        }
    }
    let mut unique_cohorts: BTreeMap<Vec<usize>, usize> = BTreeMap::new();
    for members in cohorts.values() {
        let mut canonical = members.clone();
        canonical.sort_unstable();
        canonical.dedup();
        let mut densities: Vec<f64> = canonical.iter().map(|&i| evidence[i].density).collect();
        densities.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let median_density = densities[densities.len() / 2];
        // Damaged outliers may help classify a target, but do not count as
        // donor evidence for the reusable prototype.
        canonical.retain(|&i| evidence[i].density >= median_density * 0.955);
        if canonical.len() < 3 {
            continue;
        }
        if unique_cohorts.contains_key(&canonical) {
            continue;
        }
        let mut representative = canonical[0];
        let mut best_quality = f64::MIN;
        for &candidate in &canonical {
            let mean = canonical
                .iter()
                .copied()
                .filter(|&j| j != candidate)
                .map(|j| normalized_iou(&plan.owned[candidate].unit, &plan.owned[j].unit))
                .sum::<f64>()
                / (canonical.len() - 1).max(1) as f64;
            let quality = mean;
            if quality > best_quality {
                best_quality = quality;
                representative = candidate;
            }
        }
        // Keep the observed medoid selected above for ClearScan as well. A
        // maximum-coverage impression can contain more ink because of blur,
        // bleed or a neighboring mark; evidence support alone is not shape
        // quality. Every selected outline remains traceable to one observation.
        unique_cohorts.insert(canonical, representative);
    }
    let cohorts: BTreeMap<usize, Vec<usize>> = unique_cohorts
        .into_iter()
        .map(|(members, rep)| (rep, members))
        .collect();
    for (&rep, members) in &cohorts {
        let unit = &plan.owned[rep].unit;
        let mut prototype_unit = unit.clone();
        let threshold = if unit.symbol_id.starts_with("__doc_donor:") {
            0
        } else {
            refine_observed_mask(&mut prototype_unit, rgb, page_w, page_h)
        };
        out.prototype_units
            .insert(unit.shape_key.clone(), prototype_unit);
        out.prototypes.push(GlyphPrototype {
            prototype_id: format!("prototype:{}", unit.shape_key),
            representative_symbol_id: unit.symbol_id.clone(),
            members: members
                .iter()
                .map(|&i| plan.owned[i].unit.symbol_id.clone())
                .collect(),
            outline_threshold_luma: threshold,
        });
    }

    for i in 0..n {
        let u = &plan.owned[i].unit;
        let source_key = u.shape_key.clone();
        let target_ocr_bbox = u.ocr_bbox_px;
        let mut best: Option<(usize, f64)> = None;
        for (&rep, members) in &cohorts {
            if rep == i
                || u.semantic_text != plan.owned[rep].unit.semantic_text
                || !style_compatible(&evidence[i], &evidence[rep])
            {
                continue;
            }
            let min_donor_density = members
                .iter()
                .map(|&m| evidence[m].density)
                .fold(f64::INFINITY, f64::min);
            // ClearScan canonicalizes healthy and damaged observations. The
            // faithful profile retains its source-preserving donor behavior.
            if policy.profile != "clearscan" && evidence[i].density >= min_donor_density - 0.01 {
                continue;
            }
            let score = normalized_iou(u, &plan.owned[rep].unit);
            let score_ok = if policy.profile == "clearscan" {
                score >= 0.78
            } else {
                (0.62..0.94).contains(&score)
            };
            if members.len() >= 3 && score_ok && best.map(|(_, b)| score > b).unwrap_or(true) {
                best = Some((rep, score));
            }
        }
        let mut record = GlyphOccurrence {
            symbol_id: u.symbol_id.clone(),
            text: u.semantic_text.clone(),
            source_shape_key: source_key,
            prototype_id: None,
            similarity: None,
            source_mask_iou: None,
            replacement_bbox_px: None,
            prototype_trace_iou: None,
            repaired: false,
            reused: false,
            restoration_evidence_passed: false,
            decision: "no_supported_donor".into(),
        };
        if let Some((rep, score)) = best {
            let min_donor_density = cohorts
                .get(&rep)
                .into_iter()
                .flatten()
                .map(|&m| evidence[m].density)
                .fold(f64::INFINITY, f64::min);
            let mut donor = plan.owned[rep].unit.clone();
            let donor_key = donor.shape_key.clone();
            if !donor.symbol_id.starts_with("__doc_donor:") {
                let _threshold = refine_observed_mask(&mut donor, rgb, page_w, page_h);
            }
            let sid = u.symbol_id.clone();
            record.restoration_evidence_passed = if policy.profile == "clearscan" {
                cohorts.get(&rep).is_some_and(|members| members.len() >= 3) && score >= 0.78
            } else {
                restoration_gate(score, cohorts.get(&rep).map(Vec::len).unwrap_or(0))
            };
            record.similarity = Some(score);
            if record.restoration_evidence_passed {
                record.replacement_bbox_px = Some(infer_replacement_bbox(
                    u.ocr_bbox_px,
                    cohorts.get(&rep).map(Vec::as_slice).unwrap_or(&[]),
                    &plan.owned,
                ));
                plan.owned[i].unit.shape_key = donor_key.clone();
                out.prototype_units.insert(donor_key.clone(), donor);
                record.prototype_id = Some(format!("prototype:{donor_key}"));
                let source_is_damaged = evidence[i].density < min_donor_density - 0.01;
                if source_is_damaged {
                    out.repaired_symbols.insert(sid);
                    record.repaired = true;
                    record.decision = if policy.profile == "clearscan" {
                        "canonical_repair_from_document_witnesses".into()
                    } else {
                        "repaired_from_document_donors".into()
                    };
                } else {
                    out.reused_symbols.insert(sid);
                    record.reused = true;
                    record.decision = "canonical_reuse_of_document_outline".into();
                }
            } else {
                record.decision = "rejected_restoration_gate".into();
                out.rejected_symbols.insert(u.symbol_id.clone());
            }
        } else if !u.symbol_id.starts_with("__doc_donor:") {
            let reusable = cohorts
                .iter()
                .filter_map(|(&rep, members)| {
                    if rep == i
                        || members.len() < 3
                        || u.semantic_text != plan.owned[rep].unit.semantic_text
                        || !style_compatible(&evidence[i], &evidence[rep])
                    {
                        return None;
                    }
                    let score = normalized_iou(u, &plan.owned[rep].unit);
                    reuse_gate(score, members.len()).then_some((rep, score))
                })
                .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
            if let Some((rep, score)) = reusable {
                let sid = u.symbol_id.clone();
                let donor_members = cohorts.get(&rep).map(Vec::as_slice).unwrap_or(&[]);
                let mut donor = plan.owned[rep].unit.clone();
                let donor_key = donor.shape_key.clone();
                if !donor.symbol_id.starts_with("__doc_donor:") {
                    let _threshold = refine_observed_mask(&mut donor, rgb, page_w, page_h);
                }
                plan.owned[i].unit.shape_key = donor_key.clone();
                out.prototype_units.insert(donor_key.clone(), donor);
                out.reused_symbols.insert(sid);
                record.prototype_id = Some(format!("prototype:{donor_key}"));
                record.similarity = Some(score);
                record.replacement_bbox_px = Some(infer_replacement_bbox(
                    target_ocr_bbox,
                    donor_members,
                    &plan.owned,
                ));
                record.reused = true;
                record.restoration_evidence_passed = true;
                record.decision = "shared_document_prototype".into();
            }
        }
        out.occurrences.push(record);
    }
    out.restoration_qualified = out
        .occurrences
        .iter()
        .filter(|o| o.repaired || o.reused)
        .all(|o| o.restoration_evidence_passed);
    out
}

/// Estimate expected ink extents from document-local OCR-box padding observed
/// on intact donors. This keeps a missing outer stroke from shrinking the
/// replacement's PDF placement box while preserving its original OCR location.
fn infer_replacement_bbox(
    target_ocr: [f64; 4],
    donors: &[usize],
    owned: &[crate::ownership::OwnedUnit],
) -> [f64; 4] {
    let mut pads: [Vec<f64>; 4] = std::array::from_fn(|_| Vec::new());
    for &index in donors {
        let u = &owned[index].unit;
        let ink = u.bbox_px;
        let ocr = u.ocr_bbox_px;
        let values = [
            ink[0] - ocr[0],
            ink[1] - ocr[1],
            ocr[2] - ink[2],
            ocr[3] - ink[3],
        ];
        for (at, value) in values.into_iter().enumerate() {
            if value.is_finite() && value >= 0.0 {
                pads[at].push(value);
            }
        }
    }
    let med = |values: &mut Vec<f64>| {
        if values.is_empty() {
            return 0.0;
        }
        values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        values[values.len() / 2]
    };
    [
        target_ocr[0] + med(&mut pads[0]),
        target_ocr[1] + med(&mut pads[1]),
        target_ocr[2] - med(&mut pads[2]),
        target_ocr[3] - med(&mut pads[3]),
    ]
}

/// ClearScan's restoration decision is separate from faithful source-mask
/// preservation. It requires bounded visual fit and at least three independent
/// observations in a coherent same-label/style donor cohort.
fn restoration_gate(similarity: f64, donor_support: usize) -> bool {
    const MIN_SIMILARITY: f64 = 0.62;
    // When the target is already this close to its donors, a raster fallback
    // is safer than repainting it: modest tracing/render differences can be
    // larger than the defect being repaired.
    const MAX_SIMILARITY_FOR_REPAIR: f64 = 0.90;
    const MIN_DONORS: usize = 3;
    donor_support >= MIN_DONORS && (MIN_SIMILARITY..MAX_SIMILARITY_FOR_REPAIR).contains(&similarity)
}

/// Reuse an intact document prototype only for a close visual match backed by
/// a real cohort. The stricter threshold protects normal text from broad
/// within-character deformation while still combining repeated sampling.
fn reuse_gate(similarity: f64, donor_support: usize) -> bool {
    donor_support >= 3 && similarity >= 0.96
}

/// Refine a selected observed prototype from the original grayscale samples.
/// The source mask threshold is intentionally more permissive for ownership;
/// Otsu's local crop threshold removes antialias fringe before outline tracing.
fn refine_observed_mask(unit: &mut crate::units::Unit, rgb: &[u8], page_w: u32, page_h: u32) -> u8 {
    unit.retain_grayscale(rgb, page_w, page_h);
    let (pw, ph) = (page_w as usize, page_h as usize);
    if rgb.len() != pw * ph * 3 || unit.mask.len() != unit.crop_w * unit.crop_h {
        return 128;
    }
    let x0 = unit.bbox_px[0].floor().max(0.0) as usize;
    let y0 = unit.bbox_px[1].floor().max(0.0) as usize;
    let mut gray = Vec::with_capacity(unit.mask.len());
    let mut hist = [0u64; 256];
    for y in 0..unit.crop_h {
        for x in 0..unit.crop_w {
            let px = (y0 + y).min(ph.saturating_sub(1)) * pw + (x0 + x).min(pw.saturating_sub(1));
            let at = px * 3;
            let luma = (0.2126 * rgb[at] as f64
                + 0.7152 * rgb[at + 1] as f64
                + 0.0722 * rgb[at + 2] as f64)
                .round() as u8;
            gray.push(luma);
            hist[luma as usize] += 1;
        }
    }
    let total = gray.len() as f64;
    let total_mean = hist
        .iter()
        .enumerate()
        .map(|(i, n)| i as f64 * *n as f64)
        .sum::<f64>();
    let (mut weight_b, mut sum_b, mut best_var, mut threshold) = (0.0, 0.0, -1.0, 128u8);
    for (t, n) in hist.iter().enumerate() {
        weight_b += *n as f64;
        sum_b += t as f64 * *n as f64;
        if weight_b == 0.0 {
            continue;
        }
        let weight_f = total - weight_b;
        if weight_f == 0.0 {
            break;
        }
        let mean_b = sum_b / weight_b;
        let mean_f = (total_mean - sum_b) / weight_f;
        let variance = weight_b * weight_f * (mean_b - mean_f).powi(2);
        if variance > best_var {
            best_var = variance;
            threshold = t as u8;
        }
    }
    // Otsu separates high-confidence ink from paper and antialias samples for
    // this selected observed prototype.
    for (i, value) in gray.into_iter().enumerate() {
        unit.mask[i] = value <= threshold;
    }
    threshold
}

fn style_compatible(a: &ShapeEvidence, b: &ShapeEvidence) -> bool {
    let aspect_delta = (a.aspect - b.aspect).abs() / a.aspect.max(b.aspect).max(0.01);
    let density_ratio = a.density.max(b.density) / a.density.min(b.density).max(0.005);
    aspect_delta <= 0.28
        && density_ratio <= 1.8
        && a.components == b.components
        && a.holes.abs_diff(b.holes) <= 1
}

fn normalized_iou(a: &crate::units::Unit, b: &crate::units::Unit) -> f64 {
    const SIDE: usize = 32;
    fn normalize(u: &crate::units::Unit) -> Vec<bool> {
        let mut out = vec![false; SIDE * SIDE];
        if u.crop_w == 0 || u.crop_h == 0 || u.mask.len() != u.crop_w * u.crop_h {
            return out;
        }
        let scale = (SIDE as f64 - 4.0) / u.crop_w.max(u.crop_h) as f64;
        let (w, h) = (
            (u.crop_w as f64 * scale).round().max(1.0) as usize,
            (u.crop_h as f64 * scale).round().max(1.0) as usize,
        );
        let (ox, oy) = ((SIDE - w.min(SIDE)) / 2, (SIDE - h.min(SIDE)) / 2);
        for y in 0..h.min(SIDE) {
            for x in 0..w.min(SIDE) {
                let sx = ((x as f64 + 0.5) * u.crop_w as f64 / w as f64).floor() as usize;
                let sy = ((y as f64 + 0.5) * u.crop_h as f64 / h as f64).floor() as usize;
                if u.mask[sy.min(u.crop_h - 1) * u.crop_w + sx.min(u.crop_w - 1)] {
                    out[(oy + y) * SIDE + ox + x] = true;
                }
            }
        }
        out
    }
    let (am, bm) = (normalize(a), normalize(b));
    let (mut intersection, mut union) = (0usize, 0usize);
    for (x, y) in am.iter().zip(bm) {
        if *x || y {
            union += 1;
        }
        if *x && y {
            intersection += 1;
        }
    }
    if union == 0 {
        0.0
    } else {
        intersection as f64 / union as f64
    }
}

fn mask_topology(mask: &[bool], w: usize, h: usize) -> (usize, usize) {
    if w == 0 || h == 0 || mask.len() != w * h {
        return (0, 0);
    }
    let mut seen = vec![false; mask.len()];
    let mut components = 0;
    for start in 0..mask.len() {
        if !mask[start] || seen[start] {
            continue;
        }
        components += 1;
        let mut stack = vec![start];
        seen[start] = true;
        while let Some(i) = stack.pop() {
            let (x, y) = (i % w, i / w);
            for dy in -1isize..=1 {
                for dx in -1isize..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let (nx, ny) = (x as isize + dx, y as isize + dy);
                    if nx < 0 || ny < 0 || nx >= w as isize || ny >= h as isize {
                        continue;
                    }
                    let j = ny as usize * w + nx as usize;
                    if mask[j] && !seen[j] {
                        seen[j] = true;
                        stack.push(j);
                    }
                }
            }
        }
    }
    let mut holes = 0;
    seen.fill(false);
    for start in 0..mask.len() {
        if mask[start] || seen[start] {
            continue;
        }
        let mut stack = vec![start];
        seen[start] = true;
        let mut border = false;
        while let Some(i) = stack.pop() {
            let (x, y) = (i % w, i / w);
            border |= x == 0 || y == 0 || x + 1 == w || y + 1 == h;
            for dy in -1isize..=1 {
                for dx in -1isize..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let (nx, ny) = (x as isize + dx, y as isize + dy);
                    if nx < 0 || ny < 0 || nx >= w as isize || ny >= h as isize {
                        continue;
                    }
                    let j = ny as usize * w + nx as usize;
                    if !mask[j] && !seen[j] {
                        seen[j] = true;
                        stack.push(j);
                    }
                }
            }
        }
        if !border {
            holes += 1;
        }
    }
    (components, holes)
}
