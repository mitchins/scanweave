//! Narrow image-only PDF import. Unsupported graphics use normal rasterization.
//! No arbitrary dictionaries/resources are transplanted into the output.
use hayro::hayro_syntax::{
    object::{Dict, Name, Stream},
    Pdf,
};

#[derive(Debug, Clone)]
pub struct EncodedSourceImage {
    pub(crate) bytes: Vec<u8>,
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) colors: u8,
    pub(crate) jpeg: bool,
    pub(crate) predictor: u8,
    rgb_sha256: String,
    page_width: f64,
    page_height: f64,
}

pub fn simple_page_images(bytes: Vec<u8>) -> Vec<Option<EncodedSourceImage>> {
    let Ok(pdf) = Pdf::new(bytes) else {
        return Vec::new();
    };
    pdf.pages()
        .iter()
        .map(|page| {
            let media = page.media_box();
            let crop = page.crop_box();
            // Clipping, nonzero origins and rotation deliberately use Poppler.
            if media.x0 != 0.0
                || media.y0 != 0.0
                || [crop.x0, crop.y0, crop.x1, crop.y1] != [media.x0, media.y0, media.x1, media.y1]
                || !matches!(page.rotation(), hayro::hayro_syntax::page::Rotation::None)
                || page.raw().contains_key(b"UserUnit")
                || page.raw().contains_key(b"Annots")
                || page.raw().contains_key(b"Group")
            {
                return None;
            }
            let mut ops = page.operations();
            let q = ops.next()?;
            if &**q.operator != b"q" || q.operands().count() != 0 {
                return None;
            }
            let cm = ops.next()?;
            if &**cm.operator != b"cm" {
                return None;
            }
            let numbers: Option<Vec<f32>> = cm.operands().map(|o| o.clone().into_f32()).collect();
            let n = numbers?;
            let target = [media.width(), 0.0, 0.0, media.height(), 0.0, 0.0];
            if n.len() != 6
                || n.iter()
                    .zip(target)
                    .any(|(&a, b)| !a.is_finite() || (a as f64 - b).abs() > 0.0001)
            {
                return None;
            }
            let draw = ops.next()?;
            if &**draw.operator != b"Do" {
                return None;
            }
            let mut operands = draw.operands();
            let name = operands.next()?.clone().into_name()?;
            if operands.next().is_some() {
                return None;
            }
            let image = page.resources().get_x_object(&name)?;
            let end = ops.next()?;
            if &**end.operator != b"Q" || end.operands().count() != 0 || ops.next().is_some() {
                return None;
            }
            let mut image = extract(image)?;
            image.page_width = media.width();
            image.page_height = media.height();
            Some(image)
        })
        .collect()
}

fn extract(stream: Stream<'_>) -> Option<EncodedSourceImage> {
    let d = stream.dict();
    // Reject optional interpretation/compositing properties rather than copy
    // opaque references. Only the listed self-contained subset is supported.
    let allowed: &[&[u8]] = &[
        b"Type",
        b"Subtype",
        b"Length",
        b"Width",
        b"Height",
        b"ColorSpace",
        b"BitsPerComponent",
        b"Filter",
        b"DecodeParms",
    ];
    if d.keys().any(|k| !allowed.contains(&k.as_ref())) {
        return None;
    }
    if d.get::<Name<'_>>(b"Subtype")?.as_ref() != b"Image"
        || d.get::<i32>(b"BitsPerComponent")? != 8
    {
        return None;
    }
    let colors = match d.get::<Name<'_>>(b"ColorSpace")?.as_ref() {
        b"DeviceGray" => 1,
        b"DeviceRGB" => 3,
        _ => return None,
    };
    let filter = d.get::<Name<'_>>(b"Filter")?;
    let jpeg = match filter.as_ref() {
        b"DCTDecode" => true,
        b"FlateDecode" => false,
        _ => return None,
    };
    let width = u32::try_from(d.get::<i32>(b"Width")?).ok()?;
    let height = u32::try_from(d.get::<i32>(b"Height")?).ok()?;
    if width == 0 || height == 0 || width as u64 * height as u64 > 80_000_000 {
        return None;
    }
    let mut predictor = 1;
    if d.contains_key(b"DecodeParms") {
        if jpeg {
            return None;
        }
        let p = d.get::<Dict<'_>>(b"DecodeParms")?;
        if p.keys().any(|k| {
            ![
                &b"Predictor"[..],
                b"Colors",
                b"Columns",
                b"BitsPerComponent",
            ]
            .contains(&k.as_ref())
        }) {
            return None;
        }
        predictor = u8::try_from(p.get::<i32>(b"Predictor").unwrap_or(1)).ok()?;
        if ![1, 2, 12].contains(&predictor)
            || p.get::<i32>(b"Colors").unwrap_or(1) != colors as i32
            || p.get::<i32>(b"Columns").unwrap_or(1) != width as i32
            || p.get::<i32>(b"BitsPerComponent").unwrap_or(8) != 8
        {
            return None;
        }
    }
    let mut image = EncodedSourceImage {
        bytes: stream.raw_data().into_owned(),
        width,
        height,
        colors,
        jpeg,
        predictor,
        rgb_sha256: String::new(),
        page_width: 0.0,
        page_height: 0.0,
    };
    image.rgb_sha256 = scanweave_core::hash_hex(&image.decode_rgb().ok()?);
    Some(image)
}

impl EncodedSourceImage {
    pub fn provenance(&self) -> serde_json::Value {
        serde_json::json!({"decoder":"ScanWeave direct device-colour image import (image/flate2)",
            "filter":if self.jpeg {"DCTDecode"}else{"FlateDecode"},"width":self.width,"height":self.height,
            "encoded_sha256":scanweave_core::hash_hex(&self.bytes),"decoded_rgb_sha256":self.rgb_sha256})
    }
    pub fn dimensions(&self) -> (u32, u32) {
        (self.width, self.height)
    }
    /// Decode only the validated direct device-colour subset, retaining native
    /// samples and rejecting malformed or oversized buffers.
    pub fn decode_rgb(&self) -> Result<Vec<u8>, String> {
        if self.jpeg {
            let size = image::ImageReader::with_format(
                std::io::Cursor::new(&self.bytes),
                image::ImageFormat::Jpeg,
            )
            .into_dimensions()
            .map_err(|e| e.to_string())?;
            if size != (self.width, self.height) {
                return Err("source JPEG header dimensions disagree with image dictionary".into());
            }
            let image = image::load_from_memory_with_format(&self.bytes, image::ImageFormat::Jpeg)
                .map_err(|e| e.to_string())?;
            if image.width() != self.width || image.height() != self.height {
                return Err("source JPEG dimensions disagree with image dictionary".into());
            }
            return Ok(image.to_rgb8().into_raw());
        }
        use std::io::Read;
        let row = self.width as usize * self.colors as usize;
        let size = row * self.height as usize;
        let expected = size
            + if self.predictor == 12 {
                self.height as usize
            } else {
                0
            };
        let mut samples = Vec::new();
        flate2::read::ZlibDecoder::new(self.bytes.as_slice())
            .take(expected as u64 + 1)
            .read_to_end(&mut samples)
            .map_err(|e| e.to_string())?;
        if samples.len() != expected {
            return Err("source image decoded length mismatch".into());
        }
        if self.predictor == 12 {
            let mut raw = vec![0u8; size];
            for y in 0..self.height as usize {
                if samples[y * (row + 1)] != 2 {
                    return Err("source PNG predictor is not fixed Up".into());
                }
                for x in 0..row {
                    raw[y * row + x] = samples[y * (row + 1) + 1 + x].wrapping_add(if y > 0 {
                        raw[(y - 1) * row + x]
                    } else {
                        0
                    });
                }
            }
            samples = raw;
        } else if self.predictor == 2 {
            for line in samples.chunks_exact_mut(row) {
                for x in self.colors as usize..row {
                    line[x] = line[x].wrapping_add(line[x - self.colors as usize]);
                }
            }
        }
        if self.colors == 1 {
            Ok(samples.into_iter().flat_map(|g| [g, g, g]).collect())
        } else {
            Ok(samples)
        }
    }
    pub(crate) fn matches(&self, input: &crate::convert::Input) -> bool {
        let t = input.raster_to_page_pt;
        self.width == input.width
            && self.height == input.height
            && scanweave_core::hash_hex(&input.rgb) == self.rgb_sha256
            && t[1] == 0.0
            && t[2] == 0.0
            && t[4] == 0.0
            && (t[0] * input.width as f64 - self.page_width).abs() < 0.001
            && (-t[3] * input.height as f64 - self.page_height).abs() < 0.001
            && (t[5] - self.page_height).abs() < 0.001
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pdf_writer::{Content, Finish, Name as N, Pdf as Writer, Rect, Ref};
    fn fixture(kind: &str) -> Vec<u8> {
        let mut p = Writer::new();
        p.catalog(Ref::new(1)).pages(Ref::new(2));
        p.pages(Ref::new(2)).kids([Ref::new(3)]).count(1);
        let mut page = p.page(Ref::new(3));
        page.parent(Ref::new(2))
            .media_box(Rect::new(0., 0., 72., 72.))
            .contents(Ref::new(4));
        if kind == "crop" {
            page.crop_box(Rect::new(1., 1., 71., 71.));
        }
        if kind == "rotate" {
            page.pair(N(b"Rotate"), 90);
        }
        page.resources().x_objects().pair(N(b"Im"), Ref::new(5));
        page.finish();
        let mut c = Content::new();
        c.save_state()
            .transform([72., 0., 0., 72., 0., 0.])
            .x_object(N(b"Im"))
            .restore_state();
        if kind == "extra" {
            c.rect(0., 0., 10., 10.).fill_nonzero();
        }
        p.stream(Ref::new(4), &c.finish());
        let raw = crate::serialization::deflate(&[120u8; 12]).unwrap();
        let mut im = p.image_xobject(Ref::new(5), &raw);
        im.width(2).height(2).bits_per_component(8);
        im.pair(N(b"ColorSpace"), N(b"DeviceRGB"));
        im.filter(pdf_writer::Filter::FlateDecode);
        if kind == "mask" {
            im.pair(N(b"SMask"), Ref::new(5));
        }
        if kind == "decode" {
            im.pair(N(b"Decode"), pdf_writer::Str(b"unsupported"));
        }
        im.finish();
        p.finish()
    }
    #[test]
    fn source_hint_is_bound_to_pixels_and_physical_geometry() {
        let source = simple_page_images(fixture("plain")).pop().unwrap().unwrap();
        let mut input = crate::convert::Input {
            rgb: source.decode_rgb().unwrap(),
            width: 2,
            height: 2,
            page_id: "p".into(),
            spans: vec![],
            protected_regions: vec![],
            raster_to_page_pt: [36., 0., 0., -36., 0., 72.],
            pixel_sha256: None,
        };
        assert!(source.matches(&input));
        input.rgb[0] = 121;
        assert!(!source.matches(&input));
        input.rgb[0] = 120;
        input.raster_to_page_pt[0] = 35.;
        assert!(!source.matches(&input));
    }
    #[test]
    fn accepts_only_simple_self_contained_full_page_images() {
        let found = simple_page_images(fixture("plain"));
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].as_ref().unwrap().width, 2);
        for kind in ["crop", "rotate", "extra", "mask", "decode"] {
            assert!(simple_page_images(fixture(kind))[0].is_none(), "{kind}");
        }
    }
}
