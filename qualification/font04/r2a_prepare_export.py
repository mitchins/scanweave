"""Install research-only observation hooks in an isolated R1 product checkout.

The instrumented executable must reproduce each accepted baseline PDF hash.
Neither this adapter nor its environment hook belongs on the product branch.
"""
from pathlib import Path
import sys


def prepare(checkout):
    src = checkout/'crates/scanweave-io/src'
    assert not (src/'r2a_export.rs').exists(), 'Never overwrite an instrumented checkout'
    reference = Path(__file__).resolve().parents[2]/'crates/scanweave-io/src/font04.rs'
    text = reference.read_text()
    start = text.index('pub fn snapshot(')
    end = text.index('\npub fn apply(', start)
    snapshot = text[start:end]
    first = snapshot.index('        for (oi, o) in ')
    last = snapshot.index('            let source = ', first)
    snapshot = snapshot[:first] + '        for (oi, o) in p.occurrences.iter().enumerate() {\n' + snapshot[last:]
    snapshot = snapshot.replace('    let scope = std::env::var("FONT04_SCOPE").unwrap_or_else(|_| "B1".into());\n', '')
    (src/'r2a_export.rs').write_text('use crate::{document::DocumentPage, units::Unit};\nuse serde_json::{json,Value};\n'+snapshot)
    lib = src/'lib.rs'
    lib.write_text(lib.read_text()+'\nmod r2a_export;\n')
    doc = src/'document.rs'
    text = doc.read_text()
    needle = '    let observations=sharing.map'
    hook = '''    if let Some(directory) = std::env::var_os("FONT04_R2A_EXPORT") {
        let directory = std::path::Path::new(&directory);
        std::fs::create_dir_all(directory).map_err(|e| e.to_string())?;
        std::fs::write(directory.join("source.json"), serde_json::to_vec(&crate::r2a_export::snapshot(&pages, &all_donors)).unwrap()).map_err(|e| e.to_string())?;
    }
'''
    assert needle in text
    text = text.replace(needle, hook+needle, 1)
    needle = '    // 2. document-wide font:'
    hook = '''    if let (Some(directory), Some(rows)) = (std::env::var_os("FONT04_R2A_EXPORT"), observations.as_ref()) {
        let rows: Vec<_> = rows.iter().enumerate().map(|(i,r)| serde_json::json!({
            "member":i,"page":r.page,"occurrence":r.occurrence,"id":r.id,"label":r.label,"field":r.field,"frame":r.frame,
            "canonical":r.canonical.as_ref().map(|c| serde_json::json!({"path":c.shape.path.to_svg(),"anchor":c.shape.anchor_bbox_fu,"ink_span":c.shape.ink_span_fu,"origin":c.origin,"width":c.width,"height":c.height}))
        })).collect();
        std::fs::write(std::path::Path::new(&directory).join("observations.json"), serde_json::to_vec(&rows).unwrap()).map_err(|e| e.to_string())?;
    }
'''
    assert needle in text
    doc.write_text(text.replace(needle, hook+needle, 1))
    text = doc.read_text()
    needle = '    stage_timings.document_font_union_ms = stage_start.elapsed().as_millis();'
    hook = '    if let Some(directory) = std::env::var_os("FONT04_R2A_EXPORT") {\n        let mut bindings = Vec::new();\n        for (pi, page) in pages.iter().enumerate() {\n            for (oi, o) in page.parts.occurrences.iter().enumerate() {\n                bindings.push(serde_json::json!({"page":pi,"occurrence":oi,"cid":o.1+1,\n                    "matrix":crate::glyph_sharing::ownership::default_matrix(&page.parts,&shapes[o.0],o.2)}));\n            }\n        }\n        std::fs::write(std::path::Path::new(&directory).join("native-bindings.json"),serde_json::to_vec(&bindings).unwrap()).map_err(|e|e.to_string())?;\n    }\n'
    assert needle in text
    doc.write_text(text.replace(needle, hook+needle, 1))
    plan = src/'glyph_sharing/plan.rs'
    text = plan.read_text()
    needle = '    Ok(Plan {'
    hook = '''    if let Some(directory) = std::env::var_os("FONT04_R2A_EXPORT") {
        let data = serde_json::json!({"fits":fits,"floors":floors,"bands":bands,"hygiene":screens,"groups":groups.iter().map(|g|serde_json::json!({"canonical":g.canonical,"members":g.members})).collect::<Vec<_>>()});
        std::fs::write(std::path::Path::new(&directory).join("plan.json"),serde_json::to_vec(&data).unwrap()).map_err(|e|e.to_string())?;
    }
'''
    assert needle in text
    plan.write_text(text.replace(needle, hook+needle, 1))


if __name__ == '__main__':
    prepare(Path(sys.argv[1]))
