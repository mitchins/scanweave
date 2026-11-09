use scanweave_io::convert::{convert_parts, Input, Policy};

fn page(paper: u8, marks: u8) -> Input {
    let (w, h) = (48u32, 48u32);
    let mut rgb = vec![paper; (w * h * 3) as usize];
    for y in 8..40 {
        for x in 8..40 {
            let i = ((y * w + x) * 3) as usize;
            rgb[i..i + 3].fill(marks);
        }
    }
    Input {
        rgb,
        width: w,
        height: h,
        page_id: "polarity".into(),
        spans: vec![],
        protected_regions: vec![],
        raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, h as f64 * 0.24],
        pixel_sha256: None,
    }
}

#[test]
fn inverted_no_vector_page_is_not_routed() {
    let policy = Policy {
        profile: "clearscan".into(),
        ..Policy::default()
    };
    for input in [page(0, 240), page(20, 250)] {
        let (parts, report) = convert_parts(&input, &policy).unwrap();
        assert!(report.polarity_inverted);
        assert_eq!(report.polarity_visible_occurrences, 0);
        assert!(!report.polarity_raster_baseline);
        assert!(!parts.raster_baseline);
    }
}

#[test]
fn normal_estimate_does_not_route() {
    let policy = Policy {
        profile: "clearscan".into(),
        ..Policy::default()
    };
    let (parts, report) = convert_parts(&page(250, 10), &policy).unwrap();
    assert!(!parts.raster_baseline);
    assert!(!report.polarity_raster_baseline);
    assert!(report.polarity_ink_luminance < report.polarity_paper_luminance);
}
