//! Deterministic cost-aware set cover in label/weight-band partitions.
use std::collections::{BTreeMap, BTreeSet};
#[derive(Clone, Debug)]
pub struct Member {
    pub label: String,
    pub shape_key: String,
    pub band: i32,
}
#[derive(Clone, Debug, PartialEq)]
pub struct Group {
    pub canonical: usize,
    pub members: Vec<usize>,
}
#[derive(Clone, Debug)]
pub struct Pair {
    pub member: usize,
    pub canonical: usize,
    pub normalized_error: f64,
    pub error: f64,
    pub safe: bool,
}
/// Missing pairs are untested, not interchangeable with rejected fits. A
/// canonical must pass its own admission. Tie breaks follow research index order.
pub fn cover(rows: &[Member], pairs: &[Pair], multiplier: f64, absolute_error_ceiling: Option<f64>) -> Vec<Group> {
    let mut partitions: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for (i, row) in rows.iter().enumerate() {
        partitions
            .entry(format!("{}:weight{}", row.label, row.band))
            .or_default()
            .push(i);
    }
    let valid: BTreeMap<(usize, usize), f64> = pairs
        .iter()
        .filter(|p| p.safe && p.normalized_error <= multiplier && absolute_error_ceiling.is_none_or(|ceiling| p.error <= ceiling))
        .map(|p| ((p.member, p.canonical), p.normalized_error))
        .collect();
    let mut groups = Vec::new();
    for indices in partitions.values() {
        let mut users: BTreeMap<&str, BTreeSet<usize>> = BTreeMap::new();
        for &i in indices {
            users.entry(&rows[i].shape_key).or_default().insert(i);
        }
        let mut remaining: BTreeSet<usize> = indices.iter().copied().collect();
        let mut remapped = BTreeSet::new();
        while !remaining.is_empty() {
            let mut best: Option<(isize, usize, f64, usize, Vec<usize>)> = None;
            for &j in &remaining {
                if !valid.contains_key(&(j, j)) {
                    continue;
                }
                let members: Vec<usize> = remaining
                    .iter()
                    .copied()
                    .filter(|&i| i == j || valid.contains_key(&(i, j)))
                    .collect();
                let union: BTreeSet<usize> = remapped
                    .iter()
                    .copied()
                    .chain(members.iter().copied())
                    .collect();
                let retired = users
                    .values()
                    .filter(|u| u.is_subset(&union) && !u.is_subset(&remapped))
                    .count();
                let sum: f64 = members
                    .iter()
                    .filter(|&&i| i != j)
                    .map(|&i| valid[&(i, j)])
                    .sum();
                let candidate = (
                    1 - retired as isize,
                    usize::MAX - members.len(),
                    sum,
                    j,
                    members,
                );
                let better = best.as_ref().is_none_or(|b| {
                    candidate
                        .0
                        .cmp(&b.0)
                        .then(candidate.1.cmp(&b.1))
                        .then(candidate.2.total_cmp(&b.2))
                        .then(candidate.3.cmp(&b.3))
                        .is_lt()
                });
                if better {
                    best = Some(candidate);
                }
            }
            let Some((_, _, _, j, members)) = best else {
                break;
            };
            for i in &members {
                remaining.remove(i);
            }
            if members.len() >= 2 {
                remapped.extend(members.iter().copied());
                groups.push(Group {
                    canonical: j,
                    members,
                });
            }
        }
    }
    groups
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn self_admission_and_label_partition() {
        let rows: Vec<Member> = [
            ("a", "one", 1),
            ("a", "two", 1),
            ("a", "three", 2),
            ("b", "four", 1),
        ]
        .into_iter()
        .map(|(a, b, c)| Member {
            label: a.into(),
            shape_key: b.into(),
            band: c,
        })
        .collect();
        let mut pairs = Vec::new();
        for i in 0..4 {
            for j in 0..4 {
                pairs.push(Pair {
                    member: i,
                    canonical: j,
                    normalized_error: 1.,
                    error: 0.1,
                    safe: j != 1,
                });
            }
        }
        assert_eq!(
            cover(&rows, &pairs, 2., None),
            vec![Group {
                canonical: 0,
                members: vec![0, 1]
            }]
        );
    }
    #[test]
    fn ceiling_excludes_low_normalized_high_absolute_error() {
        let rows: Vec<Member> = ["one", "two"].into_iter().map(|key| Member {
            label: "a".into(), shape_key: key.into(), band: 1,
        }).collect();
        let pairs: Vec<Pair> = (0..2).flat_map(|i| (0..2).map(move |j| Pair {
            member: i, canonical: j, normalized_error: 0.5,
            error: if i == j { 0.0 } else { 0.09 }, safe: true,
        })).collect();
        assert!(cover(&rows, &pairs, 2.0, Some(super::super::ABSOLUTE_FIT_ERROR_CEILING)).is_empty());
        assert_eq!(cover(&rows, &pairs, 2.0, None), vec![Group { canonical: 0, members: vec![0, 1] }]);
    }

}
