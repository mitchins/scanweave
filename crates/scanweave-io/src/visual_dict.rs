//! Document-scoped visual glyph dictionary.
//!
//! Clustering is visual only: OCR labels play no part. Candidate merges are
//! checked at the source-mask level and then revalidated against the same
//! traced outline fidelity gate used for any vectorized glyph.

use std::collections::BTreeMap;

use crate::ownership::OwnershipPlan;

pub fn apply(
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
            if !compatible(&descs[i], &descs[j], &plan.owned[i].unit.mask, &plan.owned[j].unit.mask, policy) {
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
        if members.len() < 2 || members.iter().map(|&i| plan.owned[i].unit.shape_key.clone()).collect::<std::collections::BTreeSet<_>>().len() < 2 {
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
        let traced = match crate::trace::trace_shape(&plan.owned[representative].unit, budget, units_per_px) {
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

fn compatible(desc_a: &(usize, usize, usize, usize, f64), desc_b: &(usize, usize, usize, usize, f64), ma: &[bool], mb: &[bool], policy: &crate::convert::Policy) -> bool {
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
