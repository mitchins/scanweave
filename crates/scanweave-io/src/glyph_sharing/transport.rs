//! Full native cover sharing with aggregate per-document economy fallback.
use super::{
    font::{self, Instance},
    group::Member,
    ownership::{candidate_matrix, default_matrix, preflight},
    plan::{self, Fit},
    source::{fitted_bbox, Observation},
};
use crate::{
    glyphs::GlyphShape,
    page_pdf::{AssemblyStats, ImageEncodingOptions, PageParts, SharingResources},
};
use std::collections::{BTreeMap, BTreeSet};
#[derive(Debug, Clone, serde::Serialize)]
pub struct Decision {
    pub member: usize,
    pub page: usize,
    pub id: String,
    pub canonical: Option<usize>,
    pub accepted: bool,
    pub reasons: Vec<String>,
    pub fitted_transform: Option<[f64; 3]>,
    pub error: Option<f64>,
    pub noise_floor: f64,
    pub weight_band: i32,
}
#[derive(Debug, Clone, serde::Serialize)]
pub struct ZeroCreditGroup {
    pub canonical: usize,
    pub members: Vec<usize>,
    pub credited_retirements: usize,
    pub canonical_outline_bytes: usize,
    pub composite_stub_bytes: usize,
}
#[derive(Debug, Clone, serde::Serialize)]
pub struct SharingReport {
    pub pdfium: Option<super::ownership::PdfiumIdentity>,
    pub stage_seconds: BTreeMap<String, f64>,
    pub method: String,
    pub multiplier: f64,
    pub net_retirement_rule: bool,
    pub fallback: Option<String>,
    pub proposed_members: usize,
    pub substituted: usize,
    pub retired_outlines: usize,
    pub added_canonicals: usize,
    pub net_outlines_retired: isize,
    pub encoded_font_bytes_before: usize,
    pub encoded_font_bytes_after: usize,
    pub zero_credit_groups: Vec<ZeroCreditGroup>,
    pub decisions: Vec<Decision>,
    pub owned_exceptions: Vec<usize>,
}
pub struct Candidate {
    pub font: Vec<u8>,
    pub pdf: Vec<u8>,
    pub stats: AssemblyStats,
}

pub fn share(
    rows: &[Observation],
    pages: &[PageParts],
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    default_font: &[u8],
    options: ImageEncodingOptions,
    tonal: bool,
    multiplier: f64,
) -> Result<(Option<Candidate>, SharingReport), String> {
    let started = std::time::Instant::now();
    let mut stage_seconds = BTreeMap::new();
    let fields: Vec<_> = rows.iter().map(|r| r.field.clone()).collect();
    let candidates: Vec<_> = rows
        .iter()
        .map(|r| r.canonical.as_ref().map(|c| c.coverage.clone()))
        .collect();
    let members: Vec<Member> = rows
        .iter()
        .map(|r| Member {
            label: r.label.clone(),
            shape_key: r.shape_key.clone(),
            band: 0,
        })
        .collect();
    stage_seconds.insert("prepare_fields".into(), started.elapsed().as_secs_f64());
    let stage = std::time::Instant::now();
    let plan = plan::plan(&members, &fields, &candidates, multiplier)?;
    stage_seconds.insert("planning".into(), stage.elapsed().as_secs_f64());
    stage_seconds.extend(plan.stage_seconds.clone());
    let stage = std::time::Instant::now();
    drop(fields);
    drop(candidates);
    let fits: BTreeMap<(usize, usize), &Fit> = plan
        .fits
        .iter()
        .map(|f| ((f.member, f.canonical), f))
        .collect();
    let mut assignments = Vec::new();
    for g in &plan.groups {
        let canonical = rows[g.canonical]
            .canonical
            .as_ref()
            .ok_or("missing canonical")?;
        for &i in &g.members {
            let frame = rows[i].frame.as_ref().ok_or("missing source frame")?;
            let fit = fits[&(i, g.canonical)];
            assignments.push((
                i,
                g.canonical,
                fitted_bbox(frame, canonical, fit.parameters),
            ));
        }
    }
    eprintln!(
        "scanweave: glyph sharing ownership preflight on {} members",
        assignments.len()
    );
    stage_seconds.insert("assignments".into(), stage.elapsed().as_secs_f64());
    let stage = std::time::Instant::now();
    let (exceptions, pdfium) = if assignments.is_empty() {
        (BTreeSet::new(), None)
    } else {
        let (exceptions, identity) = preflight(rows, pages, shapes, default_font, &assignments)?;
        (exceptions, Some(identity))
    };
    stage_seconds.insert("owned_ink_preflight".into(), stage.elapsed().as_secs_f64());
    let stage = std::time::Instant::now();
    let mut surviving = BTreeMap::new();
    let mut groups = BTreeMap::new();
    for g in &plan.groups {
        let kept: Vec<usize> = g
            .members
            .iter()
            .copied()
            .filter(|i| !exceptions.contains(i))
            .collect();
        if exceptions.contains(&g.canonical) || kept.len() < 2 {
            continue;
        }
        for &i in &kept {
            surviving.insert(i, g.canonical);
        }
        groups.insert(g.canonical, kept);
    }
    let accepted_by_draw: BTreeMap<(usize, usize), usize> = surviving
        .keys()
        .map(|&i| ((rows[i].page, rows[i].occurrence), i))
        .collect();
    let mut decisions = Vec::new();
    for (i, r) in rows.iter().enumerate() {
        let accepted = surviving.contains_key(&i);
        let attempted = if let Some(&j) = surviving.get(&i) {
            Some(fits[&(i, j)])
        } else {
            plan.fits
                .iter()
                .filter(|f| f.member == i && f.canonical != i)
                .min_by(|a, b| {
                    a.reasons
                        .len()
                        .cmp(&b.reasons.len())
                        .then(a.error.total_cmp(&b.error))
                })
        };
        let mut reasons = if accepted {
            Vec::new()
        } else {
            attempted.map_or_else(
                || {
                    vec![r
                        .source_error
                        .clone()
                        .unwrap_or_else(|| "no_safe_owned_witness".into())]
                },
                |f| f.reasons.clone(),
            )
        };
        if !accepted {
            if let Some(f) = attempted {
                if !plan.hygiene[f.canonical].is_empty() {
                    reasons.push("canonical_hygiene".into());
                }
                if plan.bands[i] != plan.bands[f.canonical] {
                    reasons.push("stroke_weight_band".into());
                }
            }
            if exceptions.contains(&i) {
                reasons.push("unexplained_owned_ink".into());
            }
            if reasons.is_empty() {
                reasons.push("ranking_or_economy_exception".into());
            }
        }
        decisions.push(Decision {
            member: i,
            page: r.page,
            id: r.id.clone(),
            canonical: attempted.map(|f| f.canonical),
            accepted,
            reasons,
            fitted_transform: attempted.map(|f| f.parameters),
            error: attempted.map(|f| f.error),
            noise_floor: plan.floors[i],
            weight_band: plan.bands[i],
        });
    }
    let before = crate::serialization::deflate(default_font)?.len();
    stage_seconds.insert("decision_ledger".into(), stage.elapsed().as_secs_f64());
    let stage = std::time::Instant::now();
    let mut report = SharingReport {
        pdfium,
        stage_seconds,
        method: format!("cover-{multiplier:.1} frozen at research 5356255"),
        multiplier,
        net_retirement_rule: false,
        fallback: None,
        proposed_members: assignments.len(),
        substituted: surviving.len(),
        retired_outlines: 0,
        added_canonicals: groups.len(),
        net_outlines_retired: 0,
        encoded_font_bytes_before: before,
        encoded_font_bytes_after: before,
        zero_credit_groups: Vec::new(),
        decisions,
        owned_exceptions: exceptions.iter().copied().collect(),
    };
    if surviving.is_empty() {
        report.fallback = Some("no surviving cover groups".into());
        report
            .stage_seconds
            .insert("font_and_economy".into(), stage.elapsed().as_secs_f64());
        report
            .stage_seconds
            .insert("sharing_total".into(), started.elapsed().as_secs_f64());
        return Ok((None, report));
    }
    let mut required = BTreeSet::new();
    for (pi, p) in pages.iter().enumerate() {
        for (oi, o) in p.occurrences.iter().enumerate() {
            if !accepted_by_draw.contains_key(&(pi, oi)) {
                required.insert(o.0 as u16 + 1);
            }
        }
        for &cid in &p.owner_cids {
            if cid > 0 {
                required.insert(encodings[cid as usize - 1].0 as u16 + 1);
            }
        }
        for owner in &p.owners {
            for c in &owner.characters {
                required.insert(encodings[c.cid as usize - 1].0 as u16 + 1);
            }
        }
    }
    let mut primitives = BTreeMap::new();
    let mut instances = Vec::new();
    let mut instance_members = Vec::new();
    // Preserve research group/member order for deterministic stub first appearance.
    for g in &plan.groups {
        for &i in &g.members {
            let Some(&j) = surviving.get(&i) else {
                continue;
            };
            let r = &rows[i];
            let page = &pages[r.page];
            let o = &page.occurrences[r.occurrence];
            let canonical = rows[j].canonical.as_ref().ok_or("missing canonical")?;
            let bbox = fitted_bbox(
                rows[i].frame.as_ref().unwrap(),
                canonical,
                fits[&(i, j)].parameters,
            );
            let old = default_matrix(page, &shapes[o.0], o.2);
            let new = candidate_matrix(page, &canonical.shape, bbox);
            if old[0] == 0. || old[3] == 0. {
                return Err("singular default placement".into());
            }
            let t = [
                new[0] / old[0],
                0.,
                0.,
                new[3] / old[3],
                (new[4] - old[4]) / old[0] * 2048.,
                (new[5] - old[5]) / old[3] * 2048.,
            ];
            primitives
                .entry(j)
                .or_insert_with(|| canonical.shape.clone());
            instances.push(Instance {
                canonical: j,
                original_gid: o.0 as u16 + 1,
                transform: t,
            });
            instance_members.push(i);
        }
    }
    let shared = font::build(default_font, &required, &primitives, &instances, encodings)?;
    let after = crate::serialization::deflate(&shared.bytes)?.len();
    report.encoded_font_bytes_after = after;
    report.retired_outlines = shared.retired;
    report.net_outlines_retired = shared.retired as isize - primitives.len() as isize;
    let mut credit = BTreeMap::<usize, usize>::new();
    let mut old_users = BTreeMap::<u16, Vec<usize>>::new();
    for (i, r) in rows.iter().enumerate() {
        let o = &pages[r.page].occurrences[r.occurrence];
        old_users.entry(o.0 as u16 + 1).or_default().push(i);
    }
    for (&gid, users) in &old_users {
        if required.contains(&gid) || !users.iter().all(|i| surviving.contains_key(i)) {
            continue;
        }
        let mut count = BTreeMap::<usize, usize>::new();
        for i in users {
            *count.entry(surviving[i]).or_default() += 1;
        }
        if let Some((&j, _)) = count
            .iter()
            .min_by_key(|(j, count)| (std::cmp::Reverse(**count), **j))
        {
            *credit.entry(j).or_default() += 1;
        }
    }
    use write_fonts::read::{FontRef, TableProvider};
    use write_fonts::types::GlyphId;
    let ff = FontRef::new(&shared.bytes).map_err(|e| e.to_string())?;
    let loca = ff.loca(None).map_err(|e| e.to_string())?;
    let glyf = ff.glyf().map_err(|e| e.to_string())?;
    let glyph_bytes = |gid: u16| -> Result<usize, String> {
        let g = loca
            .get_glyf(GlyphId::new(gid as u32), &glyf)
            .map_err(|e| e.to_string())?;
        use write_fonts::from_obj::ToOwnedTable;
        let g: write_fonts::tables::glyf::Glyph = g.ok_or("empty shared glyph")?.to_owned_table();
        Ok(write_fonts::dump_table(&g)
            .map_err(|e| e.to_string())?
            .len())
    };
    for (&j, group) in &groups {
        if credit.get(&j).copied().unwrap_or(0) != 0 {
            continue;
        }
        let stubs: BTreeSet<u16> = instance_members
            .iter()
            .zip(&shared.instance_gids)
            .filter(|(i, _)| surviving[i] == j)
            .map(|(_, g)| *g)
            .collect();
        let mut stub_bytes = 0;
        for gid in stubs {
            stub_bytes += glyph_bytes(gid)?;
        }
        report.zero_credit_groups.push(ZeroCreditGroup {
            canonical: j,
            members: group.clone(),
            credited_retirements: 0,
            canonical_outline_bytes: glyph_bytes(shared.canonical_gids[&j])?,
            composite_stub_bytes: stub_bytes,
        });
    }
    if report.net_outlines_retired < 0 || after > before {
        report.fallback = Some(
            "aggregate economy: negative net outline retirement or encoded font growth".into(),
        );
        report.substituted = 0;
        for d in &mut report.decisions {
            if d.accepted {
                d.accepted = false;
                d.reasons = vec!["document_economy_fallback".into()];
            }
        }
        report
            .stage_seconds
            .insert("font_and_economy".into(), stage.elapsed().as_secs_f64());
        report
            .stage_seconds
            .insert("sharing_total".into(), started.elapsed().as_secs_f64());
        return Ok((None, report));
    }
    report
        .stage_seconds
        .insert("font_and_economy".into(), stage.elapsed().as_secs_f64());
    let stage = std::time::Instant::now();
    let base_map: Vec<u16> = std::iter::once(0)
        .chain(encodings.iter().map(|(shape, _)| {
            shared
                .old_gids
                .get(&(*shape as u16 + 1))
                .copied()
                .unwrap_or(0)
        }))
        .collect();
    let mut maps: Vec<BTreeMap<usize, u16>> = Vec::new();
    let mut variants: Vec<Vec<Option<usize>>> = pages
        .iter()
        .map(|p| vec![None; p.occurrences.len()])
        .collect();
    let mut draw_order: Vec<usize> = (0..instance_members.len()).collect();
    draw_order.sort_by_key(|&k| {
        let r = &rows[instance_members[k]];
        (r.page, r.occurrence)
    });
    for k in draw_order {
        let i = instance_members[k];
        let r = &rows[i];
        let cid = pages[r.page].occurrences[r.occurrence].1 as usize + 1;
        let gid = shared.instance_gids[k];
        let index = maps
            .iter()
            .position(|map| map.get(&cid).is_none_or(|&v| v == gid))
            .unwrap_or_else(|| {
                maps.push(BTreeMap::new());
                maps.len() - 1
            });
        maps[index].insert(cid, gid);
        variants[r.page][r.occurrence] = Some(index + 1);
    }
    let mut cid_maps = vec![base_map.iter().flat_map(|gid| gid.to_be_bytes()).collect()];
    for map in &maps {
        let mut values = vec![0u16; base_map.len()];
        for (&cid, &gid) in map {
            values[cid] = gid;
        }
        cid_maps.push(values.iter().flat_map(|gid| gid.to_be_bytes()).collect());
    }
    let resources = SharingResources {
        cid_maps,
        occurrence_variants: variants,
    };
    let (pdf, stats) = crate::page_pdf::assemble_document_with_sharing(
        pages,
        shapes,
        encodings,
        &shared.bytes,
        options,
        tonal,
        &resources,
    )?;
    report.stage_seconds.insert(
        "transport_and_assembly".into(),
        stage.elapsed().as_secs_f64(),
    );
    report
        .stage_seconds
        .insert("sharing_total".into(), started.elapsed().as_secs_f64());
    Ok((
        Some(Candidate {
            font: shared.bytes,
            pdf,
            stats,
        }),
        report,
    ))
}
