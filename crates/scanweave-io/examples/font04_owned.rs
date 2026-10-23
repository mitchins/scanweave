//! Export every production-owned source unit, without FONT-03's class filter.
use std::{error::Error,path::Path};
fn main()->Result<(),Box<dyn Error>>{
    let args:Vec<_>=std::env::args().skip(1).collect();
    if args.len()!=3{return Err("font04_owned image.png ocr.json output.json".into());}
    let image=image::open(&args[0])?.to_rgb8();
    let page=scanweave_core::ocr_page::OcrPage::parse_bytes(&std::fs::read(&args[1])?)?;
    page.validate(&scanweave_core::Limits::m0_defaults())?;page.verify_binding(image.as_raw())?;
    let segmentation=scanweave_io::mask::segment(image.as_raw(),image.width(),image.height());
    let (plan,_)=scanweave_io::ownership::build_plan(&segmentation,image.width(),image.height(),&page);
    let observations:Vec<_>=plan.owned.into_iter().map(|owned|{
        let u=owned.unit;
        serde_json::json!({"id":u.symbol_id,"text":u.semantic_text,"shape_key":u.shape_key,"bbox":u.bbox_px,"ocr_bbox":u.ocr_bbox_px,"width":u.crop_w,"height":u.crop_h,"mask":u.mask,"suspect":owned.suspect,"span_id":u.span_id})
    }).collect();
    if let Some(parent)=Path::new(&args[2]).parent(){std::fs::create_dir_all(parent)?;}
    std::fs::write(&args[2],serde_json::to_vec(&serde_json::json!({"observations":observations,"paper":segmentation.paper,"ink":segmentation.ink,"all_classes":true}))?)?;
    Ok(())
}
