//! Frozen 4x PDFium raw-source/default/candidate owned-ink preflight.
use super::{owned_ink, quantile, source::Observation};
use crate::{glyphs::GlyphShape, page_pdf::PageParts};
use pdf_writer::types::{CidFontType, SystemInfo};
use pdf_writer::{Content, Finish, Name, Pdf, Rect, Ref, Str};
use pdfium_render::prelude::*;
use std::collections::{BTreeMap, BTreeSet};

pub enum Draw {
    Glyph {
        gid: u16,
        matrix: [f64; 6],
    },
    Image {
        pixels: Vec<u8>,
        width: usize,
        height: usize,
        matrix: [f64; 6],
    },
}
pub struct IsolatedPage {
    pub size: [f32; 2],
    pub draw: Draw,
}
fn stream(pdf: &mut Pdf, id: Ref, data: &[u8], font: bool) -> Result<(), String> {
    let decoded_len = data.len();
    let data = crate::serialization::deflate(data)?;
    let mut s = pdf.stream(id, &data);
    s.filter(pdf_writer::Filter::FlateDecode);
    if font {
        s.pair(Name(b"Length1"), decoded_len as i32);
    }
    s.finish();
    Ok(())
}
pub fn isolated(font: &[u8], pages: &[IsolatedPage]) -> Result<Vec<u8>, String> {
    let mut pdf = Pdf::new();
    pdf.catalog(Ref::new(1)).pages(Ref::new(2));
    let ids: Vec<Ref> = (0..pages.len())
        .map(|i| Ref::new(7 + i as i32 * 3))
        .collect();
    pdf.pages(Ref::new(2))
        .kids(ids.iter().copied())
        .count(pages.len() as i32);
    pdf.type0_font(Ref::new(3))
        .base_font(Name(b"Font04Preflight"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(Ref::new(4));
    pdf.cid_font(Ref::new(4))
        .subtype(CidFontType::Type2)
        .base_font(Name(b"Font04Preflight"))
        .system_info(SystemInfo {
            registry: Str(b"Adobe"),
            ordering: Str(b"Identity"),
            supplement: 0,
        })
        .font_descriptor(Ref::new(5))
        .cid_to_gid_map_predefined(Name(b"Identity"));
    pdf.font_descriptor(Ref::new(5))
        .name(Name(b"Font04Preflight"))
        .flags(pdf_writer::types::FontFlags::SYMBOLIC)
        .bbox(Rect::new(0., -50., 4096., 4096.))
        .italic_angle(0.)
        .ascent(3800.)
        .descent(-500.)
        .cap_height(3600.)
        .stem_v(80.)
        .font_file2(Ref::new(6));
    stream(&mut pdf, Ref::new(6), font, true)?;
    for (i, p) in pages.iter().enumerate() {
        let id = ids[i];
        let content = Ref::new(id.get() + 1);
        let image = Ref::new(id.get() + 2);
        let mut c = Content::new();
        match &p.draw {
            Draw::Glyph { gid, matrix } => {
                c.begin_text();
                c.set_font(Name(b"F"), 1.);
                c.set_text_matrix(matrix.map(|v| v as f32));
                c.show(Str(&gid.to_be_bytes()));
                c.end_text();
            }
            Draw::Image {
                pixels,
                width,
                height,
                matrix,
            } => {
                let encoded = crate::serialization::deflate(pixels)?;
                let mut s = pdf.image_xobject(image, &encoded);
                s.width(*width as i32)
                    .height(*height as i32)
                    .color_space()
                    .device_gray();
                s.bits_per_component(8)
                    .filter(pdf_writer::Filter::FlateDecode);
                s.finish();
                c.save_state();
                c.transform(matrix.map(|v| v as f32));
                c.x_object(Name(b"I"));
                c.restore_state();
            }
        }
        stream(&mut pdf, content, &c.finish(), false)?;
        let mut page = pdf.page(id);
        page.parent(Ref::new(2))
            .media_box(Rect::new(0., 0., p.size[0], p.size[1]))
            .contents(content);
        let mut res = page.resources();
        res.fonts().pair(Name(b"F"), Ref::new(3));
        if matches!(p.draw, Draw::Image { .. }) {
            res.x_objects().pair(Name(b"I"), image);
        }
        res.finish();
        page.finish();
    }
    Ok(pdf.finish())
}

/// Reproduce the default assembler's f32 matrix before PDF number serialization.
pub fn default_matrix(page: &PageParts, shape: &GlyphShape, b: [f64; 4]) -> [f64; 6] {
    let xf = &page.to_pt;
    let width = ((b[2] - b[0]) * xf.sx()) as f32;
    let height = ((b[3] - b[1]) * xf.sy()) as f32;
    let sx = width * 2048. / shape.ink_span_fu[0].max(1.) as f32;
    let sy = height * 2048. / shape.ink_span_fu[1].max(1.) as f32;
    let tx = xf.x(b[0]) - shape.anchor_bbox_fu[0] as f32 * sx / 2048.;
    let ty = xf.y(b[3]) - shape.anchor_bbox_fu[1] as f32 * sy / 2048.;
    [sx, 0., 0., sy, tx, ty].map(|v| v.to_string().parse().unwrap())
}
pub fn candidate_matrix(page: &PageParts, shape: &GlyphShape, b: [f64; 4]) -> [f64; 6] {
    let xf = &page.to_pt;
    let sx = (b[2] - b[0]) / shape.ink_span_fu[0];
    let sy = (b[3] - b[1]) / shape.ink_span_fu[1];
    [
        sx * 2048. * xf.sx(),
        0.,
        0.,
        sy * 2048. * xf.sy(),
        (b[0] - shape.anchor_bbox_fu[0] * sx) * xf.sx(),
        page.page_h_pt as f64 - (b[3] + shape.anchor_bbox_fu[1] * sy) * xf.sy(),
    ]
}

struct Document<'a> {
    bindings: &'a dyn PdfiumLibraryBindings,
    handle: *mut std::ffi::c_void,
}
impl Drop for Document<'_> {
    fn drop(&mut self) {
        if !self.handle.is_null() {
            self.bindings.FPDF_CloseDocument(self.handle.cast());
        }
    }
}
fn crop(
    bindings: &dyn PdfiumLibraryBindings,
    document: *mut std::ffi::c_void,
    index: usize,
    size: [f32; 2],
    bounds: [i32; 4],
) -> Result<Vec<f64>, String> {
    let page = bindings.FPDF_LoadPage(document.cast(), index as i32);
    if page.is_null() {
        return Err("PDFium preflight page load failed".into());
    }
    let w = (bounds[2] - bounds[0]) * 4;
    let h = (bounds[3] - bounds[1]) * 4;
    if w <= 0 || h <= 0 || w as i64 * h as i64 > 16_777_216 {
        bindings.FPDF_ClosePage(page);
        return Err("owned crop exceeds bounds".into());
    }
    let bitmap = bindings.FPDFBitmap_CreateEx(w, h, 1, std::ptr::null_mut(), 0);
    if bitmap.is_null() {
        bindings.FPDF_ClosePage(page);
        return Err("PDFium preflight bitmap allocation failed".into());
    }
    bindings.FPDFBitmap_FillRect(bitmap, 0, 0, w, h, 0xffffffff);
    let scale = 1200. / 72.;
    let fw = (size[0] as f64 * scale).ceil() as i32;
    let fh = (size[1] as f64 * scale).ceil() as i32;
    bindings.FPDF_RenderPageBitmap(bitmap, page, -bounds[0] * 4, -bounds[1] * 4, fw, fh, 0, 8);
    let stride = bindings.FPDFBitmap_GetStride(bitmap) as usize;
    let bytes = bindings.FPDFBitmap_GetBuffer_as_vec(bitmap);
    bindings.FPDFBitmap_Destroy(bitmap);
    bindings.FPDF_ClosePage(page);
    let mut result = vec![0.; (w / 4 * h / 4) as usize];
    for y in 0..h as usize / 4 {
        for x in 0..w as usize / 4 {
            let mut sum = 0.;
            for yy in 0..4 {
                for xx in 0..4 {
                    sum += bytes[(y * 4 + yy) * stride + x * 4 + xx] as f64;
                }
            }
            result[y * (w as usize / 4) + x] = 1. - sum / (16. * 255.);
        }
    }
    Ok(result)
}

pub fn preflight(
    rows: &[Observation],
    pages: &[PageParts],
    shapes: &[GlyphShape],
    default_font: &[u8],
    assignments: &[(usize, usize, [f64; 4])],
) -> Result<BTreeSet<usize>, String> {
    let library = std::env::var_os("SCANWEAVE_PDFIUM_LIBRARY");
    let bindings = if let Some(path) = library {
        Pdfium::bind_to_library(path)
    } else {
        Pdfium::bind_to_system_library()
    }
    .map_err(|e| format!("glyph sharing requires PDFium for its frozen owned-ink check: {e}"))?;
    let pdfium = Pdfium::new(bindings);
    let bindings = pdfium.bindings();
    let mut trace_shapes = Vec::new();
    let mut encodings = Vec::new();
    let mut gids = BTreeMap::new();
    for (i, r) in rows.iter().enumerate() {
        if let Some(c) = &r.canonical {
            gids.insert(i, trace_shapes.len() as u16 + 1);
            trace_shapes.push(c.shape.clone());
            encodings.push((trace_shapes.len() - 1, r.label.clone()));
        }
    }
    let canonical_font = crate::fontbuild::build_font_with_bounds(
        &trace_shapes,
        &encodings,
        2048,
        Some([-100, -100, 32760, 32760]),
    )?;
    let mut source = Vec::new();
    let mut current = Vec::new();
    let mut candidate = Vec::new();
    let mut bounds = Vec::new();
    for &(i, j, bbox) in assignments {
        let row = &rows[i];
        let page = &pages[row.page];
        let p = page;
        let source_unit = row.source.as_ref().ok_or("missing ownership source")?;
        let w = source_unit.crop_w + 4;
        let h = source_unit.crop_h + 4;
        let halo = source_unit
            .gray_halo
            .as_ref()
            .ok_or("missing ownership halo")?;
        let mut owned = vec![false; w * h];
        for y in 0..source_unit.crop_h {
            for x in 0..source_unit.crop_w {
                owned[(y + 2) * w + x + 2] = source_unit.mask[y * source_unit.crop_w + x];
            }
        }
        let off: Vec<f64> = halo
            .iter()
            .zip(&owned)
            .filter(|(_, m)| !**m)
            .map(|(&v, _)| v as f64)
            .collect();
        let on: Vec<f64> = halo
            .iter()
            .zip(&owned)
            .filter(|(_, m)| **m)
            .map(|(&v, _)| v as f64)
            .collect();
        let paper = quantile(&off, 0.8);
        let ink = quantile(&on, 0.15);
        let pixels: Vec<u8> = halo
            .iter()
            .map(|&v| {
                ((1. - ((paper - v as f64) / (paper - ink).max(1.)).clamp(0., 1.)) * 255.)
                    .round_ties_even() as u8
            })
            .collect();
        let s = source_unit.bbox_px;
        let x = s[0] - 2.;
        let y = s[1] - 2.;
        let xf = &p.to_pt;
        let size = [p.page_w_pt, p.page_h_pt];
        source.push(IsolatedPage {
            size,
            draw: Draw::Image {
                pixels,
                width: w,
                height: h,
                matrix: [
                    w as f64 * xf.sx(),
                    0.,
                    0.,
                    h as f64 * xf.sy(),
                    x * xf.sx(),
                    p.page_h_pt as f64 - (y + h as f64) * xf.sy(),
                ],
            },
        });
        let o = &p.occurrences[row.occurrence];
        current.push(IsolatedPage {
            size,
            draw: Draw::Glyph {
                gid: o.0 as u16 + 1,
                matrix: default_matrix(page, &shapes[o.0], o.2),
            },
        });
        let c = rows[j]
            .canonical
            .as_ref()
            .ok_or("missing canonical trace")?;
        candidate.push(IsolatedPage {
            size,
            draw: Draw::Glyph {
                gid: gids[&j],
                matrix: candidate_matrix(page, &c.shape, bbox),
            },
        });
        bounds.push([
            s[0] as i32 - 4,
            s[1] as i32 - 4,
            s[2] as i32 + 4,
            s[3] as i32 + 4,
        ]);
    }
    let source_pdf = isolated(default_font, &source)?;
    let current_pdf = isolated(default_font, &current)?;
    let candidate_pdf = isolated(&canonical_font, &candidate)?;
    let docs: Vec<Document<'_>> = [&source_pdf, &current_pdf, &candidate_pdf]
        .iter()
        .map(|bytes| Document {
            bindings,
            handle: bindings.FPDF_LoadMemDocument64(bytes, None).cast(),
        })
        .collect();
    if docs.iter().any(|d| d.handle.is_null()) {
        return Err("PDFium preflight document load failed".into());
    }
    let mut exceptions = BTreeSet::new();
    for (k, &(i, _, _)) in assignments.iter().enumerate() {
        let size = source[k].size;
        let values: Vec<Vec<f64>> = docs
            .iter()
            .map(|doc| crop(bindings, doc.handle, k, size, bounds[k]))
            .collect::<Result<_, _>>()?;
        if !owned_ink(
            &values[0],
            &values[1],
            &values[2],
            (bounds[k][2] - bounds[k][0]) as usize,
            (bounds[k][3] - bounds[k][1]) as usize,
        )
        .is_empty()
        {
            exceptions.insert(i);
        }
    }
    Ok(exceptions)
}
