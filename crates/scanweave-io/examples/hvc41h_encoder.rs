//! Research-only access to the unchanged #39 residual JPEG encoder.
#[path = "../src/tonal_image.rs"]
mod tonal_image;
use std::{env, fs};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    if env::var("SCANWEAVE_HVC41H_ENCODER").as_deref() != Ok("1") {
        return Err("HVC-41H research switch required".into());
    }
    let args: Vec<String> = env::args().collect();
    if args.len() != 5 { return Err("usage: encoder residual|native input.png output.jpg resized.png".into()); }
    let rgb = image::open(&args[2])?.to_rgb8();
    let (w, h) = rgb.dimensions();
    let page_w = 416.88_f32;
    let page_h = 564.96_f32;
    let (bytes, rw, rh) = if args[1] == "residual" {
        let c = tonal_image::encode_residual(rgb.as_raw(), w, h, 3, page_w, page_h)?
            .ok_or("input was ineligible for the existing compact encoder")?;
        (c.bytes, c.width, c.height)
    } else if args[1] == "native" {
        if (w, h) != (1158, 1569) { return Err("unexpected native dimensions".into()); }
        let mut bytes = Vec::new();
        let mut encoder = jpeg_encoder::Encoder::new(&mut bytes, 85);
        encoder.set_sampling_factor(jpeg_encoder::SamplingFactor::R_4_2_0);
        encoder.set_optimized_huffman_tables(true);
        encoder.set_progressive(true);
        encoder.encode(rgb.as_raw(), w as u16, h as u16, jpeg_encoder::ColorType::Rgb)?;
        (bytes, w, h)
    } else { return Err("unknown mode".into()); };
    let resized = image::imageops::resize(&rgb, rw, rh, image::imageops::FilterType::Lanczos3);
    resized.save(&args[4])?;
    fs::write(&args[3], &bytes)?;
    println!("width={rw} height={rh} bytes={}", bytes.len());
    Ok(())
}
