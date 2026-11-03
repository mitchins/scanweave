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
    for point in ["off", "cover-2.0-ceiling-q3"] {
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
        assert!(String::from_utf8_lossy(&out.stderr).contains("read input PDF:"));
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
