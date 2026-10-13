//! Known-answer tests for canonical pixel hash v1 (SPEC Appendix A).
//! Expected values independently computed with a Python reference implementation.

use scanweave_core::pixel_hash::{pixel_hash, CanonicalFormat, ColourTag};

#[test]
fn gray8_known_answer() {
    let samples = [0u8, 255, 128, 1, 254, 0, 7, 9];
    let h = pixel_hash(
        CanonicalFormat::Gray8,
        4,
        2,
        ColourTag::Srgb,
        None,
        &samples,
    )
    .unwrap();
    assert_eq!(
        h,
        "063b1c73e3ef7c42a32dc8d722efa7f5efa2b2dad11f91278b480556a5ca399a"
    );
}

#[test]
fn rgb8_known_answer() {
    let samples = [255u8, 0, 0, 0, 255, 0];
    let h = pixel_hash(CanonicalFormat::Rgb8, 2, 1, ColourTag::Srgb, None, &samples).unwrap();
    assert_eq!(
        h,
        "e135ce513322ae419170a9de2f35ea2c8a03efa81f883fe5e4d2ca5efc8c07aa"
    );
}

#[test]
fn mono1_msb_known_answer() {
    // 8x1 pixel row 10101010 -> packed byte 0b10101010 (high bit first, 1=white)
    let samples = [0b10101010u8];
    let h = pixel_hash(
        CanonicalFormat::Mono1Msb,
        8,
        1,
        ColourTag::GrayGamma22,
        None,
        &samples,
    )
    .unwrap();
    assert_eq!(
        h,
        "c2b372bafbd231c925d4089e6c38cb9139b9aa6ac2b4be909bfd2438a0aeab6e"
    );
}

#[test]
fn rgba16be_icc_known_answer() {
    let samples = [0x12u8, 0x34, 0xAB, 0xCD, 0x00, 0xFF, 0x12, 0x34];
    let icc = "ab".repeat(32);
    let h = pixel_hash(
        CanonicalFormat::Rgba16Be,
        1,
        1,
        ColourTag::Icc,
        Some(&icc),
        &samples,
    )
    .unwrap();
    assert_eq!(
        h,
        "c93d2714aad4896ef57eae348f72deda00c982a3488d8b4ef108002bcce2593c"
    );
}

#[test]
fn icc_tag_requires_hash() {
    // colour_tag=icc with null ICC hash is invalid (SPEC Appendix A)
    let result = pixel_hash(CanonicalFormat::Gray8, 1, 1, ColourTag::Icc, None, &[0]);
    assert!(
        matches!(result, Err(scanweave_core::error::ScanWeaveError::InvalidInput { .. })),
        "icc tag with null icc hash must be rejected as InvalidInput"
    );
}
