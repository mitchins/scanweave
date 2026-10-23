use std::{io::Read, path::Path};
fn main() -> Result<(), String> {
    let out = std::env::args()
        .nth(1)
        .ok_or("usage: font04_trace output-directory < request.json")?;
    let mut bytes = Vec::new();
    std::io::stdin()
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    let request = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    let (records, _, font) = scanweave_io::font04::trace_batch(&request)?;
    std::fs::create_dir_all(&out).map_err(|e| e.to_string())?;
    std::fs::write(Path::new(&out).join("font.ttf"), font).map_err(|e| e.to_string())?;
    std::fs::write(
        Path::new(&out).join("outlines.json"),
        serde_json::to_vec(&records).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
