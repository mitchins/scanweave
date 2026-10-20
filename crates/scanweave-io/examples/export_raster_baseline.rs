//! Qualification artifact export only: use the normal document converter and
//! save its already serialized searchable-raster candidate. No alternate
//! inference, OCR, composition, or public conversion profile.
use std::{error::Error, path::Path};
fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 2 {
        return Err("usage: export_raster_baseline document.json output.pdf".into());
    }
    let path = Path::new(&args[0]);
    let root = path.parent().ok_or("bundle has no parent")?;
    let bundle = scanweave_core::bundle::Bundle::parse_bytes(&std::fs::read(path)?)?;
    let limits = scanweave_core::Limits::m0_defaults();
    bundle.verify_pairing(root, &limits)?;
    let mut inputs = Vec::new();
    for page in &bundle.pages {
        let source = bundle.sources.iter().find(|s| s.source_id == page.source_id)
            .ok_or("unknown source")?;
        if page.source_page_index != 0 || !matches!(source.kind, scanweave_core::bundle::BundleSourceKind::Image) {
            return Err("export requires single-image bundle sources".into());
        }
        let image = image::open(root.join(&source.asset_path))?.to_rgb8();
        let ocr = scanweave_core::ocr_page::OcrPage::parse_bytes(&std::fs::read(root.join(&page.ocr_page_path))?)?;
        ocr.validate(&limits)?;
        ocr.verify_binding(image.as_raw())?;
        inputs.push(scanweave_io::convert::input_from_ocr_page(image.as_raw(), image.width(), image.height(), &page.page_id, &ocr));
    }
    let policy = scanweave_io::convert::Policy {
        profile: "clearscan".into(), glyph_dictionary: "visual".into(),
        ..Default::default()
    };
    let output = scanweave_io::document::convert_document(&bundle.document_id, &inputs, &policy)?;
    std::fs::write(&args[1], &output.raster_baseline_pdf_bytes)?;
    println!("{} bytes", output.raster_baseline_pdf_bytes.len());
    Ok(())
}
