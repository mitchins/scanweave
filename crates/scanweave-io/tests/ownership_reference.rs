//! Demonstrates the scope of the existing component-identity invariant.
//! This is not a new validation gate and does not authorize mutating units.
use scanweave_io::ownership::{OwnedUnit, OwnershipPlan};
use scanweave_io::units::Unit;

#[test]
fn component_id_invariant_does_not_validate_added_mask_pixels() {
    let unit = Unit {
        shape_key: "original".into(), span_id: "s".into(), symbol_id: "x".into(),
        semantic_text: "x".into(), bbox_px: [0., 0., 2., 2.],
        ocr_bbox_px: [0., 0., 2., 2.], crop_w: 2, crop_h: 2,
        mask: vec![true, false, false, false], gray_samples: None, gray_halo: None,
    };
    let mut plan = OwnershipPlan {
        owned: vec![OwnedUnit { unit, components: vec![1], slots: vec![], suspect: false }],
        components_total: 1, components_owned: 1, components_artwork: 0,
        ..OwnershipPlan::default()
    };
    assert!(plan.visual_invariant_ok());
    // This pixel was not a member of the original foreground component.
    plan.owned[0].unit.mask[1] = true;
    assert!(plan.visual_invariant_ok(), "the invariant checks component IDs, not changed mask pixels");
}

#[test]
fn component_id_invariant_does_not_detect_mask_overlap_with_artwork() {
    let make = |id: &str, mask| Unit {
        shape_key: id.into(), span_id: "s".into(), symbol_id: id.into(),
        semantic_text: "".into(), bbox_px: [0., 0., 2., 2.],
        ocr_bbox_px: [0., 0., 2., 2.], crop_w: 2, crop_h: 2,
        mask, gray_samples: None, gray_halo: None,
    };
    let mut plan = OwnershipPlan {
        owned: vec![OwnedUnit { unit: make("text", vec![true, false, false, false]), components: vec![1], slots: vec![], suspect: false }],
        artwork_units: vec![(make("art", vec![false, true, false, false]), vec![2])],
        components_total: 2, components_owned: 1, components_artwork: 1,
        ..OwnershipPlan::default()
    };
    assert!(plan.visual_invariant_ok());
    plan.owned[0].unit.mask[1] = true;
    assert!(plan.owned[0].unit.mask[1] && plan.artwork_units[0].0.mask[1]);
    assert!(plan.visual_invariant_ok(), "unchanged component IDs conceal overlapping masks");
}
