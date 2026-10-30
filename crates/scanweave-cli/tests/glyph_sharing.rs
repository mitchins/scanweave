use std::process::Command;
#[test]
fn sharing_flag_validation_precedes_input_work() {
    for (profile, point, message) in [
        (
            "clearscan",
            "unknown",
            "--glyph-sharing must be off, cover-2.0, cover-2.0-ceiling or cover-1.5",
        ),
        (
            "faithful",
            "cover-2.0",
            "glyph sharing requires --profile clearscan",
        ),
    ] {
        let out = Command::new(env!("CARGO_BIN_EXE_scanweave"))
            .args([
                "missing-input.pdf",
                "missing-output.pdf",
                "--profile",
                profile,
                "--glyph-sharing",
                point,
            ])
            .output()
            .unwrap();
        assert!(!out.status.success());
        assert!(String::from_utf8_lossy(&out.stderr).contains(message));
    }
}

/// Full financial input is deliberately local and never committed. Run with
/// SCANWEAVE_FONT04_FINANCIAL_INPUT and optional FONT04_DEFAULT_OUTPUT set.
#[test]
#[ignore = "requires the owner-provided local financial document and OCR tools"]
fn financial_default_byte_identity() {
    let input = std::env::var_os("SCANWEAVE_FONT04_FINANCIAL_INPUT")
        .expect("set SCANWEAVE_FONT04_FINANCIAL_INPUT");
    let directory = tempfile::tempdir().unwrap();
    let output = std::env::var_os("FONT04_DEFAULT_OUTPUT")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| directory.path().join("default.pdf"));
    let status = Command::new(env!("CARGO_BIN_EXE_scanweave"))
        .arg(input)
        .arg(&output)
        .args(["--dpi", "300", "--profile", "clearscan"])
        .status()
        .unwrap();
    assert!(status.success());
    assert_eq!(
        scanweave_core::hash_hex(&std::fs::read(output).unwrap()),
        "74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f"
    );
}
