//! TrueType serialization via write-fonts (no hand-written table bytes).
//! Glyphs: .notdef + one per distinct shape. The nominal cmap maps a
//! representative char per shape; it is NOT the PDF extraction source of truth.

use crate::glyphs::GlyphShape;
use write_fonts::{
    tables::{
        cmap::Cmap,
        glyf::{GlyfLocaBuilder, SimpleGlyph},
        head::Head,
        hhea::Hhea,
        hmtx::{Hmtx, LongMetric},
        maxp::Maxp,
        name::{Name, NameRecord},
        os2::Os2,
        post::Post,
    },
    types::{Fixed, FWord, GlyphId, LongDateTime, NameId, UfWord},
    OffsetMarker,
    FontBuilder,
};

pub fn build_font(
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    upem: u16,
) -> Result<Vec<u8>, String> {
    let placeholder = shapes.is_empty() && !encodings.is_empty();
    let num_glyphs = shapes.len() + 1 + usize::from(placeholder);

    // glyf/loca — .notdef is a tiny real glyph so glyf is never zero-length
    // (a zero-length glyf fails OTS sanitization on owner-only fonts)
    let mut notdef_path = kurbo::BezPath::new();
    notdef_path.move_to(kurbo::Point::new(4.0, 4.0));
    notdef_path.line_to(kurbo::Point::new(200.0, 4.0));
    notdef_path.line_to(kurbo::Point::new(200.0, 200.0));
    notdef_path.line_to(kurbo::Point::new(4.0, 200.0));
    notdef_path.close_path();
    let notdef = SimpleGlyph::from_bezpath(&notdef_path).map_err(|e| format!("notdef: {e:?}"))?;
    let mut builder = GlyfLocaBuilder::new();
    builder.add_glyph(&notdef).map_err(|e| e.to_string())?;
    for s in shapes {
        let g = SimpleGlyph::from_bezpath(&s.path)
            .map_err(|e| format!("glyph {}: {e:?}", s.shape_key))?;
        builder.add_glyph(&g).map_err(|e| e.to_string())?;
    }
    // invisible owner CIDs reference real GIDs: PDFium drops runs whose CID maps
    // to a glyph the font does not actually contain. Owner-only fonts (no vector
    // shapes) therefore get one placeholder glyph at GID1.
    if placeholder {
        // GID1 for owner CIDs: the glyph must EXIST in the font (PDFium drops
        // runs whose CID has no glyph) and must stay a normal clockwise outer
        // contour (the qualification harness flags degenerate contours). What
        // the owner RUN paints is decided by the assembling rendering mode, not
        // by this outline: owner runs are drawn INVISIBLE (see page_pdf.rs) on
        // the span's traced ink baseline, so this box is never painted.
        let mut placeholder_path = kurbo::BezPath::new();
        placeholder_path.move_to(kurbo::Point::new(4.0, 4.0));
        placeholder_path.line_to(kurbo::Point::new(4.0, 200.0));
        placeholder_path.line_to(kurbo::Point::new(200.0, 200.0));
        placeholder_path.line_to(kurbo::Point::new(200.0, 4.0));
        placeholder_path.close_path();
        let placeholder_glyph = SimpleGlyph::from_bezpath(&placeholder_path)
            .map_err(|e| format!("placeholder: {e:?}"))?;
        builder
            .add_glyph(&placeholder_glyph)
            .map_err(|e| e.to_string())?;
    }
    let (glyf, loca, loca_format) = builder.build();

    // global bbox (must cover the placeholder glyph too: an all-zero bbox makes
    // PDFium reject the font program)
    let (mut x_min, mut y_min, mut x_max, mut y_max) = (i16::MAX, i16::MAX, i16::MIN, i16::MIN);
    for s in shapes {
        x_min = x_min.min(s.bbox_fu[0].floor() as i16);
        y_min = y_min.min(s.bbox_fu[1].floor() as i16);
        x_max = x_max.max(s.bbox_fu[2].ceil() as i16);
        y_max = y_max.max(s.bbox_fu[3].ceil() as i16);
    }
    if x_min > x_max {
        (x_min, y_min, x_max, y_max) = (0, 0, 0, 0);
    }
    if placeholder {
        x_min = x_min.min(4);
        y_min = y_min.min(4);
        x_max = x_max.max(200);
        y_max = y_max.max(200);
    }

    // advances: ink width + 2 units padding
    let advances: Vec<u16> = std::iter::once(0)
        .chain(shapes.iter().map(|s| {
            let w = (s.bbox_fu[2] - s.bbox_fu[0]).ceil().max(1.0) as u16;
            w + 2
        }))
        .collect();

    let head = Head {
        font_revision: Fixed::from_i32(0),
        checksum_adjustment: 0,
        magic_number: 0x5F0F3CF5,
        flags: 0x000B,
        units_per_em: upem,
        created: LongDateTime::new(0),
        modified: LongDateTime::new(0),
        x_min,
        y_min,
        x_max,
        y_max,
        mac_style: Default::default(),
        lowest_rec_ppem: 8,
        font_direction_hint: 2,
        index_to_loc_format: if loca_format == write_fonts::tables::loca::LocaFormat::Long {
            1
        } else {
            0
        },
    };

    let hhea = Hhea {
        ascender: FWord::new(y_max.max(1)),
        descender: FWord::new(y_min.min(0)),
        line_gap: FWord::new(0),
        advance_width_max: UfWord::new(advances.iter().copied().max().unwrap_or(upem)),
        min_left_side_bearing: FWord::new(x_min),
        min_right_side_bearing: FWord::new(0),
        x_max_extent: FWord::new(x_max),
        caret_slope_rise: 1,
        caret_slope_run: 0,
        caret_offset: 0,
        number_of_h_metrics: num_glyphs.min(0x7FFF) as u16,
    };

    let maxp = Maxp {
        num_glyphs: num_glyphs as u16,
        max_points: Some(shapes.iter().map(|s| s.num_points as u16).max().unwrap_or(0)),
        max_contours: Some(
            shapes
                .iter()
                .map(|s| s.num_contours as u16)
                .max()
                .unwrap_or(0),
        ),
        max_composite_points: Some(0),
        max_composite_contours: Some(0),
        max_zones: Some(1),
        max_twilight_points: Some(0),
        max_storage: Some(0),
        max_function_defs: Some(0),
        max_instruction_defs: Some(0),
        max_stack_elements: Some(64),
        max_size_of_instructions: Some(0),
        max_component_elements: Some(0),
        max_component_depth: Some(0),
    };

    // advances: .notdef + shapes (+ placeholder when owner CIDs exist)
    let mut hmtx_metrics: Vec<LongMetric> = Vec::with_capacity(num_glyphs);
    hmtx_metrics.push(LongMetric { advance: 0, side_bearing: 0 }); // notdef
    for s in shapes {
        let w = (s.bbox_fu[2] - s.bbox_fu[0]).ceil().max(1.0) as u16;
        let advance = w + 2;
        hmtx_metrics.push(LongMetric {
            advance,
            side_bearing: s.bbox_fu[0] as i16,
        });
    }
    if placeholder {
        hmtx_metrics.push(LongMetric { advance: 0, side_bearing: 0 });
    }
    let hmtx = Hmtx::new(hmtx_metrics, vec![]);

    // nominal cmap: representative chars per shape (NOT the PDF extraction truth).
    // One char may be carried by several shapes (SPEC §3: several differently
    // printed shapes can expose the same Unicode); the nominal cmap keeps only
    // the first mapping per char — extraction uses ToUnicode, never this table.
    let mut mappings: Vec<(char, GlyphId)> = Vec::new();
    let mut seen: Vec<char> = Vec::new();
    for (glyph_idx, semantic) in encodings {
        let gid = GlyphId::new(glyph_idx.wrapping_add(1) as u32);
        for ch in semantic.chars() {
            if !seen.contains(&ch) {
                seen.push(ch);
                mappings.push((ch, gid));
            }
        }
    }
    let cmap = Cmap::from_mappings(mappings).map_err(|e| e.to_string())?;

    // minimal name table: family + full name + postscript name (Windows Unicode records)
    let name = Name::new(vec![
        NameRecord::new(
            3,
            1,
            0x0409,
            NameId::FAMILY_NAME,
            OffsetMarker::new("ScanWeave M0 Probe".to_string()),
        ),
        NameRecord::new(
            3,
            1,
            0x0409,
            NameId::UNIQUE_ID,
            OffsetMarker::new("ScanWeaveM0Probe;M0;20261013".to_string()),
        ),
        NameRecord::new(
            3,
            1,
            0x0409,
            NameId::FULL_NAME,
            OffsetMarker::new("ScanWeave M0 Probe Regular".to_string()),
        ),
        NameRecord::new(
            3,
            1,
            0x0409,
            NameId::POSTSCRIPT_NAME,
            OffsetMarker::new("ScanWeaveM0Probe".to_string()),
        ),
    ]);

    // post version 3.0: no glyph names (version 1.0 without the standard-names
    // array is malformed and can make renderers reject the font program)
    let post = Post {
        version: write_fonts::types::Version16Dot16::new(3, 0),
        ..Default::default()
    };
    // OS/2 minimal (version 0): the M0 baseline's font with this table embedding
    // cleanly in both engines; keep it identical.
    let os2 = Os2::default();

    let mut fb = FontBuilder::new();
    fb.add_table(&head).map_err(|e| e.to_string())?;
    fb.add_table(&hhea).map_err(|e| e.to_string())?;
    fb.add_table(&maxp).map_err(|e| e.to_string())?;
    fb.add_table(&hmtx).map_err(|e| e.to_string())?;
    fb.add_table(&cmap).map_err(|e| e.to_string())?;
    fb.add_table(&name).map_err(|e| e.to_string())?;
    fb.add_table(&post).map_err(|e| e.to_string())?;
    fb.add_table(&os2).map_err(|e| e.to_string())?;
    fb.add_table(&glyf).map_err(|e| e.to_string())?;
    fb.add_table(&loca).map_err(|e| e.to_string())?;
    Ok(fb.build())
}
