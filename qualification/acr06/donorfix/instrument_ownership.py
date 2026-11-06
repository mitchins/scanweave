#!/usr/bin/env python3
"""Produce a temporary candidate source file that snapshots ownership masks."""
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();needle='''    let (mut plan, _) = build_plan(&seg, w, h, &ocr);
'''
patch=needle+'''    if let Some(dir) = std::env::var_os("SCANWEAVE_OWNERSHIP_CAPTURE") {
        let pack = |unit: &crate::units::Unit| {
            let mut bits = vec![0u8; unit.mask.len().div_ceil(8)];
            for (i, &value) in unit.mask.iter().enumerate() {
                if value { bits[i / 8] |= 1 << (i % 8); }
            }
            serde_json::json!({"id": unit.symbol_id, "bbox": unit.bbox_px, "width": unit.crop_w, "height": unit.crop_h, "bits": bits})
        };
        let owned: Vec<_> = plan.owned.iter().map(|o| pack(&o.unit)).collect();
        let artwork: Vec<_> = plan.artwork_units.iter().map(|(u, _)| pack(u)).collect();
        let snapshot = serde_json::json!({"page_id": input.page_id, "width": w, "height": h, "owned": owned, "artwork": artwork});
        let path = std::path::PathBuf::from(dir).join(format!("{}.json", input.page_id));
        std::fs::write(path, serde_json::to_vec(&snapshot).unwrap()).unwrap();
    }
'''
assert needle in s
Path(sys.argv[2]).write_text(s.replace(needle,patch,1))
