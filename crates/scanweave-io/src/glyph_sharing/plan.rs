//! Source-only frozen cover planning. No document-specific labels or IDs.
use super::{
    fit::register,
    group::{cover, Group, Member, Pair},
    hard_checks, hygiene, mse, quantile, weight_band, Field,
};
use std::collections::BTreeMap;
#[derive(Clone, Debug, serde::Serialize)]
pub struct Fit {
    pub member: usize,
    pub canonical: usize,
    pub error: f64,
    pub reasons: Vec<String>,
    pub parameters: [f64; 3],
}
#[derive(Debug)]
pub struct Plan {
    pub fits: Vec<Fit>,
    pub groups: Vec<Group>,
    pub floors: Vec<f64>,
    pub bands: Vec<i32>,
    pub hygiene: Vec<Vec<String>>,
}

/// Compute all frozen stages through cover grouping. Ownership must be checked
/// against raw source and default emission before these groups can be emitted.
pub fn plan(
    rows: &[Member],
    fields: &[Field],
    candidates: &[Option<Field>],
    multiplier: f64,
) -> Result<Plan, String> {
    if !matches!(multiplier, 1.5 | 2.0) {
        return Err("unsupported frozen operating point".into());
    }
    let n = rows.len();
    if fields.len() != n
        || candidates.len() != n
        || fields
            .iter()
            .any(|f| f.len() != 4096 || f.iter().any(|x| !x.is_finite()))
        || candidates
            .iter()
            .flatten()
            .any(|f| f.len() != 4096 || f.iter().any(|x| !x.is_finite()))
    {
        return Err("invalid sharing fields".into());
    }
    let mut labels: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
    for (i, row) in rows.iter().enumerate() {
        labels.entry(&row.label).or_default().push(i);
    }
    let bands: Vec<i32> = fields.iter().map(|f| weight_band(f)).collect();
    let mut fits = Vec::new();
    let mut by_member: Vec<Vec<usize>> = vec![Vec::new(); n];
    for i in 0..n {
        if i % 100 == 0 {
            eprintln!("scanweave: glyph sharing fitting {i}/{n}");
        }
        if fields[i].iter().sum::<f64>() <= 0. {
            continue;
        }
        let indices = &labels[rows[i].label.as_str()];
        let mut nearest: Vec<(f64, usize)> = indices
            .iter()
            .map(|&j| {
                (
                    if j == i {
                        f64::INFINITY
                    } else {
                        candidates[j]
                            .as_ref()
                            .map_or(f64::INFINITY, |c| mse(&fields[i], c))
                    },
                    j,
                )
            })
            .collect();
        nearest.sort_by(|a, b| a.0.total_cmp(&b.0).then(a.1.cmp(&b.1)));
        for &(distance, j) in nearest.iter().take(24.min(indices.len().saturating_sub(1))) {
            if !distance.is_finite() {
                continue;
            }
            let (p, aligned) = register(&fields[i], candidates[j].as_ref().unwrap());
            let error = mse(&fields[i], &aligned);
            let reasons = hard_checks(&fields[i], &aligned);
            by_member[i].push(fits.len());
            fits.push(Fit {
                member: i,
                canonical: j,
                error,
                reasons,
                parameters: p,
            });
        }
    }
    eprintln!("scanweave: glyph sharing source variation estimates");
    let mut original_floors = vec![None; n];
    for i in 0..n {
        let mut ordered = by_member[i].clone();
        ordered.sort_by(|&a, &b| {
            fits[a]
                .error
                .total_cmp(&fits[b].error)
                .then(fits[a].canonical.cmp(&fits[b].canonical))
        });
        let mut values = Vec::new();
        for index in ordered {
            let f = &fits[index];
            let j = f.canonical;
            if !f.reasons.is_empty() || rows[i].shape_key == rows[j].shape_key {
                continue;
            }
            let (_, aligned) = register(&fields[i], &fields[j]);
            if hard_checks(&fields[i], &aligned).is_empty() {
                values.push(mse(&fields[i], &aligned));
            }
            if values.len() >= 5 {
                break;
            }
        }
        if values.len() >= 2 {
            original_floors[i] = Some(quantile(&values, 0.85));
        }
    }
    let mut floors = vec![0.; n];
    for i in 0..n {
        if let Some(level) = original_floors[i] {
            floors[i] = level;
            continue;
        }
        let peers: Vec<f64> = labels[rows[i].label.as_str()]
            .iter()
            .filter(|&&j| bands[j] == bands[i] && rows[i].shape_key != rows[j].shape_key)
            .filter_map(|&j| original_floors[j])
            .collect();
        if !peers.is_empty() {
            floors[i] = quantile(&peers, 0.5);
            continue;
        }
        let available: Vec<usize> = labels[rows[i].label.as_str()]
            .iter()
            .copied()
            .filter(|&j| j != i && fields[j].iter().sum::<f64>() > 0.)
            .collect();
        let independent: Vec<usize> = available
            .iter()
            .copied()
            .filter(|&j| rows[i].shape_key != rows[j].shape_key)
            .collect();
        let pool = if independent.is_empty() {
            available
        } else {
            independent
        };
        let same: Vec<usize> = pool
            .iter()
            .copied()
            .filter(|&j| bands[i] == bands[j])
            .collect();
        let mut pool = if same.is_empty() { pool } else { same };
        pool.sort_by(|&a, &b| {
            mse(&fields[i], &fields[a])
                .total_cmp(&mse(&fields[i], &fields[b]))
                .then(a.cmp(&b))
        });
        let values: Vec<f64> = pool
            .iter()
            .take(5)
            .map(|&j| {
                let (_, aligned) = register(&fields[i], &fields[j]);
                mse(&fields[i], &aligned)
            })
            .collect();
        if values.is_empty() {
            return Err(format!("no source LOO witness for member {i}"));
        }
        floors[i] = quantile(&values, 0.85);
    }
    for i in 0..n {
        if let Some(c) = &candidates[i] {
            let (p, aligned) = register(&fields[i], c);
            fits.push(Fit {
                member: i,
                canonical: i,
                error: mse(&fields[i], &aligned),
                reasons: hard_checks(&fields[i], &aligned),
                parameters: p,
            });
        }
    }
    eprintln!("scanweave: glyph sharing canonical hygiene");
    let screens: Vec<Vec<String>> = (0..n)
        .map(|j| {
            if let Some(c) = &candidates[j] {
                let independent: Vec<&[f64]> = labels[rows[j].label.as_str()]
                    .iter()
                    .filter(|&&i| {
                        rows[i].shape_key != rows[j].shape_key && fields[i].iter().sum::<f64>() > 0.
                    })
                    .map(|&i| fields[i].as_slice())
                    .collect();
                hygiene(c, &independent)
            } else {
                vec!["no_trace".into()]
            }
        })
        .collect();
    let ranked: Vec<Member> = rows
        .iter()
        .enumerate()
        .map(|(i, r)| Member {
            label: r.label.clone(),
            shape_key: r.shape_key.clone(),
            band: bands[i],
        })
        .collect();
    let pairs: Vec<Pair> = fits
        .iter()
        .map(|f| Pair {
            member: f.member,
            canonical: f.canonical,
            normalized_error: f.error / floors[f.member].max(1e-6),
            safe: f.reasons.is_empty()
                && screens[f.canonical].is_empty()
                && bands[f.member] == bands[f.canonical],
        })
        .collect();
    let groups = cover(&ranked, &pairs, multiplier);
    Ok(Plan {
        fits,
        groups,
        floors,
        bands,
        hygiene: screens,
    })
}
