//! One-page PDF assembly for the M1-A pipeline.
//!
//! One document, two fonts:
//!   * F1 — the embedded reconstructed font (source-derived TrueType outlines),
//!     per-glyph ToUnicode fallback + per-span `/ActualText`;
//!   * F2 — a glyphless font (one empty glyph, per-CID explicit ToUnicode)
//!     used ONLY to place invisible semantic owner text over raster fallback
//!     regions (SPEC §6.2 fallback font; exactly one owner per span).
//!
//! Paint order: paper background → raster fallback patches (original source
//! pixels, Flate) → invisible owner text → visible vector glyphs.

use pdf_writer::types::CidFontType;
use pdf_writer::types::SystemInfo;
use pdf_writer::types::TextRenderingMode;
use pdf_writer::{Content, Finish, Name, Pdf, Rect, Ref, Str, TextStr};

use crate::glyphs::GlyphShape;

#[derive(Debug, Default, Clone)]
pub struct Patch {
    pub bbox_px: [f64; 4],
    pub rgb: Vec<u8>,
    pub w: u32,
    pub h: u32,
}

#[derive(Debug, Default, Clone)]
pub struct Owner {
    pub text: String,
    pub bbox_px: [f64; 4],
    /// the OCR span this owner overlays (line-level marks need the span id)
    pub span_id: String,
}

/// A reading-order line of the OCR document: the exact line text (OCR's own
/// separators verbatim — no invented whitespace) and its span ids in order.
#[derive(Debug, Clone)]
pub struct LineSpec {
    pub text: String,
    pub spans: Vec<String>,
}

fn to_unicode_stream(encodings: &[(usize, String)]) -> String {
    let mut cmap = String::from(
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n",
    );
    if !encodings.is_empty() {
        cmap.push_str(&format!(
            "1 begincodespacerange\n<0000> <{:04X}>\nendcodespacerange\n",
            encodings.len()
        ));
        cmap.push_str(&format!("{} beginbfchar\n", encodings.len()));
        for (cid, (_, semantic)) in encodings.iter().enumerate() {
            cmap.push_str(&format!("<{:04X}> <", cid + 1));
            for unit in semantic.encode_utf16() {
                cmap.push_str(&format!("{unit:04X}"));
            }
            cmap.push_str(">\n");
        }
        cmap.push_str("endbfchar\n");
    }
    cmap.push_str("endcmap\nCMapName currentdict /CMap defineresource pop\nend end\n");
    cmap
}

fn cid_to_gid_bytes(encodings: &[(usize, String)]) -> Vec<u8> {
    let mut v = vec![0u8, 0u8]; // CID 0 → GID 0 (.notdef)
    for (glyph_idx, _) in encodings {
        let gid = glyph_idx.wrapping_add(1);
        v.push((gid >> 8) as u8);
        v.push((gid & 0xFF) as u8);
    }
    v
}

#[allow(clippy::too_many_arguments)]
pub fn assemble(
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    occurrences: &[(usize, u32, [f64; 4], String, String, String)],
    span_texts: &[(String, String)],
    page_w_pt: f32,
    page_h_pt: f32,
    dpi: f64,
    paper: [u8; 3],
    ink: [u8; 3],
    font_bytes: Vec<u8>,
    glyphless_bytes: Vec<u8>,
    glyphless_encodings: &[(usize, String)],
    patches: &[Patch],
    owners: &[Owner],
    owner_cids: &[u32],
    lines: &[LineSpec],
) -> Result<Vec<u8>, String> {
    let _ = glyphless_bytes;
    let _ = glyphless_encodings;
    let mut pdf = Pdf::new();
    pdf.set_version(1, 7);

    let catalog = Ref::new(1);
    let page_tree = Ref::new(2);
    let page = Ref::new(3);
    let content = Ref::new(4);
    let glyph_font = Ref::new(5);
    let glyph_desc = Ref::new(6);
    let glyph_cidfont = Ref::new(7);
    let glyph_ff = Ref::new(8);
    let glyph_map = Ref::new(9);
    let glyph_tu = Ref::new(10);
    let mut next = 11;

    let glyphless_font = Ref::new(next);
    next += 1;
    let glyphless_desc = Ref::new(next);
    next += 1;
    let glyphless_cidfont = Ref::new(next);
    next += 1;
    let glyphless_ff = Ref::new(next);
    next += 1;
    let glyphless_map = Ref::new(next);
    next += 1;
    let glyphless_tu = Ref::new(next);
    next += 1;

    let image_ids: Vec<Ref> = (0..patches.len())
        .map(|i| {
            let r = Ref::new(next + i as i32);
            r
        })
        .collect();

    pdf.catalog(catalog).pages(page_tree);
    pdf.pages(page_tree).kids([page]).count(1);

    // glyph font (all streams before the CID-font writer)
    let map_bytes = cid_to_gid_bytes(encodings);
    let tu = to_unicode_stream(encodings);
    pdf.stream(glyph_map, &map_bytes).finish();
    pdf.stream(glyph_tu, tu.as_bytes()).finish();
    pdf.stream(glyph_ff, &font_bytes)
        .pair(Name(b"Length1"), font_bytes.len() as i32)
        .finish();
    pdf.font_descriptor(glyph_desc)
        .name(Name(b"ScanWeaveM0Probe"))
        .flags(pdf_writer::types::FontFlags::SYMBOLIC)
        .bbox(Rect::new(0.0, -50.0, 4096.0, 4096.0))
        .italic_angle(0.0)
        .ascent(3800.0)
        .descent(-500.0)
        .cap_height(3600.0)
        .stem_v(80.0)
        .font_file2(glyph_ff);
    {
        let mut cid = pdf.cid_font(glyph_cidfont);
        cid.subtype(CidFontType::Type2)
            .base_font(Name(b"ScanWeaveM0Probe"))
            .system_info(SystemInfo {
                registry: Str(b"Adobe"),
                ordering: Str(b"Identity"),
                supplement: 0,
            })
            .font_descriptor(glyph_desc)
            .default_width(1000.0)
            .cid_to_gid_map_stream(glyph_map);
        {
            let mut widths = cid.widths();
            for (cid_index, (elem, _)) in encodings.iter().enumerate() {
                // owner-only CIDs reference GID1 (invisible runs): default width
                let w = if *elem < shapes.len() {
                    (shapes[*elem].ink_span_fu[0].ceil().max(1.0) + 2.0) * 1000.0 / 2048.0
                } else {
                    500.0
                };
                widths.consecutive(cid_index as u16 + 1, [w as f32]);
            }
            widths.finish();
        }
    }

    // F2 (glyphless owner font) is only emitted when the caller supplies it.
    // An empty stub resource makes PDFium reject the whole document, so it is
    // omitted entirely when absent.
    if !glyphless_bytes.is_empty() {
        let gl_map = cid_to_gid_bytes(glyphless_encodings);
        let gl_tu = to_unicode_stream(glyphless_encodings);
        pdf.stream(glyphless_map, &gl_map).finish();
        pdf.stream(glyphless_tu, gl_tu.as_bytes()).finish();
        pdf.stream(glyphless_ff, &glyphless_bytes)
            .pair(Name(b"Length1"), glyphless_bytes.len() as i32)
            .finish();
        pdf.font_descriptor(glyphless_desc)
            .name(Name(b"ScanWeaveM0ProbeGlyphless"))
            .flags(pdf_writer::types::FontFlags::SYMBOLIC)
            .bbox(Rect::new(0.0, -200.0, 0.0, 700.0))
            .italic_angle(0.0)
            .ascent(700.0)
            .descent(-200.0)
            .cap_height(700.0)
            .stem_v(80.0)
            .font_file2(glyphless_ff);
        {
            let mut gl_cid = pdf.cid_font(glyphless_cidfont);
            gl_cid.subtype(CidFontType::Type2)
                .base_font(Name(b"ScanWeaveM0ProbeGlyphless"))
                .system_info(SystemInfo {
                    registry: Str(b"Adobe"),
                    ordering: Str(b"Identity"),
                    supplement: 0,
                })
                .font_descriptor(glyphless_desc)
                .default_width(500.0)
                .cid_to_gid_map_stream(glyphless_map);
        }
        let mut t0g = pdf.type0_font(glyphless_font);
        t0g.base_font(Name(b"ScanWeaveM0ProbeGlyphless"))
            .encoding_predefined(Name(b"Identity-H"))
            .descendant_font(glyphless_cidfont)
            .to_unicode(glyphless_tu);
        t0g.finish();
    }

    // type0 font (the only one)
    let mut t0 = pdf.type0_font(glyph_font);
    t0.base_font(Name(b"ScanWeaveM0Probe"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(glyph_cidfont)
        .to_unicode(glyph_tu);
    t0.finish();

    // patch images
    for (i, patch) in patches.iter().enumerate() {
        let mut enc = flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
        use std::io::Write;
        enc.write_all(&patch.rgb).map_err(|e| e.to_string())?;
        let compressed = enc.finish().map_err(|e| e.to_string())?;
        let mut img = pdf.stream(image_ids[i], &compressed);
        img.pair(Name(b"Type"), Name(b"XObject"));
        img.pair(Name(b"Subtype"), Name(b"Image"));
        img.pair(Name(b"Width"), patch.w as i32);
        img.pair(Name(b"Height"), patch.h as i32);
        img.pair(Name(b"ColorSpace"), Name(b"DeviceRGB"));
        img.pair(Name(b"BitsPerComponent"), 8);
        img.pair(Name(b"Filter"), Name(b"FlateDecode"));
        img.finish();
    }

    // content
    let mut c = Content::new();
    c.set_fill_rgb(
        paper[0] as f32 / 255.0,
        paper[1] as f32 / 255.0,
        paper[2] as f32 / 255.0,
    );
    c.rect(0.0, 0.0, page_w_pt, page_h_pt);
    c.fill_nonzero();

    for (i, patch) in patches.iter().enumerate() {
        let x = patch.bbox_px[0] as f32 * 72.0 / dpi as f32;
        let y_bot = page_h_pt - patch.bbox_px[3] as f32 * 72.0 / dpi as f32;
        let w_pt = (patch.bbox_px[2] - patch.bbox_px[0]) as f32 * 72.0 / dpi as f32;
        let h_pt = (patch.bbox_px[3] - patch.bbox_px[1]) as f32 * 72.0 / dpi as f32;
        c.save_state();
        c.transform([w_pt, 0.0, 0.0, h_pt, x, y_bot]);
        let name = format!("Im{i}");
        c.x_object(Name(name.as_bytes()));
        c.restore_state();
    }

    let span_map: std::collections::HashMap<&str, &str> = span_texts
        .iter()
        .map(|(id, t)| (id.as_str(), t.as_str()))
        .collect();
    let span_astral = |id: &str| {
        span_map
            .get(id)
            .copied()
            .unwrap_or("")
            .chars()
            .any(|c| (c as u32) > 0xFFFF)
    };
    let owner_by_span: std::collections::HashMap<&str, (&Owner, u32)> = owners
        .iter()
        .zip(owner_cids.iter())
        .map(|(o, c)| (o.span_id.as_str(), (o, *c)))
        .collect();
    // visible occurrences grouped per span (reading order within a span)
    let mut groups: Vec<Vec<usize>> = Vec::new();
    {
        let mut current: Option<&str> = None;
        for (i, occ) in occurrences.iter().enumerate() {
            if current != Some(occ.3.as_str()) {
                groups.push(Vec::new());
                current = Some(occ.3.as_str());
            }
            groups.last_mut().unwrap().push(i);
        }
    }

    c.begin_text();
    c.set_font(Name(b"F1"), 1.0);
    c.set_fill_rgb(
        ink[0] as f32 / 255.0,
        ink[1] as f32 / 255.0,
        ink[2] as f32 / 255.0,
    );

    let mut emitted_spans: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut covered = |span: &str, emitted: &mut std::collections::HashSet<String>| {
        emitted.insert(span.to_string())
    };

    // Lines in reading order. A line that mixes visible spans with raster-fallback
    // owners is wrapped in ONE line-level /ActualText carrying the OCR line text
    // (OCR separators verbatim): native search then finds the whole line, and the
    // fallback owner run rides inside the mark instead of being hoisted to the end
    // of the extraction by PDFium's invisible-run ordering. Pure-vector lines keep
    // the per-span marks of the accepted M0-Q/M1-A behaviour (astral spans keep the
    // per-glyph ToUnicode owner).
    for line in lines {
        for sid in &line.spans {
            covered(sid.as_str(), &mut emitted_spans);
            let visible = groups
                .iter()
                .find(|g| occurrences[g[0]].3.as_str() == sid.as_str());
            if let Some(group) = visible {
                let span_id = occurrences[group[0]].3.as_str();
                let actual = span_map.get(span_id).copied().unwrap_or("");
                let astral = span_astral(span_id);
                if !astral {
                    let mut mc = c.begin_marked_content_with_properties(Name(b"Span"));
                    let mut pl = mc.properties();
                    pl.actual_text(TextStr(actual));
                }
                for &i in group {
                    let (gidx, cid, bbox_px, _, _, _) = &occurrences[i];
                    let g = &shapes[*gidx];
                    let x0 = bbox_px[0] as f32 * 72.0 / dpi as f32;
                    let y1_px = bbox_px[3] as f32;
                    let y0_px = bbox_px[1] as f32;
                    let bottom_pt = page_h_pt - y1_px * 72.0 / dpi as f32;
                    let top_pt = page_h_pt - y0_px * 72.0 / dpi as f32;
                    let w_pt = bbox_px[2] as f32 * 72.0 / dpi as f32 - x0;
                    let h_pt = top_pt - bottom_pt;
                    let gx_span = g.ink_span_fu[0] as f32;
                    let gy_span = g.ink_span_fu[1] as f32;
                    let sx = w_pt * 2048.0 / gx_span.max(1.0);
                    let sy = h_pt * 2048.0 / gy_span.max(1.0);
                    let tx = x0 - (g.anchor_bbox_fu[0] as f32) * sx / 2048.0;
                    let ty = bottom_pt - (g.anchor_bbox_fu[1] as f32) * sy / 2048.0;
                    c.set_text_matrix([sx, 0.0, 0.0, sy, tx, ty]);
                    let cid = *cid + 1;
                    c.show(Str(&[(cid >> 8) as u8, (cid & 0xFF) as u8]));
                }
                if !astral {
                    c.end_marked_content();
                }
            } else if let Some((owner, cid)) = owner_by_span.get(sid.as_str()) {
                // Fallback-span owner run, drawn VISIBLY at the span's position:
                // the owner CID references the font's EMPTY placeholder glyph,
                // so nothing is painted (the raster patch already carries the
                // pixels) while both extractors order the run inline like any
                // other visible text. An invisible run is appended at the end of
                // the text page by PDFium (measured, M1-A N1). /ActualText owns
                // the span's label for word grouping; astral labels keep the
                // per-glyph ToUnicode transport.
                let owner_text = span_map.get(sid.as_str()).copied().unwrap_or("");
                let astral = owner_text.chars().any(|c| (c as u32) > 0xFFFF);
                if !astral {
                    let mut mc = c.begin_marked_content_with_properties(Name(b"Span"));
                    let mut pl = mc.properties();
                    pl.actual_text(TextStr(owner_text));
                }
                let x0 = owner.bbox_px[0] as f32 * 72.0 / dpi as f32;
                let y_bot = page_h_pt - owner.bbox_px[3] as f32 * 72.0 / dpi as f32;
                let h_pt =
                    ((owner.bbox_px[3] - owner.bbox_px[1]) as f32 * 72.0 / dpi as f32).max(4.0);
                let cx = *cid;
                let bytes = Str(&[(cx >> 8) as u8, (cx & 0xFF) as u8]);
                c.set_font(Name(b"F1"), h_pt);
                c.set_text_matrix([1.0, 0.0, 0.0, 1.0, x0, y_bot]);
                c.show(bytes);
                c.set_font(Name(b"F1"), 1.0);
                if !astral {
                    c.end_marked_content();
                }
            }
        }
    }

    // defensive: any span not covered by a line (empty OCR text etc.)
    for (i, occ) in occurrences.iter().enumerate() {
        let sid = occ.3.as_str();
        if !emitted_spans.contains(sid) {
            let (gidx, cid, bbox_px, _, _, _) = &occurrences[i];
            let g = &shapes[*gidx];
            let x0 = bbox_px[0] as f32 * 72.0 / dpi as f32;
            let y1_px = bbox_px[3] as f32;
            let y0_px = bbox_px[1] as f32;
            let bottom_pt = page_h_pt - y1_px * 72.0 / dpi as f32;
            let top_pt = page_h_pt - y0_px * 72.0 / dpi as f32;
            let w_pt = bbox_px[2] as f32 * 72.0 / dpi as f32 - x0;
            let h_pt = top_pt - bottom_pt;
            let sx = w_pt * 2048.0 / g.ink_span_fu[0].max(1.0) as f32;
            let sy = h_pt * 2048.0 / g.ink_span_fu[1].max(1.0) as f32;
            let tx = x0 - (g.anchor_bbox_fu[0] as f32) * sx / 2048.0;
            let ty = bottom_pt - (g.anchor_bbox_fu[1] as f32) * sy / 2048.0;
            c.set_text_matrix([sx, 0.0, 0.0, sy, tx, ty]);
            let cid = *cid + 1;
            c.show(Str(&[(cid >> 8) as u8, (cid & 0xFF) as u8]));
        }
    }
    for (owner, cid) in owners.iter().zip(owner_cids.iter()) {
        if emitted_spans.contains(owner.span_id.as_str()) {
            continue;
        }
        let x0 = owner.bbox_px[0] as f32 * 72.0 / dpi as f32;
        let y_bot = page_h_pt - owner.bbox_px[3] as f32 * 72.0 / dpi as f32;
        let h_pt = ((owner.bbox_px[3] - owner.bbox_px[1]) as f32 * 72.0 / dpi as f32).max(4.0);
        let cx = *cid;
        let bytes = Str(&[(cx >> 8) as u8, (cx & 0xFF) as u8]);
        c.set_text_rendering_mode(TextRenderingMode::Invisible);
        c.set_font(Name(b"F1"), h_pt);
        c.set_text_matrix([1.0, 0.0, 0.0, 1.0, x0, y_bot]);
        c.show(bytes);
        c.set_text_rendering_mode(TextRenderingMode::Fill);
        c.set_font(Name(b"F1"), 1.0);
    }

    c.end_text();
    let content_bytes = c.finish();
    pdf.stream(content, &content_bytes).finish();

    let mut p = pdf.page(page);
    p.parent(page_tree)
        .media_box(Rect::new(0.0, 0.0, page_w_pt, page_h_pt))
        .contents(content);
    let mut res = p.resources();
    if !glyphless_bytes.is_empty() {
        res.fonts()
            .pair(Name(b"F1"), glyph_font)
            .pair(Name(b"F2"), glyphless_font);
    } else {
        res.fonts().pair(Name(b"F1"), glyph_font);
    }
    if !patches.is_empty() {
        let mut xo = res.x_objects();
        for (i, id) in image_ids.iter().enumerate() {
            let name = format!("Im{i}");
            xo.pair(Name(name.as_bytes()), *id);
        }
    }
    res.finish();
    p.finish();

    let info_id = Ref::new(next + patches.len() as i32);
    let mut doc = pdf.document_info(info_id);
    doc.producer(TextStr("scanweave-m1a"));
    doc.finish();

    Ok(pdf.finish())
}

fn g_free() -> i32 {
    0
}
