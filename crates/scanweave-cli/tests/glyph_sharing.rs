use std::process::Command;

#[test]
fn sharing_flag_validation_precedes_input_work() {
    for point in ["cover-2.0", "cover-1.5", "cover-2.0-ceiling", "unknown"] {
        let out = Command::new(env!("CARGO_BIN_EXE_scanweave"))
            .args([
                "missing-input.pdf",
                "missing-output.pdf",
                "--glyph-sharing",
                point,
            ])
            .output()
            .unwrap();
        assert!(!out.status.success());
        assert!(String::from_utf8_lossy(&out.stderr)
            .contains("--glyph-sharing must be off or cover-2.0-ceiling-q3"));
    }
    let out = Command::new(env!("CARGO_BIN_EXE_scanweave"))
        .args([
            "missing-input.pdf",
            "missing-output.pdf",
            "--profile",
            "faithful",
            "--glyph-sharing",
            "cover-2.0-ceiling-q3",
        ])
        .output()
        .unwrap();
    assert!(!out.status.success());
    assert!(
        String::from_utf8_lossy(&out.stderr).contains("glyph sharing requires --profile clearscan")
    );
}

#[test]
fn q3_rejects_unusable_pdfium_before_input_work() {
    let dir = tempfile::tempdir().unwrap();
    let invalid = dir.path().join("invalid-library");
    std::fs::write(&invalid, b"not a library").unwrap();
    for library in [dir.path().join("missing-library"), invalid] {
        let output = dir.path().join("output.pdf");
        let result = Command::new(env!("CARGO_BIN_EXE_scanweave"))
            .args([
                "missing-input.pdf",
                output.to_str().unwrap(),
                "--glyph-sharing",
                "cover-2.0-ceiling-q3",
            ])
            .env("SCANWEAVE_PDFIUM_LIBRARY", library)
            .env("PATH", dir.path())
            .output()
            .unwrap();
        let stderr = String::from_utf8_lossy(&result.stderr);
        assert!(!result.status.success());
        assert!(stderr.contains("SCANWEAVE_PDFIUM_LIBRARY"), "{stderr}");
        assert!(stderr.contains("native libpdfium path"), "{stderr}");
        assert!(stderr.contains("--glyph-sharing off"), "{stderr}");
        assert!(!stderr.contains("rasterizing"), "{stderr}");
        assert!(!output.exists());
        assert!(!dir.path().join("output.pdf.json").exists());
    }
}

#[test]
fn sharing_off_does_not_check_pdfium() {
    let result = Command::new(env!("CARGO_BIN_EXE_scanweave"))
        .args([
            "missing-input.pdf",
            "missing-output.pdf",
            "--glyph-sharing",
            "off",
        ])
        .env("SCANWEAVE_PDFIUM_LIBRARY", "/nonexistent/libpdfium.so")
        .output()
        .unwrap();
    let stderr = String::from_utf8_lossy(&result.stderr);
    assert!(stderr.contains("read input PDF:"), "{stderr}");
    assert!(!stderr.contains("PDFium"), "{stderr}");
}
