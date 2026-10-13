//! PDF assembly via pdf-writer: Type 0 / CIDFontType2, explicit CIDToGIDMap,
//! UTF-16BE ToUnicode CMap, per-occurrence placement from source geometry.
//! Different semantic strings over one shared glyph get distinct CIDs.

use crate::glyphs::GlyphShape;
use pdf_writer::{Content, Finish, Name, Pdf, Ref, Rect, Str, TextStr};
use pdf_writer::types::{CidFontType, SystemInfo};

fn utf16be_hex(s: &str) -> String {
    let mut out = String::new();
    for unit in s.encode_utf16() {
        out.push_str(&format!("{unit:04X}"));
    }
    out
}

#[allow(clippy::too_many_arguments)]
pub fn assemble(
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    occurrences: &[(usize, usize, [f64; 4], String, String, String)],
    artwork: &[(usize, [f64; 4])],
    contour_polylines: &std::collections::HashMap<String, Vec<Vec<[f64; 2]>>>,
    page_w_pt: f32,
    page_h_pt: f32,
    paper: [u8; 3],
    ink: [u8; 3],
    font_bytes: Vec<u8>,
) -> Result<(Vec<u8>, Vec<(String, u64)>), String> {
    let upem = 2048.0f32;
    let mut breakdown: Vec<(String, u64)> = Vec::new();
    let mut pdf = Pdf::new();
    pdf.set_version(1, 7);

    let catalog_id = Ref::new(1);
    let page_tree_id = Ref::new(2);
    let page_id = Ref::new(3);
    let content_id = Ref::new(4);
    let font_id = Ref::new(5);
    let cidfont_id = Ref::new(6);
    let descriptor_id = Ref::new(7);
    let fontfile_id = Ref::new(8);
    let cid_to_gid_id = Ref::new(9);
    let to_unicode_id = Ref::new(10);
    let info_id = Ref::new(11);

    pdf.catalog(catalog_id).pages(page_tree_id);
    pdf.pages(page_tree_id).kids([page_id]).count(1);

    // font file
    let mut fontfile = pdf.stream(fontfile_id, &font_bytes);
    fontfile.pair(Name(b"Length1"), font_bytes.len() as i32);
    fontfile.finish();
    breakdown.push(("font_file2".into(), font_bytes.len() as u64));

    // font descriptor
    let mut bbox = [i16::MAX, i16::MAX, i16::MIN, i16::MIN];
    for s in shapes {
        bbox[0] = bbox[0].min(s.bbox_fu[0] as i16);
        bbox[1] = bbox[1].min(s.bbox_fu[1] as i16);
        bbox[2] = bbox[2].max(s.bbox_fu[2] as i16);
        bbox[3] = bbox[3].max(s.bbox_fu[3] as i16);
    }
    if bbox[0] > bbox[2] {
        bbox = [0, 0, 0, 0];
    }
    pdf.font_descriptor(descriptor_id)
        .name(Name(b"ScanWeaveM0Probe"))
        .flags(pdf_writer::types::FontFlags::SYMBOLIC)
        .bbox(Rect::new(
            bbox[0] as f32,
            bbox[1] as f32,
            bbox[2] as f32,
            bbox[3] as f32,
        ))
        .italic_angle(0.0)
        .ascent(bbox[3] as f32)
        .descent(bbox[1] as f32)
        .cap_height(bbox[3] as f32)
        .stem_v(80.0)
        .font_file2(fontfile_id);

    // CIDToGIDMap stream: 2 bytes per CID; CID 0 is reserved for .notdef (GID 0),
    // allocated CIDs start at 1 (PDF spec: CID 0 shall be reserved)
    let mut map_bytes = vec![0u8, 0u8];
    for (glyph_idx, _) in encodings {
        let gid = glyph_idx + 1; // 0 = notdef
        map_bytes.push((gid >> 8) as u8);
        map_bytes.push((gid & 0xFF) as u8);
    }
    pdf.stream(cid_to_gid_id, &map_bytes).finish();
    breakdown.push(("cid_to_gid_map".into(), map_bytes.len() as u64));

    // descendant CIDFont
    let dw = 1000.0f32;
    {
        let mut cid = pdf.cid_font(cidfont_id);
        cid.subtype(CidFontType::Type2)
            .base_font(Name(b"ScanWeaveM0Probe"))
            .system_info(SystemInfo {
                registry: Str(b"Adobe"),
                ordering: Str(b"Identity"),
                supplement: 0,
            })
            .font_descriptor(descriptor_id)
            .default_width(dw)
            .cid_to_gid_map_stream(cid_to_gid_id);
        // W array: per-CID widths in PDF glyph units (1000 per em)
        let mut w = cid.widths();
        for (cid_index, (glyph_idx, _)) in encodings.iter().enumerate() {
            let s = &shapes[*glyph_idx];
            let w_units_1000 = ((s.bbox_fu[2] - s.bbox_fu[0]).ceil().max(1.0) + 2.0) * 1000.0 / upem as f64;
            w.consecutive(cid_index as u16 + 1, [w_units_1000 as f32]);
        }
        w.finish();
    }

    // ToUnicode CMap (UTF-16BE, multi-codepoint and supplementary-plane safe)
    let mut cmap = String::new();
    cmap.push_str("/CIDInit /ProcSet findresource begin\n");
    cmap.push_str("12 dict begin\nbegincmap\n");
    cmap.push_str("/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n");
    cmap.push_str("/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n");
    // codespace must cover all allocated CIDs (1..=len); a range ending at 0000
    // makes every real CID out-of-codespace and renderers drop the text
    cmap.push_str(&format!(
        "1 begincodespacerange\n<0000> <{:04X}>\nendcodespacerange\n",
        encodings.len()
    ));
    if !encodings.is_empty() {
        cmap.push_str(&format!("{} beginbfchar\n", encodings.len()));
        for (cid, (_, semantic)) in encodings.iter().enumerate() {
            cmap.push_str(&format!(
                "<{:04X}> <{}>\n",
                cid + 1,
                utf16be_hex(semantic)
            ));
        }
        cmap.push_str("endbfchar\n");
    }
    cmap.push_str("endcmap\nCMapName currentdict /CMap defineresource pop\nend end\n");
    pdf.stream(to_unicode_id, cmap.as_bytes()).finish();
    breakdown.push(("to_unicode_cmap".into(), cmap.as_bytes().len() as u64));

    // Type 0 font
    let mut type0 = pdf.type0_font(font_id);
    type0
        .base_font(Name(b"ScanWeaveM0Probe"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(cidfont_id)
        .to_unicode(to_unicode_id);
    type0.finish();

    // content stream
    let mut content = Content::new();
    // paper background (probe pages are locally simple; sampled, never whitened)
    content.set_fill_rgb(
        paper[0] as f32 / 255.0,
        paper[1] as f32 / 255.0,
        paper[2] as f32 / 255.0,
    );
    content.rect(0.0, 0.0, page_w_pt, page_h_pt);
    content.fill_nonzero();
    // glyph fill uses the SAMPLED source ink colour (never pure black by default:
    // repainting gray-30 source ink as pure black is a visible colour change —
    // caught by the M0-Q whole-page MAE gate)
    content.set_fill_rgb(
        ink[0] as f32 / 255.0,
        ink[1] as f32 / 255.0,
        ink[2] as f32 / 255.0,
    );

    // unowned ink: vector artwork paths (no text semantics, no invented Unicode)
    for (glyph_idx, bbox_px) in artwork {
        let s = &shapes[*glyph_idx];
        let Some(polys) = contour_polylines.get(&s.shape_key) else {
            continue;
        };
        let x0 = bbox_px[0] as f32 * 72.0 / 300.0;
        let x1 = bbox_px[2] as f32 * 72.0 / 300.0;
        let y0_px = bbox_px[1] as f32;
        let y1_px = bbox_px[3] as f32;
        let bottom_pt = page_h_pt - y1_px * 72.0 / 300.0;
        let w_pt = x1 - x0;
        let h_pt = (y1_px - y0_px) * 72.0 / 300.0;
        let inv = 1.0 / crate::trace::SS as f32;
        let sx = w_pt / (s.ink_span_fu[0] as f32 * inv);
        let sy = h_pt / (s.ink_span_fu[1] as f32 * inv);
        content.save_state();
        content.transform([sx, 0.0, 0.0, sy, x0, bottom_pt]);
        for poly in polys {
            if poly.len() < 3 {
                continue;
            }
            content.move_to(poly[0][0] as f32, poly[0][1] as f32);
            for pt in &poly[1..] {
                content.line_to(pt[0] as f32, pt[1] as f32);
            }
            content.close_path();
        }
        content.fill_nonzero();
        content.restore_state();
    }

    content.begin_text();
    content.set_font(Name(b"F1"), 1.0);
    for (glyph_idx, cid, bbox_px, _span, _symbol, _text) in occurrences {
        let s = &shapes[*glyph_idx];
        // source bbox px -> page pt (y flip)
        let x0 = bbox_px[0] as f32 * 72.0 / 300.0;
        let x1 = bbox_px[2] as f32 * 72.0 / 300.0;
        let y0_px = bbox_px[1] as f32;
        let y1_px = bbox_px[3] as f32;
        let bottom_pt = page_h_pt - y1_px * 72.0 / 300.0;
        let top_pt = page_h_pt - y0_px * 72.0 / 300.0;
        let w_pt = x1 - x0;
        let h_pt = top_pt - bottom_pt;
        // glyph ink bbox in font units (baseline at ink bottom)
        // SCALE from the construction box (ink touches the crop edges, so the
        // ink size in font units is exactly cw*k x ch*k); TRANSLATION corrected
        // by the outline's actual on-curve extremes (the traced contour may sit
        // sub-pixel inside the construction box on a given edge). Renderers
        // scale TrueType glyph units by unitsPerEm into the 1000-unit PDF
        // glyph space (measured behaviour).
        let gx_span = s.ink_span_fu[0] as f32;
        let gy_span = s.ink_span_fu[1] as f32;
        let sx = w_pt * upem / gx_span.max(1.0);
        let sy = h_pt * upem / gy_span.max(1.0);
        let tx = x0 - (s.anchor_bbox_fu[0] as f32) * sx / upem;
        let ty = bottom_pt - (s.anchor_bbox_fu[1] as f32) * sy / upem;
        content.set_text_matrix([sx, 0.0, 0.0, sy, tx, ty]);
        content.show(Str(&cid_utf16be(*cid)));
    }
    content.end_text();
    let content_bytes = content.finish();
    pdf.stream(content_id, &content_bytes).finish();
    breakdown.push(("content_stream".into(), content_bytes.len() as u64));

    // page
    let mut page = pdf.page(page_id);
    page.parent(page_tree_id)
        .media_box(Rect::new(0.0, 0.0, page_w_pt, page_h_pt))
        .contents(content_id);
    let mut resources = page.resources();
    resources.fonts().pair(Name(b"F1"), font_id);
    resources.finish();
    page.finish();

    let mut doc = pdf.document_info(info_id);
    doc.producer(TextStr("scanweave-m0-probe"));
    doc.finish();

    let bytes = pdf.finish();
    let total = bytes.len() as u64;
    let streams: u64 = breakdown.iter().map(|(_, n)| n).sum();
    breakdown.push(("xref_dicts_overhead".into(), total.saturating_sub(streams)));
    breakdown.push(("total".into(), total));
    Ok((bytes, breakdown))
}

fn cid_utf16be(cid: usize) -> Vec<u8> {
    // Identity-H: 2-byte CIDs; +1 because CID 0 is reserved for .notdef
    let cid = cid + 1;
    vec![(cid >> 8) as u8, (cid & 0xFF) as u8]
}
