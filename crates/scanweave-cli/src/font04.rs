//! Explicit discovery mode; Python scientific tooling is an opt-in dependency.
use scanweave_io::{document::DocumentPage, units::Unit};
use serde_json::{json, Value};
use std::{
    io::Write,
    path::Path,
    process::{Command, Stdio},
};

fn planner(stage: &str, directory: &Path, data: &Value) -> Result<Value, String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let python = std::env::var_os("SCANWEAVE_RESEARCH_PYTHON")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| root.join("qualification/.venv/bin/python"));
    let mut child = Command::new(python)
        .arg(root.join("qualification/font04/planner.py"))
        .arg(stage)
        .arg(directory)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| format!("FONT04 scientific planner: {e}"))?;
    child
        .stdin
        .take()
        .ok_or("planner stdin")?
        .write_all(&serde_json::to_vec(data).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    let output = child.wait_with_output().map_err(|e| e.to_string())?;
    if !output.status.success() {
        return Err(format!("FONT04 planner failed: {}", output.status));
    }
    serde_json::from_slice(&output.stdout).map_err(|e| e.to_string())
}

pub fn experiment(
    pages: &mut [DocumentPage],
    donors: &[Vec<Unit>],
    directory: &Path,
) -> Result<(), String> {
    std::fs::create_dir_all(directory).map_err(|e| e.to_string())?;
    let snapshot = scanweave_io::font04::snapshot(pages, donors);
    let request = planner("prepare", directory, &snapshot)?;
    let (outlines, shapes, font) = scanweave_io::font04::trace_batch(&request)?;
    std::fs::write(directory.join("canonical.ttf"), font).map_err(|e| e.to_string())?;
    let plan = planner(
        "plan",
        directory,
        &json!({"snapshot":snapshot,"outlines":outlines}),
    )?;
    scanweave_io::font04::apply(pages, &plan, &shapes)
}
