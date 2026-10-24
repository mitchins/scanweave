//! Native TrueType composite emission with original instance advance metrics.
use crate::glyphs::GlyphShape;
use std::collections::{BTreeMap, BTreeSet};
use write_fonts::read::{FontRef, TableProvider};
use write_fonts::{
    from_obj::ToOwnedTable,
    tables::{
        cmap::Cmap,
        glyf::{
            Anchor, Component, ComponentFlags, CompositeGlyph, GlyfLocaBuilder, Glyph, SimpleGlyph,
            Transform,
        },
        head::Head,
        hhea::Hhea,
        hmtx::{Hmtx, LongMetric},
        maxp::Maxp,
    },
    types::{F2Dot14, GlyphId, GlyphId16},
    FontBuilder,
};
#[derive(Debug, Clone)]
pub struct Instance {
    pub canonical: usize,
    pub original_gid: u16,
    pub transform: [f64; 6],
}
pub struct SharedFont {
    pub bytes: Vec<u8>,
    pub old_gids: BTreeMap<u16, u16>,
    pub instance_gids: Vec<u16>,
    pub canonical_gids: BTreeMap<usize, u16>,
    pub retired: usize,
    pub canonical_bytes: usize,
    pub stub_bytes: usize,
}

/// The caller supplies the union of all remaining visible and invisible users.
/// CIDs and widths are independent of this subset's GID numbering.
pub fn build(
    default: &[u8],
    required: &BTreeSet<u16>,
    canonicals: &BTreeMap<usize, GlyphShape>,
    instances: &[Instance],
    encodings: &[(usize, String)],
) -> Result<SharedFont, String> {
    let error = |e: &dyn std::fmt::Display| e.to_string();
    let font = FontRef::new(default).map_err(|e| error(&e))?;
    let loca = font.loca(None).map_err(|e| error(&e))?;
    let glyf = font.glyf().map_err(|e| error(&e))?;
    let oldmax = font.maxp().map_err(|e| error(&e))?;
    let oldcount = oldmax.num_glyphs();
    let hmtx = font.hmtx().map_err(|e| error(&e))?;
    let mut builder = GlyfLocaBuilder::new();
    let mut metrics = Vec::new();
    let mut old_gids = BTreeMap::new();
    let mut keep = required.clone();
    keep.insert(0);
    if keep.len() + canonicals.len() + instances.len() > u16::MAX as usize {
        return Err("shared font exceeds 16-bit GID space".into());
    }
    for &old in &keep {
        if old >= oldcount {
            return Err("required default GID out of range".into());
        }
        let glyph: Glyph = loca
            .get_glyf(GlyphId::new(old as u32), &glyf)
            .map_err(|e| error(&e))?
            .map(|g| g.to_owned_table())
            .unwrap_or(Glyph::Empty);
        let gid = old_gids.len() as u16;
        old_gids.insert(old, gid);
        builder.add_glyph(&glyph).map_err(|e| error(&e))?;
        metrics.push(LongMetric {
            advance: hmtx.advance(GlyphId::new(old as u32)).unwrap_or(0),
            side_bearing: hmtx.side_bearing(GlyphId::new(old as u32)).unwrap_or(0),
        });
    }
    let mut factors = BTreeMap::<usize, f64>::new();
    for instance in instances {
        if instance.transform.iter().any(|x| !x.is_finite()) {
            return Err("nonfinite composite transform".into());
        }
        let t = instance.transform;
        let factor = t[..4].iter().map(|x| x.abs()).fold(0., f64::max) / 1.5;
        let value = factors.entry(instance.canonical).or_insert(1.);
        *value = value.max(factor);
    }
    let mut canonical_gids = BTreeMap::new();
    let mut canonical_paths = BTreeMap::new();
    let mut canonical_bytes = 0;
    for (&j, shape) in canonicals {
        let factor = *factors.get(&j).ok_or("canonical has no instance")?;
        let path = kurbo::Affine::scale(factor) * shape.path.clone();
        let glyph = SimpleGlyph::from_bezpath(&path).map_err(|e| format!("{e:?}"))?;
        canonical_bytes += write_fonts::dump_table(&glyph)
            .map_err(|e| error(&e))?
            .len();
        let gid = metrics.len() as u16;
        canonical_gids.insert(j, gid);
        canonical_paths.insert(j, path);
        builder.add_glyph(&glyph).map_err(|e| error(&e))?;
        metrics.push(LongMetric {
            advance: 2048,
            side_bearing: glyph.bbox.x_min,
        });
    }
    let mut instance_gids = Vec::new();
    let mut seen = BTreeMap::new();
    let mut stub_bytes = 0;
    for instance in instances {
        let t = instance.transform;
        let factor = factors[&instance.canonical];
        let q: [i16; 4] =
            std::array::from_fn(|i| (t[i] / factor * 16384.).round_ties_even() as i16);
        let offsets: [f64; 2] = [t[4].round_ties_even(), t[5].round_ties_even()];
        if t[..4].iter().any(|v| (v / factor).abs() >= 2.)
            || offsets.iter().any(|v| v.abs() > 32767.)
        {
            return Err("composite transform out of range".into());
        }
        let key = (
            instance.canonical,
            q,
            offsets[0] as i16,
            offsets[1] as i16,
            instance.original_gid,
        );
        if let Some(&gid) = seen.get(&key) {
            instance_gids.push(gid);
            continue;
        }
        let linear = q.map(|v| v as f64 / 16384.);
        let transform = Transform {
            xx: F2Dot14::from_bits(q[0]),
            yx: F2Dot14::from_bits(q[1]),
            xy: F2Dot14::from_bits(q[2]),
            yy: F2Dot14::from_bits(q[3]),
        };
        let path = kurbo::Affine::new([
            linear[0], linear[1], linear[2], linear[3], offsets[0], offsets[1],
        ]) * canonical_paths[&instance.canonical].clone();
        let bbox = path.control_box();
        let glyph = CompositeGlyph::new(
            Component::new(
                GlyphId16::new(canonical_gids[&instance.canonical]),
                Anchor::Offset {
                    x: offsets[0] as i16,
                    y: offsets[1] as i16,
                },
                transform,
                ComponentFlags {
                    round_xy_to_grid: true,
                    unscaled_component_offset: true,
                    ..Default::default()
                },
            ),
            bbox,
        );
        let bytes = write_fonts::dump_table(&glyph).map_err(|e| error(&e))?;
        stub_bytes += bytes.len();
        builder.add_glyph(&glyph).map_err(|e| error(&e))?;
        let gid = metrics.len() as u16;
        instance_gids.push(gid);
        seen.insert(key, gid);
        metrics.push(LongMetric {
            advance: hmtx
                .advance(GlyphId::new(instance.original_gid as u32))
                .ok_or("missing original advance")?,
            side_bearing: glyph.bbox.x_min,
        });
    }
    let (glyf, loca, format) = builder.build();
    let mut head: Head = font.head().map_err(|e| error(&e))?.to_owned_table();
    head.index_to_loc_format = if format == write_fonts::tables::loca::LocaFormat::Long {
        1
    } else {
        0
    };
    let mut maxp: Maxp = oldmax.to_owned_table();
    maxp.num_glyphs = metrics.len() as u16;
    maxp.max_points = Some(
        maxp.max_points.unwrap_or(0).max(
            canonicals
                .values()
                .map(|s| s.num_points as u16)
                .max()
                .unwrap_or(0),
        ),
    );
    maxp.max_contours = Some(
        maxp.max_contours.unwrap_or(0).max(
            canonicals
                .values()
                .map(|s| s.num_contours as u16)
                .max()
                .unwrap_or(0),
        ),
    );
    maxp.max_component_elements = Some(1);
    maxp.max_component_depth = Some(1);
    maxp.max_composite_points = Some(
        canonicals
            .values()
            .map(|s| s.num_points as u16)
            .max()
            .unwrap_or(0),
    );
    maxp.max_composite_contours = Some(
        canonicals
            .values()
            .map(|s| s.num_contours as u16)
            .max()
            .unwrap_or(0),
    );
    let mut hhea: Hhea = font.hhea().map_err(|e| error(&e))?.to_owned_table();
    hhea.number_of_h_metrics = metrics.len() as u16;
    let mut cmap = Vec::new();
    let mut chars = BTreeSet::new();
    for (shape, text) in encodings {
        if let Some(&gid) = old_gids.get(&(*shape as u16 + 1)) {
            for c in text.chars() {
                if chars.insert(c) {
                    cmap.push((c, GlyphId::new(gid as u32)));
                }
            }
        }
    }
    if cmap.is_empty() {
        cmap.push(('\0', GlyphId::new(0)));
    }
    let cmap = Cmap::from_mappings(cmap).map_err(|e| error(&e))?;
    let hmtx = Hmtx::new(metrics, vec![]);
    let mut out = FontBuilder::new();
    out.add_table(&glyf)
        .map_err(|e| error(&e))?
        .add_table(&loca)
        .map_err(|e| error(&e))?
        .add_table(&head)
        .map_err(|e| error(&e))?
        .add_table(&maxp)
        .map_err(|e| error(&e))?
        .add_table(&hhea)
        .map_err(|e| error(&e))?
        .add_table(&hmtx)
        .map_err(|e| error(&e))?
        .add_table(&cmap)
        .map_err(|e| error(&e))?
        .copy_missing_tables(font);
    Ok(SharedFont {
        bytes: out.build(),
        retired: oldcount as usize - keep.len(),
        old_gids,
        instance_gids,
        canonical_gids,
        canonical_bytes,
        stub_bytes,
    })
}
