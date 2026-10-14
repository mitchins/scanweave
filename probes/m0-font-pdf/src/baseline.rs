//! B0 — searchable raster control: canonical full-page raster (Flate RGB) plus
//! invisible text (rendering mode 3) using the same embedded font and supplied
//! OCR geometry. This is the utility's own safety baseline (SPEC §5.1, §6.2).

use crate::glyphs::GlyphShape;
use pdf_writer::{Chunk, Content, Finish, Name, Pdf, Ref, Rect, Str, TextStr};
use pdf_writer::types::TextRenderingMode;
use std::io::Write;

fn utf16be_hex(s: &str) -> String {
    let mut out = String::new();
    for unit in s.encode_utf16() {
        out.push_str(&format!("{unit:04X}"));
    }
    out
}

#[allow(clippy::too_many_arguments)]
pub fn assemble_raster(
    rgb: &[u8],
    width: u32,
    height: u32,
    encodings: &[(usize, String)],
    occurrences: &[(usize, usize, [f64; 4], String, String, String)],
    page_w_pt: f32,
    page_h_pt: f32,
    font_bytes: Vec<u8>,
    shapes: &[GlyphShape],
    span_texts: &std::collections::HashMap<String, String>,
) -> Result<(Vec<u8>, Vec<(String, u64)>), String> {
    let upem = 2048.0f32;
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
    let image_id = Ref::new(11);
    let info_id = Ref::new(12);

    pdf.catalog(catalog_id).pages(page_tree_id);
    pdf.pages(page_tree_id).kids([page_id]).count(1);
    let mut breakdown: Vec<(String, u64)> = Vec::new();

    // page image: Flate RGB
    let mut enc = flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
    enc.write_all(rgb).map_err(|e| e.to_string())?;
    let compressed = enc.finish().map_err(|e| e.to_string())?;
    breakdown.push(("page_image_flate".into(), compressed.len() as u64));
    let mut img = pdf.stream(image_id, &compressed);
    img.pair(Name(b"Type"), Name(b"XObject"));
    img.pair(Name(b"Subtype"), Name(b"Image"));
    img.pair(Name(b"Width"), width as i32);
    img.pair(Name(b"Height"), height as i32);
    img.pair(Name(b"ColorSpace"), Name(b"DeviceRGB"));
    img.pair(Name(b"BitsPerComponent"), 8);
    img.pair(Name(b"Filter"), Name(b"FlateDecode"));
    img.finish();

    let mut fontfile = pdf.stream(fontfile_id, &font_bytes);
    fontfile.pair(Name(b"Length1"), font_bytes.len() as i32);
    fontfile.finish();

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

    let mut map_bytes = vec![0u8, 0u8];
    for (glyph_idx, _) in encodings {
        let gid = glyph_idx + 1;
        map_bytes.push((gid >> 8) as u8);
        map_bytes.push((gid & 0xFF) as u8);
    }
    pdf.stream(cid_to_gid_id, &map_bytes).finish();

    let mut cmap = String::from(
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n",
    );
    cmap.push_str(&format!(
        "1 begincodespacerange\n<0000> <{:04X}>\nendcodespacerange\n",
        encodings.len()
    ));
    if !encodings.is_empty() {
        cmap.push_str(&format!("{} beginbfchar\n", encodings.len()));
        for (cid, (_, semantic)) in encodings.iter().enumerate() {
            cmap.push_str(&format!("<{:04X}> <{}>\n", cid + 1, utf16be_hex(semantic)));
        }
        cmap.push_str("endbfchar\n");
    }
    cmap.push_str("endcmap\nCMapName currentdict /CMap defineresource pop\nend end\n");
    pdf.stream(to_unicode_id, cmap.as_bytes()).finish();

    let mut cid = pdf.cid_font(cidfont_id);
    cid.subtype(pdf_writer::types::CidFontType::Type2)
        .base_font(Name(b"ScanWeaveM0Probe"))
        .system_info(pdf_writer::types::SystemInfo {
            registry: Str(b"Adobe"),
            ordering: Str(b"Identity"),
            supplement: 0,
        })
        .font_descriptor(descriptor_id)
        .default_width(1000.0)
        .cid_to_gid_map_stream(cid_to_gid_id);
    cid.finish();

    let mut type0 = pdf.type0_font(font_id);
    type0
        .base_font(Name(b"ScanWeaveM0Probe"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(cidfont_id)
        .to_unicode(to_unicode_id);
    type0.finish();

    // content: page image, then invisible text (Tr 3)
    let mut content = Content::new();
    content.save_state();
    content.transform([page_w_pt, 0.0, 0.0, page_h_pt, 0.0, 0.0]);
    content.x_object(Name(b"Im0"));
    content.restore_state();
    content.begin_text();
    content.set_font(Name(b"F1"), 1.0);
    content.set_text_rendering_mode(TextRenderingMode::Invisible);
    for (glyph_idx, cid, bbox_px, _span, _symbol, _text) in occurrences {
        let s = &shapes[*glyph_idx];
        let x0 = bbox_px[0] as f32 * 72.0 / 300.0;
        let x1 = bbox_px[2] as f32 * 72.0 / 300.0;
        let y0_px = bbox_px[1] as f32;
        let y1_px = bbox_px[3] as f32;
        let bottom_pt = page_h_pt - y1_px * 72.0 / 300.0;
        let top_pt = page_h_pt - y0_px * 72.0 / 300.0;
        let w_pt = x1 - x0;
        let h_pt = top_pt - bottom_pt;
        let gx_span = s.ink_span_fu[0];
        let gy_span = s.ink_span_fu[1];
        let sx = w_pt * upem / (gx_span as f32).max(1.0);
        let sy = h_pt * upem / (gy_span as f32).max(1.0);
        content.set_text_matrix([sx, 0.0, 0.0, sy, x0, bottom_pt]);
        let c = cid + 1;
        content.show(Str(&[(c >> 8) as u8, (c & 0xFF) as u8]));
    }
    content.end_text();
    let content_bytes = content.finish();
    pdf.stream(content_id, &content_bytes).finish();

    let mut page = pdf.page(page_id);
    page.parent(page_tree_id)
        .media_box(Rect::new(0.0, 0.0, page_w_pt, page_h_pt))
        .contents(content_id);
    let mut resources = page.resources();
    resources.fonts().pair(Name(b"F1"), font_id);
    resources
        .x_objects()
        .pair(Name(b"Im0"), image_id);
    resources.finish();
    page.finish();

    let mut doc = pdf.document_info(info_id);
    doc.producer(TextStr("scanweave-m0-probe-b0"));
    doc.finish();

    let bytes = pdf.finish();
    breakdown.push(("font_file2".into(), font_bytes.len() as u64));
    breakdown.push(("cid_to_gid_map".into(), map_bytes.len() as u64));
    breakdown.push(("to_unicode_cmap".into(), cmap.as_bytes().len() as u64));
    breakdown.push(("content_stream".into(), content_bytes.len() as u64));
    let total = bytes.len() as u64;
    let streams: u64 = breakdown.iter().map(|(_, n)| n).sum();
    breakdown.push(("xref_dicts_overhead".into(), total.saturating_sub(streams)));
    breakdown.push(("total".into(), total));
    Ok((bytes, breakdown))
}
