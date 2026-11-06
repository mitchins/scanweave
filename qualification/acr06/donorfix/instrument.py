#!/usr/bin/env python3
"""Insert temporary instrumentation into a copy of visual_dict.rs, never commit it."""
import sys
from pathlib import Path
src=Path(sys.argv[1]); dest=Path(sys.argv[2]); s=src.read_text()
needle='''                plan.owned[i].unit.shape_key = donor_key.clone();
                let prototype_id'''
patch='''                if std::env::var_os("SCANWEAVE_DONOR_DEBUG").is_some() {
                    let members: Vec<_> = cohorts[&family_rep].iter().map(|&m| {
                        let d = &plan.owned[m].unit;
                        serde_json::json!({"id": d.symbol_id, "text": d.semantic_text, "ocr": d.ocr_bbox_px, "ink": d.bbox_px})
                    }).collect();
                    eprintln!("DONOR_DEBUG {}", serde_json::json!({"id": u.symbol_id, "text": u.semantic_text, "ocr": u.ocr_bbox_px, "ink": u.bbox_px, "replacement": record.replacement_bbox_px, "donor": donor.symbol_id, "donor_text": donor.semantic_text, "donor_ocr": donor.ocr_bbox_px, "donor_ink": donor.bbox_px, "members": members}));
                }
                plan.owned[i].unit.shape_key = donor_key.clone();
                let prototype_id'''
assert needle in s
dest.write_text(s.replace(needle,patch,1))
