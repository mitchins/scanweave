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
use sha2::{Digest, Sha256};
use std::collections::HashMap;

use crate::glyphs::GlyphShape;

/// Lossless representation only: decoded bytes and text ownership are unchanged.
fn compressed_stream(pdf: &mut Pdf, id: Ref, data: &[u8], font: bool) -> Result<usize, String> {
    let encoded = crate::serialization::deflate(data)?;
    let mut stream = pdf.stream(id, &encoded);
    stream.filter(pdf_writer::Filter::FlateDecode);
    if font {
        stream.pair(Name(b"Length1"), data.len() as i32);
    }
    stream.finish();
    Ok(encoded.len())
}

#[derive(Debug, Default, Clone)]
pub struct Patch {
    pub bbox_px: [f64; 4],
    pub rgb: Vec<u8>,
    pub w: u32,
    pub h: u32,
    /// Only a reduced ClearScan background may use a bounded-error codec.
    pub compact_background: bool,
}

/// Native raster serialization choices. Assembly uses exact
/// resource reuse and grayscale storage when the decoded RGB samples prove
/// equal. Reduced ClearScan backgrounds separately permit bounded-error JPEG.
/// The explicit switches also support reproducible ablation PDFs.
#[derive(Debug, Clone, Copy, serde::Serialize)]
pub struct ImageEncodingOptions {
    pub reuse_identical: bool,
    pub grayscale_equal_channels: bool,
    pub compression_level: u32,
    /// PDF predictor: 0 (smallest of lossless variants), 1 (none), 2 (TIFF), or 12 (PNG Up).
    pub predictor: u8,
}

impl Default for ImageEncodingOptions {
    fn default() -> Self {
        Self {
            reuse_identical: true,
            grayscale_equal_channels: true,
            compression_level: 6,
            predictor: 1,
        }
    }
}

#[derive(Debug, Clone, Eq)]
struct ImageResourceKey {
    width: u32,
    height: u32,
    bits_per_component: u8,
    color_space: u8, // 1 = DeviceGray, 3 = DeviceRGB
    compression_level: u32,
    predictor: u8,
    compact_background: bool,
    sample_sha256: [u8; 32],
    samples: Vec<u8>,
}

impl PartialEq for ImageResourceKey {
    fn eq(&self, other: &Self) -> bool {
        self.width == other.width
            && self.height == other.height
            && self.bits_per_component == other.bits_per_component
            && self.color_space == other.color_space
            && self.compression_level == other.compression_level
            && self.predictor == other.predictor
            && self.compact_background == other.compact_background
            && self.sample_sha256 == other.sample_sha256
            && self.samples == other.samples
    }
}

#[derive(Debug)]
struct EncodedImageResource {
    id: Ref,
    key: ImageResourceKey,
    compressed: Vec<u8>,
    jpeg: bool,
    predictor: u8,
}

fn canonical_patch(
    patch: &Patch,
    options: ImageEncodingOptions,
) -> Result<ImageResourceKey, String> {
    let expected = (patch.w as usize)
        .checked_mul(patch.h as usize)
        .and_then(|n| n.checked_mul(3))
        .ok_or_else(|| "image patch dimensions overflow addressable memory".to_string())?;
    if patch.w == 0 || patch.h == 0 {
        return Err("image patch dimensions must be nonzero".into());
    }
    if patch.rgb.len() != expected {
        return Err(format!(
            "image patch sample length mismatch: {}x{} requires {expected} RGB bytes, got {}",
            patch.w,
            patch.h,
            patch.rgb.len()
        ));
    }
    let is_gray = options.grayscale_equal_channels
        && patch
            .rgb
            .as_chunks::<3>().0.iter()
            .all(|p| p[0] == p[1] && p[1] == p[2]);
    let samples = if is_gray {
        patch.rgb.as_chunks::<3>().0.iter().map(|p| p[0]).collect::<Vec<_>>()
    } else {
        patch.rgb.clone()
    };
    if is_gray
        && samples
            .iter()
            .zip(patch.rgb.as_chunks::<3>().0.iter())
            .any(|(g, rgb)| *g != rgb[0] || rgb[0] != rgb[1] || rgb[1] != rgb[2])
    {
        return Err("DeviceGray expansion check failed".into());
    }
    let mut digest = Sha256::new();
    digest.update(patch.w.to_be_bytes());
    digest.update(patch.h.to_be_bytes());
    digest.update([8, if is_gray { 1 } else { 3 }]);
    digest.update(options.compression_level.min(9).to_be_bytes());
    digest.update([options.predictor, patch.compact_background as u8]);
    digest.update(&samples);
    let sample_sha256: [u8; 32] = digest.finalize().into();
    Ok(ImageResourceKey {
        width: patch.w,
        height: patch.h,
        bits_per_component: 8,
        color_space: if is_gray { 1 } else { 3 },
        compression_level: options.compression_level.min(9),
        predictor: options.predictor,
        compact_background: patch.compact_background,
        sample_sha256,
        samples,
    })
}

fn encode_predictor_value(key: &ImageResourceKey, predictor: u8) -> Result<Vec<u8>, String> {
    let colors = key.color_space as usize;
    let row_bytes = key.width as usize * colors;
    match predictor {
        1 => Ok(key.samples.clone()),
        2 | 12 => {
            if key.samples.len() != row_bytes * key.height as usize {
                return Err("predictor input does not match image dimensions".into());
            }
            let mut out = Vec::with_capacity(
                key.samples.len()
                    + if predictor == 12 {
                        key.height as usize
                    } else {
                        0
                    },
            );
            for y in 0..key.height as usize {
                let row = &key.samples[y * row_bytes..(y + 1) * row_bytes];
                if predictor == 12 {
                    out.push(2);
                } // PNG Up row selector
                for x in 0..row_bytes {
                    let prior = if predictor == 2 && x >= colors {
                        row[x - colors]
                    } else if predictor == 12 && y > 0 {
                        key.samples[(y - 1) * row_bytes + x]
                    } else {
                        0
                    };
                    out.push(row[x].wrapping_sub(prior));
                }
            }
            Ok(out)
        }
        other => Err(format!(
            "unsupported PDF image predictor {other}; supported values are 1, 2, 12"
        )),
    }
}

fn compress_samples(key: &ImageResourceKey) -> Result<(Vec<u8>, bool, u8), String> {
    let candidates: &[u8] = if key.predictor == 0 {
        &[1, 2, 12]
    } else {
        std::slice::from_ref(&key.predictor)
    };
    let mut lossless = Vec::new();
    let mut selected_predictor = 1;
    for &predictor in candidates {
        let predicted = encode_predictor_value(key, predictor)?;
        let mut enc = flate2::write::ZlibEncoder::new(
            Vec::new(),
            flate2::Compression::new(key.compression_level.min(9)),
        );
        use std::io::Write;
        enc.write_all(&predicted).map_err(|e| e.to_string())?;
        let encoded = enc.finish().map_err(|e| e.to_string())?;
        if lossless.is_empty() || encoded.len() < lossless.len() {
            lossless = encoded;
            selected_predictor = predictor;
        }
    }
    // Only the already-qualified reduced paper background may be lossy.
    // Native text/artwork/unknown samples remain lossless.
    if key.compact_background {
        for quality in [95, 98, 100] {
            let mut jpeg = Vec::new();
            let color = if key.color_space == 1 {
                image::ExtendedColorType::L8
            } else {
                image::ExtendedColorType::Rgb8
            };
            image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, quality)
                .encode(&key.samples, key.width, key.height, color)
                .map_err(|e| e.to_string())?;
            if jpeg.len() * 10 >= lossless.len() * 9 {
                continue;
            }
            let decoded = image::load_from_memory_with_format(&jpeg, image::ImageFormat::Jpeg)
                .map_err(|e| e.to_string())?;
            let samples = if key.color_space == 1 {
                decoded.to_luma8().into_raw()
            } else {
                decoded.to_rgb8().into_raw()
            };
            let mut max_error = 0u8;
            let mut sum_error = 0u64;
            for (&a, &b) in key.samples.iter().zip(&samples) {
                let error = a.abs_diff(b);
                max_error = max_error.max(error);
                sum_error += error as u64;
            }
            if samples.len() == key.samples.len()
                && max_error <= 3
                && sum_error as f64 <= key.samples.len() as f64 * 0.25
            {
                return Ok((jpeg, true, 1));
            }
        }
    }
    Ok((lossless, false, selected_predictor))
}

/// Compare actual lossless stream costs for two existing residual layouts.
/// No resampling, atlas coordinates or new source pixels are introduced.
pub(crate) fn lossless_patch_cost(patches: &[Patch]) -> Result<usize, String> {
    let options = ImageEncodingOptions {
        predictor: 0,
        ..Default::default()
    };
    let mut cost = 0usize;
    for patch in patches {
        let mut key = canonical_patch(patch, options)?;
        key.compact_background = false;
        cost += compress_samples(&key)?.0.len();
    }
    Ok(cost)
}

#[derive(Debug, Default, Clone)]
pub struct OwnerCharacter {
    pub cid: u32,
    pub bbox_px: [f64; 4],
    pub order: usize,
}

#[derive(Debug, Default, Clone)]
pub struct Owner {
    pub text: String,
    /// the OCR span polygon box (reporting)
    pub bbox_px: [f64; 4],
    /// ink-derived placement box: the first traced unit's ink bbox of the span.
    /// The owner run is placed on THIS baseline: extractors merge runs into a
    /// line by baseline and then sort by x, so a span-box-derived baseline
    /// (which sits off the glyph ink baseline) creates a separate line and the
    /// label is appended out of order (the real M1-A N1 mechanism).
    pub place_px: [f64; 4],
    /// the OCR span this owner overlays (reading-order marks need the span id)
    pub span_id: String,
    pub characters: Vec<OwnerCharacter>,
    pub visible_order: std::collections::BTreeMap<String, usize>,
}

fn cid_advance(shapes: &[GlyphShape], encodings: &[(usize, String)], cid: u32) -> f32 {
    encodings
        .get(cid.saturating_sub(1) as usize)
        .and_then(|e| shapes.get(e.0))
        .map(|g| ((g.ink_span_fu[0].ceil().max(1.0) + 2.0) / 2048.0) as f32)
        .unwrap_or(0.5)
}

fn emit_owner_characters(
    c: &mut Content,
    characters: &[OwnerCharacter],
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    xf: &PageTransform,
) {
    c.set_text_rendering_mode(TextRenderingMode::Invisible);
    for ch in characters {
        let b = ch.bbox_px;
        let height = ((b[3] - b[1]) * xf.sy()).max(0.1) as f32;
        let width = ((b[2] - b[0]) * xf.sx()).max(0.01) as f32;
        let glyph = encodings
            .get(ch.cid.saturating_sub(1) as usize)
            .and_then(|e| shapes.get(e.0));
        // An observed glyph need not be one em tall: the first glyph may be a
        // tiny punctuation mark. Fit its real font frame rather than assuming
        // font size equals source ink height (which made native boxes vanish).
        let frame = glyph.map(|g| g.bbox_fu).unwrap_or([4.0, 4.0, 200.0, 200.0]);
        let horizontal = width / cid_advance(shapes, encodings, ch.cid).max(0.0001);
        let vertical = height * 2048.0 / (frame[3] - frame[1]).max(1.0) as f32;
        let tx = xf.x(b[0]) - frame[0] as f32 * horizontal / 2048.0;
        let ty = xf.y(b[3]) - frame[1] as f32 * vertical / 2048.0;
        c.set_font(Name(b"F1"), 1.0);
        c.set_text_matrix([horizontal, 0.0, 0.0, vertical, tx, ty]);
        c.show(Str(&[(ch.cid >> 8) as u8, (ch.cid & 0xff) as u8]));
    }
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

/// Draw the paper fill and the raster patches (source-exact crops), in order.
fn emit_patches(
    c: &mut Content,
    patches: &[Patch],
    xf: &PageTransform,
    page_w_pt: f32,
    page_h_pt: f32,
    paper: [u8; 3],
) {
    c.set_fill_rgb(
        paper[0] as f32 / 255.0,
        paper[1] as f32 / 255.0,
        paper[2] as f32 / 255.0,
    );
    c.rect(0.0, 0.0, page_w_pt, page_h_pt);
    c.fill_nonzero();
    for (i, patch) in patches.iter().enumerate() {
        let x = xf.x(patch.bbox_px[0]);
        let y_bot = xf.y(patch.bbox_px[3]);
        let w_pt = (patch.bbox_px[2] - patch.bbox_px[0]) * xf.sx();
        let h_pt = (patch.bbox_px[3] - patch.bbox_px[1]) * xf.sy();
        c.save_state();
        c.transform([w_pt as f32, 0.0, 0.0, h_pt as f32, x, y_bot]);
        let name = format!("Im{i}");
        c.x_object(Name(name.as_bytes()));
        c.restore_state();
    }
}

/// Emit the page's text layer: visible vector glyph runs in reading order with
/// per-span /ActualText (BMP only; astral spans keep per-glyph ToUnicode), and
/// the invisible fallback owner runs inline in reading order on the span's
/// traced ink baseline, each with its own per-span /ActualText.
// A repaired/absorbed occurrence need not remain adjacent to its original
// word's other occurrences. Group by semantic span identity, preserving first
// appearance and per-span order; never silently paint only the first run.
fn occurrence_groups(occurrences: &[Occurrence]) -> Vec<Vec<usize>> {
    let mut groups: Vec<Vec<usize>> = Vec::new();
    let mut indices = HashMap::new();
    for (i, occurrence) in occurrences.iter().enumerate() {
        let index = *indices.entry(occurrence.3.as_str()).or_insert_with(|| {
            groups.push(Vec::new());
            groups.len() - 1
        });
        groups[index].push(i);
    }
    groups
}

#[allow(clippy::too_many_arguments)]
fn emit_text_runs(
    c: &mut Content,
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    occurrences: &[Occurrence],
    span_texts: &[(String, String)],
    owners: &[Owner],
    owner_cids: &[u32],
    lines: &[LineSpec],
    xf: &PageTransform,
    ink: [u8; 3],
    raster_baseline: bool,
) {
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
    let groups = occurrence_groups(occurrences);

    c.begin_text();
    c.set_font(Name(b"F1"), 1.0);
    c.set_fill_rgb(
        ink[0] as f32 / 255.0,
        ink[1] as f32 / 255.0,
        ink[2] as f32 / 255.0,
    );
    // raster-baseline candidates paint NO text: the whole-page source patch
    // carries the pixels, the text layer only carries the searchable labels
    if raster_baseline {
        c.set_text_rendering_mode(TextRenderingMode::Invisible);
    }

    let mut emitted_spans: std::collections::HashSet<String> = std::collections::HashSet::new();

    for line in lines {
        for sid in &line.spans {
            emitted_spans.insert(sid.clone());
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
                let partial_owner = owner_by_span.get(span_id).map(|(owner, _)| *owner);
                let missing = owner_by_span
                    .get(span_id)
                    .map(|(owner, _)| owner.characters.as_slice())
                    .unwrap_or(&[]);
                let mut missing_cursor = 0;
                let mut ordered = group.clone();
                if let Some(owner) = partial_owner {
                    if !owner.visible_order.is_empty() {
                        ordered.sort_by_key(|&i| {
                            owner
                                .visible_order
                                .get(&occurrences[i].4)
                                .copied()
                                .unwrap_or(usize::MAX)
                        });
                    }
                }
                for &i in &ordered {
                    let (gidx, cid, bbox_px, _, _, _) = &occurrences[i];
                    while missing_cursor < missing.len()
                        && missing[missing_cursor].order
                            < partial_owner
                                .and_then(|o| o.visible_order.get(&occurrences[i].4))
                                .copied()
                                .unwrap_or(usize::MAX)
                    {
                        emit_owner_characters(
                            c,
                            &missing[missing_cursor..missing_cursor + 1],
                            shapes,
                            encodings,
                            xf,
                        );
                        missing_cursor += 1;
                    }
                    if !missing.is_empty() {
                        c.set_font(Name(b"F1"), 1.0);
                        c.set_text_rendering_mode(if raster_baseline {
                            TextRenderingMode::Invisible
                        } else {
                            TextRenderingMode::Fill
                        });
                    }
                    let g = &shapes[*gidx];
                    let x0 = xf.x(bbox_px[0]);
                    let bottom_pt = xf.y(bbox_px[3]);
                    let w_pt = ((bbox_px[2] - bbox_px[0]) * xf.sx()) as f32;
                    let h_pt = ((bbox_px[3] - bbox_px[1]) * xf.sy()) as f32;
                    let sx = w_pt * 2048.0 / g.ink_span_fu[0].max(1.0) as f32;
                    let sy = h_pt * 2048.0 / g.ink_span_fu[1].max(1.0) as f32;
                    let tx = x0 - (g.anchor_bbox_fu[0] as f32) * sx / 2048.0;
                    let ty = bottom_pt - (g.anchor_bbox_fu[1] as f32) * sy / 2048.0;
                    c.set_text_matrix([sx, 0.0, 0.0, sy, tx, ty]);
                    let cid = *cid + 1;
                    c.show(Str(&[(cid >> 8) as u8, (cid & 0xFF) as u8]));
                }
                if missing_cursor < missing.len() {
                    emit_owner_characters(c, &missing[missing_cursor..], shapes, encodings, xf);
                    c.set_font(Name(b"F1"), 1.0);
                    c.set_text_rendering_mode(if raster_baseline {
                        TextRenderingMode::Invisible
                    } else {
                        TextRenderingMode::Fill
                    });
                }
                if !astral {
                    c.end_marked_content();
                }
            } else if let Some((owner, cid)) = owner_by_span.get(sid.as_str()) {
                let owner_text = span_map.get(sid.as_str()).copied().unwrap_or("");
                let astral = owner_text.chars().any(|c| (c as u32) > 0xFFFF);
                if !astral {
                    let mut mc = c.begin_marked_content_with_properties(Name(b"Span"));
                    let mut pl = mc.properties();
                    pl.actual_text(TextStr(owner_text));
                }
                if !owner.characters.is_empty() {
                    emit_owner_characters(c, &owner.characters, shapes, encodings, xf);
                    c.set_text_rendering_mode(if raster_baseline {
                        TextRenderingMode::Invisible
                    } else {
                        TextRenderingMode::Fill
                    });
                    c.set_font(Name(b"F1"), 1.0);
                    if !astral {
                        c.end_marked_content();
                    }
                    continue;
                }
                let y_bot = xf.y(owner.place_px[3]);
                let h_pt = ((owner.place_px[3] - owner.place_px[1]) * xf.sy()) as f32;
                let h_pt = h_pt.max(4.0);
                let x0 = xf.x(owner.place_px[0]);
                let cx = *cid;
                let bytes = Str(&[(cx >> 8) as u8, (cx & 0xFF) as u8]);
                c.set_text_rendering_mode(TextRenderingMode::Invisible);
                c.set_font(Name(b"F1"), h_pt);
                c.set_text_matrix([1.0, 0.0, 0.0, 1.0, x0, y_bot]);
                c.show(bytes);
                // restore the layer's mode: Fill normally, Invisible for the
                // raster-baseline candidates (whose whole layer paints nothing)
                c.set_text_rendering_mode(if raster_baseline {
                    TextRenderingMode::Invisible
                } else {
                    TextRenderingMode::Fill
                });
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
            let x0 = xf.x(bbox_px[0]);
            let bottom_pt = xf.y(bbox_px[3]);
            let w_pt = ((bbox_px[2] - bbox_px[0]) * xf.sx()) as f32;
            let h_pt = ((bbox_px[3] - bbox_px[1]) * xf.sy()) as f32;
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
        if !owner.characters.is_empty() {
            emit_owner_characters(c, &owner.characters, shapes, encodings, xf);
            c.set_text_rendering_mode(if raster_baseline {
                TextRenderingMode::Invisible
            } else {
                TextRenderingMode::Fill
            });
            c.set_font(Name(b"F1"), 1.0);
            continue;
        }
        let y_bot = xf.y(owner.place_px[3]);
        let h_pt = (((owner.place_px[3] - owner.place_px[1]) * xf.sy()) as f32).max(4.0);
        let x0 = xf.x(owner.place_px[0]);
        let cx = *cid;
        let bytes = Str(&[(cx >> 8) as u8, (cx & 0xFF) as u8]);
        c.set_text_rendering_mode(TextRenderingMode::Invisible);
        c.set_font(Name(b"F1"), h_pt);
        c.set_text_matrix([1.0, 0.0, 0.0, 1.0, x0, y_bot]);
        c.show(bytes);
        c.set_text_rendering_mode(if raster_baseline {
            TextRenderingMode::Invisible
        } else {
            TextRenderingMode::Fill
        });
        c.set_font(Name(b"F1"), 1.0);
    }
}

#[allow(clippy::too_many_arguments)]
pub fn assemble(
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    occurrences: &[Occurrence],
    span_texts: &[(String, String)],
    page_w_pt: f32,
    page_h_pt: f32,
    paper: [u8; 3],
    ink: [u8; 3],
    font_bytes: Vec<u8>,
    glyphless_bytes: Vec<u8>,
    glyphless_encodings: &[(usize, String)],
    patches: &[Patch],
    owners: &[Owner],
    owner_cids: &[u32],
    lines: &[LineSpec],
    to_pt: &PageTransform,
) -> Result<Vec<u8>, String> {
    assemble_with_options(
        shapes,
        encodings,
        occurrences,
        span_texts,
        page_w_pt,
        page_h_pt,
        paper,
        ink,
        font_bytes,
        glyphless_bytes,
        glyphless_encodings,
        patches,
        owners,
        owner_cids,
        lines,
        to_pt,
        ImageEncodingOptions::default(),
    )
}

#[allow(clippy::too_many_arguments)]
pub fn assemble_with_options(
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    occurrences: &[Occurrence],
    span_texts: &[(String, String)],
    page_w_pt: f32,
    page_h_pt: f32,
    paper: [u8; 3],
    ink: [u8; 3],
    font_bytes: Vec<u8>,
    glyphless_bytes: Vec<u8>,
    glyphless_encodings: &[(usize, String)],
    patches: &[Patch],
    owners: &[Owner],
    owner_cids: &[u32],
    lines: &[LineSpec],
    to_pt: &PageTransform,
    image_options: ImageEncodingOptions,
) -> Result<Vec<u8>, String> {
    let _ = glyphless_bytes;
    validate_occurrence_geometry(occurrences)?;
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

    let mut image_resources: Vec<EncodedImageResource> = Vec::new();
    let mut resource_lookup: HashMap<[u8; 32], Vec<usize>> = HashMap::new();
    let mut image_ids = Vec::with_capacity(patches.len());
    for patch in patches {
        let key = canonical_patch(patch, image_options)?;
        let existing = if image_options.reuse_identical {
            resource_lookup
                .get(&key.sample_sha256)
                .and_then(|candidates| {
                    candidates
                        .iter()
                        .copied()
                        .find(|&i| image_resources[i].key == key)
                })
        } else {
            None
        };
        let index = match existing {
            Some(i) => i,
            None => {
                let (compressed, jpeg, predictor) = compress_samples(&key)?;
                let id = Ref::new(next + image_resources.len() as i32);
                let digest = key.sample_sha256;
                let i = image_resources.len();
                image_resources.push(EncodedImageResource {
                    id,
                    key,
                    compressed,
                    jpeg,
                    predictor,
                });
                if image_options.reuse_identical {
                    resource_lookup.entry(digest).or_default().push(i);
                }
                i
            }
        };
        image_ids.push(image_resources[index].id);
    }

    pdf.catalog(catalog).pages(page_tree);
    pdf.pages(page_tree).kids([page]).count(1);

    // glyph font (all streams before the CID-font writer)
    let map_bytes = cid_to_gid_bytes(encodings);
    let tu = to_unicode_stream(encodings);
    compressed_stream(&mut pdf, glyph_map, &map_bytes, false)?;
    compressed_stream(&mut pdf, glyph_tu, tu.as_bytes(), false)?;
    compressed_stream(&mut pdf, glyph_ff, &font_bytes, true)?;
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
        compressed_stream(&mut pdf, glyphless_map, &gl_map, false)?;
        compressed_stream(&mut pdf, glyphless_tu, gl_tu.as_bytes(), false)?;
        compressed_stream(&mut pdf, glyphless_ff, &glyphless_bytes, true)?;
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
            gl_cid
                .subtype(CidFontType::Type2)
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

    // patch images; image_ids is placement-local and may repeat a resource.
    for resource in &image_resources {
        let mut img = pdf.stream(resource.id, &resource.compressed);
        img.pair(Name(b"Type"), Name(b"XObject"));
        img.pair(Name(b"Subtype"), Name(b"Image"));
        img.pair(Name(b"Width"), resource.key.width as i32);
        img.pair(Name(b"Height"), resource.key.height as i32);
        let color_space: &[u8] = if resource.key.color_space == 1 {
            b"DeviceGray"
        } else {
            b"DeviceRGB"
        };
        img.pair(Name(b"ColorSpace"), Name(color_space));
        img.pair(
            Name(b"BitsPerComponent"),
            resource.key.bits_per_component as i32,
        );
        img.pair(
            Name(b"Filter"),
            Name(if resource.jpeg {
                b"DCTDecode"
            } else {
                b"FlateDecode"
            }),
        );
        if !resource.jpeg && resource.predictor != 1 {
            let predictor = match resource.predictor {
                2 => pdf_writer::types::Predictor::Tiff,
                12 => pdf_writer::types::Predictor::PngUp,
                _ => unreachable!("validated by encoder"),
            };
            img.decode_parms()
                .predictor(predictor)
                .colors(resource.key.color_space as i32)
                .bits_per_component(resource.key.bits_per_component as i32)
                .columns(resource.key.width as i32);
        }
        img.finish();
    }

    // content
    let mut c = Content::new();
    emit_patches(&mut c, patches, to_pt, page_w_pt, page_h_pt, paper);
    emit_text_runs(
        &mut c,
        shapes,
        encodings,
        occurrences,
        span_texts,
        owners,
        owner_cids,
        lines,
        to_pt,
        ink,
        false,
    );

    c.end_text();
    let content_bytes = c.finish();
    compressed_stream(&mut pdf, content, &content_bytes, false)?;

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

    let info_id = Ref::new(next + image_resources.len() as i32);
    let mut doc = pdf.document_info(info_id);
    doc.producer(TextStr("scanweave-m1a"));
    doc.finish();

    crate::serialization::compact(pdf.finish())
}

/// The authoritative raster→page-points mapping (SPEC §4.1): the normalized
/// OCR page's affine, restricted to the axis-aligned case applied once at
/// normalization. A 600 dpi scan carries a = 72/600 here, so its physical
/// dimensions come from the page's own geometry — never from a CLI default.
#[derive(Debug, Clone, Copy)]
pub struct PageTransform {
    /// raster px → pt scale in x (a)
    pub a: f64,
    /// raster px → pt scale in y (d; negative = y-flip)
    pub d: f64,
    /// pt offset in x (e)
    pub e: f64,
    /// pt offset in y (f)
    pub f: f64,
}

impl PageTransform {
    pub fn x(&self, px: f64) -> f32 {
        (self.a * px + self.e) as f32
    }
    pub fn y(&self, py: f64) -> f32 {
        (self.d * py + self.f) as f32
    }
    /// pt per raster pixel in x
    pub fn sx(&self) -> f64 {
        self.a
    }
    /// pt per raster pixel in y (positive)
    pub fn sy(&self) -> f64 {
        -self.d
    }
    /// page extent in pt (the MediaBox), from the affine + raster size
    pub fn page_w(&self, px: f64) -> f32 {
        (self.a * px + self.e).max(0.0) as f32
    }
    pub fn page_h(&self, py: f64) -> f32 {
        // d is negative (y-flip): the top edge sits at -d*py + f and the bottom
        // at f, so the height is the scale times the raster height
        ((-self.d) * py).max(0.0) as f32
    }
}

/// A drawn glyph occurrence: (shape index, 0-based CID, ink bbox in source px,
/// span id, symbol id, semantic text).
pub type Occurrence = (usize, u32, [f64; 4], String, String, String);

fn validate_occurrence_geometry(occurrences: &[Occurrence]) -> Result<(), String> {
    for (_, _, b, _, symbol, _) in occurrences {
        if !b.iter().all(|v| v.is_finite()) || b[2] <= b[0] || b[3] <= b[1] {
            return Err(format!(
                "invalid glyph occurrence geometry for {symbol}: {b:?}"
            ));
        }
    }
    Ok(())
}

/// One page's assembly inputs. `occurrences`/`owner_cids` use the CID space of
/// the encodings slice inside the same struct (single-page use). For documents,
/// the document builder remaps them onto the shared encoding space.
#[derive(Debug, Clone)]
pub struct PageParts {
    /// the canonical source raster (needed by the whole-page raster baseline)
    pub source_rgb: Vec<u8>,
    /// raster-baseline candidate: the text layer is drawn INVISIBLY over the
    /// whole-page source patch (searchable text, source pixels, no vector ink)
    pub raster_baseline: bool,
    /// Verified simple input image, available only for a zero-vector page.
    pub encoded_source: Option<crate::source_image::EncodedSourceImage>,
    pub source_w: usize,
    pub source_h: usize,
    pub shapes: Vec<GlyphShape>,
    /// (index into `shapes`, semantic string) — one entry per CID (1-based)
    pub encodings: Vec<(usize, String)>,
    pub occurrences: Vec<(usize, u32, [f64; 4], String, String, String)>,
    pub span_texts: Vec<(String, String)>,
    pub page_w_pt: f32,
    pub page_h_pt: f32,
    pub dpi: f64,
    /// the authoritative raster→pt affine (page geometry source of truth)
    pub to_pt: PageTransform,
    pub paper: [u8; 3],
    pub ink: [u8; 3],
    pub patches: Vec<Patch>,
    pub owners: Vec<Owner>,
    pub owner_cids: Vec<u32>,
    pub lines: Vec<LineSpec>,
}

/// Assemble a multi-page document over ONE shared font resource.
///
/// `encodings` is the document-wide encoding table: `(index into `shapes`,
/// semantic string)` in first-appearance order (page order, then slot order),
/// so identical (shape, label) pairs across pages share one CID — the
/// document-level font reuse. Every page's occurrences/owner CIDs must already
/// be expressed in this table's 1-based CID space. Object numbers are assigned
/// deterministically (catalog, pages, shared font, then page/content pairs,
/// then per-page images in page order), so output bytes are a pure function of
/// the inputs.
#[allow(clippy::too_many_arguments)]
pub fn assemble_document(
    pages: &[PageParts],
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    font_bytes: &[u8],
) -> Result<(Vec<u8>, AssemblyStats), String> {
    assemble_document_with_options(
        pages,
        shapes,
        encodings,
        font_bytes,
        ImageEncodingOptions::default(),
    )
}

pub fn assemble_document_with_options(
    pages: &[PageParts],
    shapes: &[GlyphShape],
    encodings: &[(usize, String)],
    font_bytes: &[u8],
    image_options: ImageEncodingOptions,
) -> Result<(Vec<u8>, AssemblyStats), String> {
    for page in pages {
        validate_occurrence_geometry(&page.occurrences)?;
    }
    let assembly_started = std::time::Instant::now();
    let image_started = std::time::Instant::now();
    if pages.is_empty() {
        return Err("document has no pages".into());
    }
    if encodings.len() + 1 > u16::MAX as usize {
        return Err(format!(
            "document CID table exceeds the 16-bit Identity-H space ({} CIDs)",
            encodings.len()
        ));
    }
    let mut stats = AssemblyStats::default();
    let mut pdf = Pdf::new();
    pdf.set_version(1, 7);

    let catalog = Ref::new(1);
    let page_tree = Ref::new(2);
    let font = Ref::new(3);
    let desc = Ref::new(4);
    let cidfont = Ref::new(5);
    let fontfile = Ref::new(6);
    let cid_map = Ref::new(7);
    let to_uni = Ref::new(8);

    // per-page: page object then content object
    let page_refs: Vec<Ref> = (0..pages.len())
        .map(|i| Ref::new(9 + (i * 2) as i32))
        .collect();
    let content_refs: Vec<Ref> = (0..pages.len())
        .map(|i| Ref::new(10 + (i * 2) as i32))
        .collect();
    let mut next_image = 9 + (pages.len() * 2) as i32;
    let mut image_refs: Vec<Vec<Ref>> = Vec::with_capacity(pages.len());
    let mut image_resources: Vec<EncodedImageResource> = Vec::new();
    let mut resource_lookup: HashMap<[u8; 32], Vec<usize>> = HashMap::new();
    for p in pages {
        let mut ids = Vec::with_capacity(p.patches.len());
        for patch in &p.patches {
            let key = canonical_patch(patch, image_options)?;
            let existing = if image_options.reuse_identical {
                resource_lookup
                    .get(&key.sample_sha256)
                    .and_then(|candidates| {
                        candidates
                            .iter()
                            .copied()
                            .find(|&i| image_resources[i].key == key)
                    })
            } else {
                None
            };
            let resource_index = match existing {
                Some(i) => i,
                None => {
                    let (mut compressed, mut jpeg, mut predictor) = compress_samples(&key)?;
                    let mut key = key;
                    if p.occurrences.is_empty() && p.patches.len() == 1 {
                        if let Some(source) = &p.encoded_source {
                            if source.jpeg || source.bytes.len() < compressed.len() {
                                compressed = source.bytes.clone();
                                jpeg = source.jpeg;
                                predictor = source.predictor;
                                key.width = source.width;
                                key.height = source.height;
                                key.color_space = source.colors;
                                // Encoded source identity is distinct from normalized RGB.
                                let mut digest = Sha256::new();
                                digest.update(&source.bytes);
                                digest.update(source.width.to_be_bytes());
                                digest.update(source.height.to_be_bytes());
                                digest.update([source.colors, source.jpeg as u8, source.predictor]);
                                key.sample_sha256 = digest.finalize().into();
                                // Retain bytes for a collision-checked equality test.
                                key.samples = source.bytes.clone();
                            }
                        }
                    }
                    if image_options.reuse_identical {
                        if let Some(existing) =
                            resource_lookup.get(&key.sample_sha256).and_then(|items| {
                                items
                                    .iter()
                                    .copied()
                                    .find(|&i| image_resources[i].key == key)
                            })
                        {
                            ids.push(image_resources[existing].id);
                            continue;
                        }
                    }
                    let id = Ref::new(next_image);
                    next_image += 1;
                    let i = image_resources.len();
                    let digest = key.sample_sha256;
                    image_resources.push(EncodedImageResource {
                        id,
                        key,
                        compressed,
                        jpeg,
                        predictor,
                    });
                    if image_options.reuse_identical {
                        resource_lookup.entry(digest).or_default().push(i);
                    }
                    i
                }
            };
            ids.push(image_resources[resource_index].id);
        }
        image_refs.push(ids);
    }
    stats.image_encoding_ms = image_started.elapsed().as_millis();

    pdf.catalog(catalog).pages(page_tree);
    let kids: Vec<Ref> = page_refs.clone();
    pdf.pages(page_tree).kids(kids).count(pages.len() as i32);

    // shared font program
    let map_bytes = cid_to_gid_bytes(encodings);
    let tu = to_unicode_stream(encodings);
    compressed_stream(&mut pdf, cid_map, &map_bytes, false)?;
    compressed_stream(&mut pdf, to_uni, tu.as_bytes(), false)?;
    stats.font_bytes = compressed_stream(&mut pdf, fontfile, font_bytes, true)?;
    pdf.font_descriptor(desc)
        .name(Name(b"ScanWeaveDoc"))
        .flags(pdf_writer::types::FontFlags::SYMBOLIC)
        .bbox(Rect::new(0.0, -50.0, 4096.0, 4096.0))
        .italic_angle(0.0)
        .ascent(3800.0)
        .descent(-500.0)
        .cap_height(3600.0)
        .stem_v(80.0)
        .font_file2(fontfile);
    {
        let mut cid = pdf.cid_font(cidfont);
        cid.subtype(CidFontType::Type2)
            .base_font(Name(b"ScanWeaveDoc"))
            .system_info(SystemInfo {
                registry: Str(b"Adobe"),
                ordering: Str(b"Identity"),
                supplement: 0,
            })
            .font_descriptor(desc)
            .default_width(1000.0)
            .cid_to_gid_map_stream(cid_map);
        {
            let mut widths = cid.widths();
            for (cid_index, (elem, _)) in encodings.iter().enumerate() {
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
    let mut t0 = pdf.type0_font(font);
    t0.base_font(Name(b"ScanWeaveDoc"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(cidfont)
        .to_unicode(to_uni);
    t0.finish();

    // Image streams are document-global; page-local content names refer to a
    // shared XObject only when its complete decoded samples and parameters match.
    stats.image_xobjects = image_resources.len();
    stats.image_references = image_refs.iter().map(Vec::len).sum();
    for resource in &image_resources {
        stats.raster_encoded_bytes += resource.compressed.len();
        let mut img = pdf.stream(resource.id, &resource.compressed);
        img.pair(Name(b"Type"), Name(b"XObject"));
        img.pair(Name(b"Subtype"), Name(b"Image"));
        img.pair(Name(b"Width"), resource.key.width as i32);
        img.pair(Name(b"Height"), resource.key.height as i32);
        let color_space: &[u8] = if resource.key.color_space == 1 {
            b"DeviceGray"
        } else {
            b"DeviceRGB"
        };
        img.pair(Name(b"ColorSpace"), Name(color_space));
        img.pair(
            Name(b"BitsPerComponent"),
            resource.key.bits_per_component as i32,
        );
        img.pair(
            Name(b"Filter"),
            Name(if resource.jpeg {
                b"DCTDecode"
            } else {
                b"FlateDecode"
            }),
        );
        if !resource.jpeg && resource.predictor != 1 {
            let predictor = match resource.predictor {
                2 => pdf_writer::types::Predictor::Tiff,
                12 => pdf_writer::types::Predictor::PngUp,
                _ => unreachable!("validated by encoder"),
            };
            img.decode_parms()
                .predictor(predictor)
                .colors(resource.key.color_space as i32)
                .bits_per_component(resource.key.bits_per_component as i32)
                .columns(resource.key.width as i32);
        }
        img.finish();
    }

    // pages
    for (i, p) in pages.iter().enumerate() {
        // content
        let mut c = Content::new();
        emit_patches(
            &mut c,
            &p.patches,
            &p.to_pt,
            p.page_w_pt,
            p.page_h_pt,
            p.paper,
        );
        emit_text_runs(
            &mut c,
            shapes,
            encodings,
            &p.occurrences,
            &p.span_texts,
            &p.owners,
            &p.owner_cids,
            &p.lines,
            &p.to_pt,
            p.ink,
            p.raster_baseline,
        );
        c.end_text();
        let content_bytes = c.finish();
        stats.content_bytes += compressed_stream(&mut pdf, content_refs[i], &content_bytes, false)?;

        let mut page = pdf.page(page_refs[i]);
        page.parent(page_tree)
            .media_box(Rect::new(0.0, 0.0, p.page_w_pt, p.page_h_pt))
            .contents(content_refs[i]);
        let mut res = page.resources();
        res.fonts().pair(Name(b"F1"), font);
        {
            let mut xo = res.x_objects();
            for (j, r) in image_refs[i].iter().enumerate() {
                let name = format!("Im{j}");
                xo.pair(Name(name.as_bytes()), *r);
            }
            xo.finish();
        }
        res.finish();
        page.finish();
    }

    let result = crate::serialization::compact(pdf.finish())?;
    stats.assembly_ms = assembly_started.elapsed().as_millis();
    Ok((result, stats))
}

/// What the assembled document actually contains (honest byte accounting:
/// object counts and the encoded sizes that end up in the file).
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct AssemblyStats {
    /// Unique image resources serialized in the document.
    pub image_xobjects: usize,
    /// Page-local image placements that reference those resources.
    pub image_references: usize,
    pub raster_encoded_bytes: usize,
    pub content_bytes: usize,
    pub font_bytes: usize,
    pub image_encoding_ms: u128,
    pub assembly_ms: u128,
}

#[cfg(test)]
mod image_resource_tests {
    use super::*;

    fn page(patches: Vec<Patch>) -> PageParts {
        PageParts {
            source_rgb: vec![255; 3],
            raster_baseline: false,
            encoded_source: None,
            source_w: 1,
            source_h: 1,
            shapes: vec![],
            encodings: vec![],
            occurrences: vec![],
            span_texts: vec![],
            page_w_pt: 72.0,
            page_h_pt: 72.0,
            dpi: 72.0,
            to_pt: PageTransform {
                a: 1.0,
                d: -1.0,
                e: 0.0,
                f: 72.0,
            },
            paper: [255; 3],
            ink: [0; 3],
            patches,
            owners: vec![],
            owner_cids: vec![],
            lines: vec![],
        }
    }

    fn patch(bbox_px: [f64; 4], rgb: [u8; 3]) -> Patch {
        Patch {
            compact_background: false,
            bbox_px,
            rgb: rgb.to_vec(),
            w: 1,
            h: 1,
        }
    }

    #[test]
    fn exact_resources_are_shared_and_equal_channels_use_gray() {
        let pages = [
            page(vec![
                patch([0.0, 0.0, 1.0, 1.0], [220; 3]),
                patch([1.0, 0.0, 2.0, 1.0], [220; 3]),
            ]),
            page(vec![
                patch([0.0, 0.0, 1.0, 1.0], [220; 3]),
                patch([1.0, 0.0, 2.0, 1.0], [220, 219, 220]),
            ]),
        ];
        let (pdf, stats) =
            assemble_document_with_options(&pages, &[], &[], &[], ImageEncodingOptions::default())
                .unwrap();
        assert_eq!(stats.image_references, 4);
        assert_eq!(
            stats.image_xobjects, 2,
            "identical Gray pixels share one resource; different RGB stays separate"
        );
        assert!(String::from_utf8_lossy(&pdf).contains("/DeviceGray"));
        assert!(String::from_utf8_lossy(&pdf).contains("/DeviceRGB"));
        let (pdf2, _) =
            assemble_document_with_options(&pages, &[], &[], &[], ImageEncodingOptions::default())
                .unwrap();
        assert_eq!(
            pdf, pdf2,
            "object assignment and output must be deterministic"
        );
    }

    #[test]
    fn auto_predictor_selects_actual_smallest_lossless_stream() {
        let patch = Patch {
            bbox_px: [0., 0., 128., 128.],
            w: 128,
            h: 128,
            compact_background: false,
            rgb: (0..128 * 128)
                .flat_map(|i| {
                    let g = ((i % 128) * 2) as u8;
                    [g, g, g]
                })
                .collect(),
        };
        let mut key = canonical_patch(
            &patch,
            ImageEncodingOptions {
                predictor: 0,
                ..Default::default()
            },
        )
        .unwrap();
        let best = compress_samples(&key).unwrap();
        assert!(!best.1);
        let minimum = [1, 2, 12]
            .iter()
            .map(|&p| {
                key.predictor = p;
                compress_samples(&key).unwrap().0.len()
            })
            .min()
            .unwrap();
        assert_eq!(best.0.len(), minimum);
        // Faint samples, including a 1-level mark, are never sent to a native
        // lossy codec. Decoding the chosen lossless predictor is exact.
        key.predictor = best.2;
        let mut reader = flate2::read::ZlibDecoder::new(best.0.as_slice());
        let mut decoded = Vec::new();
        std::io::Read::read_to_end(&mut reader, &mut decoded).unwrap();
        assert_eq!(decoded, encode_predictor_value(&key, best.2).unwrap());
    }

    #[test]
    fn image_dimensions_and_sample_length_are_validated() {
        let pages = [page(vec![Patch {
            compact_background: false,
            bbox_px: [0.0; 4],
            rgb: vec![1, 2, 3],
            w: 2,
            h: 1,
        }])];
        assert!(assemble_document_with_options(
            &pages,
            &[],
            &[],
            &[],
            ImageEncodingOptions::default()
        )
        .is_err());
    }

    #[test]
    fn flate_predictor_control_pdfs_are_serialized_when_requested() {
        let patches = vec![
            Patch {
                compact_background: false,
                bbox_px: [0.0, 0.0, 2.0, 2.0],
                w: 2,
                h: 2,
                rgb: vec![248, 248, 248, 250, 250, 250, 252, 252, 252, 255, 255, 255],
            },
            Patch {
                compact_background: false,
                bbox_px: [2.0, 0.0, 4.0, 2.0],
                w: 2,
                h: 2,
                rgb: vec![255, 0, 0, 0, 255, 0, 0, 0, 255, 30, 60, 90],
            },
            Patch {
                compact_background: false,
                bbox_px: [4.0, 0.0, 6.0, 2.0],
                w: 2,
                h: 2,
                rgb: vec![0, 0, 255, 255, 255, 0, 120, 20, 200, 10, 80, 30],
            },
        ];
        let pages = [page(patches)];
        let output_dir = std::env::var_os("M1F_CONTROL_DIR").map(std::path::PathBuf::from);
        if let Some(dir) = &output_dir {
            std::fs::create_dir_all(dir).unwrap();
        }
        for (name, predictor) in [("none", 1), ("tiff", 2), ("png_up", 12)] {
            let options = ImageEncodingOptions {
                predictor,
                ..ImageEncodingOptions::default()
            };
            let (pdf, stats) =
                assemble_document_with_options(&pages, &[], &[], &[], options).unwrap();
            assert_eq!(stats.image_xobjects, 3);
            assert!(String::from_utf8_lossy(&pdf).contains("/DeviceRGB"));
            assert!(String::from_utf8_lossy(&pdf).contains("/DeviceGray"));
            if let Some(dir) = &output_dir {
                std::fs::write(dir.join(format!("predictor-{name}.pdf")), pdf).unwrap();
            }
        }
    }
}

#[cfg(test)]
mod owner_frame_tests {
    use super::*;
    #[test]
    fn noncontiguous_occurrences_of_a_span_are_all_emitted_once() {
        let make = |span: &str| {
            (
                0,
                0,
                [0., 0., 1., 1.],
                span.to_string(),
                String::new(),
                String::new(),
            )
        };
        assert_eq!(
            occurrence_groups(&[make("a"), make("b"), make("a")]),
            vec![vec![0, 2], vec![1]]
        );
        assert_eq!(
            occurrence_groups(&[make("a"), make("a"), make("b")]),
            vec![vec![0, 1], vec![2]]
        );
    }
    #[test]
    fn owner_only_cid_advance_matches_the_serialized_half_em_width() {
        assert_eq!(cid_advance(&[], &[(0, "x".into())], 1), 0.5);
        let mut content = Content::new();
        content.begin_text();
        emit_owner_characters(
            &mut content,
            &[OwnerCharacter {
                cid: 1,
                bbox_px: [10.0, 20.0, 30.0, 40.0],
                order: 0,
            }],
            &[],
            &[(0, "x".into())],
            &PageTransform {
                a: 1.0,
                d: -1.0,
                e: 0.0,
                f: 100.0,
            },
        );
        let stream = String::from_utf8(content.finish()).unwrap();
        assert!(
            stream.contains("40 0 0 "),
            "half-em owner must advance the full 20pt span: {stream}"
        );
        assert!(
            stream.contains("3 Tr"),
            "semantic glyph must stay invisible: {stream}"
        );
    }

    #[test]
    fn a_reversed_replacement_box_cannot_be_serialized_as_a_mirrored_glyph() {
        let o = (
            0,
            0,
            [129.0, 936.0, 124.0, 940.0],
            "word".into(),
            "real-e".into(),
            "e".into(),
        );
        assert!(validate_occurrence_geometry(&[o])
            .unwrap_err()
            .contains("real-e"));
    }
}
