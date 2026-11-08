from pathlib import Path
p=Path('/tmp/scanweave-trace32/crates/scanweave-io/src/convert.rs')
s=p.read_text()
s=s.replace('    for (symbol, source_key) in local_geometry_fallback {','    let profile_symbols = local_geometry_fallback.clone();\n    for (symbol, source_key) in local_geometry_fallback {')
s=s.replace('            plan.owned[index].unit.shape_key = local.shape_key;','            eprintln!("TRACE32 {} {} success", input.page_id, symbol);\n            plan.owned[index].unit.shape_key = local.shape_key;')
s=s.replace('        } else {\n            missing.insert((symbol,));\n        }\n    }\n    reconstruction.restoration_qualified', '        } else {\n            eprintln!("TRACE32 {} {} failed", input.page_id, symbol);\n            missing.insert((symbol,));\n        }\n    }\n    reconstruction.restoration_qualified')
s=s.replace('    // encoding (four-part key)', '    for (symbol, _) in &profile_symbols {\n        for r in &regions {\n            if r.units.iter().any(|&ui| plan.owned[ui].unit.symbol_id == *symbol) {\n                eprintln!("TRACE32_FINAL {} {} {:?}", input.page_id, symbol, r.disposition);\n            }\n        }\n    }\n\n    // encoding (four-part key)')
p.write_text(s)
