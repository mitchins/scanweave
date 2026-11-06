#!/usr/bin/env python3
"""Generate temporary targeted mask instrumentation from the original visual_dict.rs."""
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(); needle='''                plan.owned[i].unit.shape_key = donor_key.clone();
                let prototype_id'''
patch='''                if std::env::var_os("SCANWEAVE_DONOR_MASK_DEBUG").is_some() && ["w000053s0000","w000053s0001","w000102s0000","w000102s0001","w000130s0001","w000175s0001","w000180s0001","w000471s0000","w000471s0001","w000070s0000","w000106s0006","w000005s0011"].contains(&u.symbol_id.as_str()) {
                    let placed=record.replacement_bbox_px.unwrap();
                    let neighbors: Vec<_> = plan.owned.iter().filter(|o| o.unit.symbol_id != u.symbol_id && !o.unit.symbol_id.starts_with("__doc_donor:") && o.unit.bbox_px[0] < placed[2] && placed[0] < o.unit.bbox_px[2] && o.unit.bbox_px[1] < placed[3] && placed[1] < o.unit.bbox_px[3]).map(|o| serde_json::json!({"id":o.unit.symbol_id,"bbox":o.unit.bbox_px,"width":o.unit.crop_w,"height":o.unit.crop_h,"mask":o.unit.mask})).collect();
                    eprintln!("DONOR_MASK_DEBUG {}", serde_json::json!({"id":u.symbol_id,"text":u.semantic_text,"bbox":u.bbox_px,"width":u.crop_w,"height":u.crop_h,"mask":u.mask,"replacement":placed,"donor":donor.symbol_id,"donor_width":donor.crop_w,"donor_height":donor.crop_h,"donor_mask":donor.mask,"neighbors":neighbors}));
                }
                plan.owned[i].unit.shape_key = donor_key.clone();
                let prototype_id'''
assert needle in s
Path(sys.argv[2]).write_text(s.replace(needle,patch,1))
