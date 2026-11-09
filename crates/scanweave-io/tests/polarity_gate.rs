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

fn outlined_text_page(inverted: bool) -> Input {
    use scanweave_io::convert::{SpanInput, SymbolInput};
    let (w, h) = (300u32, 160u32);
    let mut rgb = vec![245u8; (w * h * 3) as usize];
    let mut rect = |x0: u32, y0: u32, x1: u32, y1: u32, color: u8| {
        for y in y0..y1 {
            for x in x0..x1 {
                let i = ((y * w + x) * 3) as usize;
                rgb[i..i + 3].fill(color);
            }
        }
    };
    if inverted {
        rect(0, 0, w, 8, 0);
        rect(0, h - 8, w, h, 0);
        rect(0, 0, 8, h, 0);
        rect(w - 8, 0, w, h, 0);
    }
    // Dark rules split the surrounding light foreground into components whose
    // bounds do not overlap the O's counter. This lets that paper-shaped
    // counter survive region planning as a visible occurrence on main.
    if inverted {
        rect(70, 8, 100, h - 8, 20);
        rect(140, 8, 170, h - 8, 20);
        rect(8, 25, w - 8, 55, 20);
        rect(8, 105, w - 8, 135, 20);
    } else {
        rect(70, 25, 170, 135, 20);
    }
    rect(100, 55, 140, 105, 245);
    let polygon = if inverted {
        vec![[98.0, 53.0], [142.0, 53.0], [142.0, 107.0], [98.0, 107.0]]
    } else {
        vec![[68.0, 23.0], [172.0, 23.0], [172.0, 137.0], [68.0, 137.0]]
    };
    let spans = vec![SpanInput {
        id: "word".into(),
        text: "O".into(),
        separator_after: "".into(),
        polygon: polygon.clone(),
        symbols: vec![SymbolInput {
            id: "symbol".into(),
            range: (0, 1),
            polygon,
        }],
    }];
    Input {
        rgb,
        width: w,
        height: h,
        page_id: if inverted { "inverted" } else { "normal" }.into(),
        spans,
        protected_regions: vec![],
        raster_to_page_pt: [0.24, 0.0, 0.0, -0.24, 0.0, h as f64 * 0.24],
        pixel_sha256: None,
    }
}

/// Count text-show operations by their PDF text rendering mode. The fixture
/// uses simple text runs, so each show is either filled or invisible.
fn text_show_counts(pdf: &[u8]) -> Vec<(usize, usize)> {
    use hayro::hayro_syntax::content::ops::TypedInstruction;
    let parsed = hayro::hayro_syntax::Pdf::new(pdf.to_vec()).unwrap();
    parsed
        .pages()
        .iter()
        .map(|page| {
            let mut mode = 0;
            let (mut visible, mut invisible) = (0, 0);
            let mut operations = page.typed_operations();
            while let Some(instruction) = operations.next() {
                match instruction {
                    TypedInstruction::TextRenderingMode(value) => mode = value.0.as_i64(),
                    TypedInstruction::ShowText(_)
                    | TypedInstruction::ShowTexts(_)
                    | TypedInstruction::NextLineAndShowText(_)
                    | TypedInstruction::ShowTextWithParameters(_) => {
                        if mode == 3 {
                            invisible += 1;
                        } else {
                            visible += 1;
                        }
                    }
                    _ => {}
                }
            }
            (visible, invisible)
        })
        .collect()
}

#[test]
fn inverted_visible_glyph_routes_to_exact_searchable_baseline() {
    let input = outlined_text_page(true);
    let policy = Policy {
        profile: "clearscan".into(),
        ..Policy::default()
    };
    let (parts, report) = convert_parts(&input, &policy).unwrap();
    assert!(report.polarity_inverted);
    assert!(report.polarity_visible_occurrences > 0);
    assert!(parts.raster_baseline);
    assert!(report.polarity_raster_baseline);
    assert_eq!(report.compact_decision, "encoder_ineligible");
    assert_eq!(parts.patches.len(), 1);
    assert_eq!(
        parts.patches[0].bbox_px,
        [0.0, 0.0, input.width as f64, input.height as f64]
    );
    assert_eq!(parts.patches[0].rgb, input.rgb);
    assert_eq!(report.selected, "raster_baseline");
    assert!(!report.semantic_owner.is_empty());
    assert!(report
        .semantic_owner
        .values()
        .all(|owner| owner == "invisible"));
    assert!(report
        .occurrences
        .iter()
        .any(|occ| occ.symbol_id == "symbol" && occ.owner == "invisible"));
    assert!(report
        .occurrences
        .iter()
        .all(|occ| occ.owner != "visible_tounicode"));
    assert_eq!(report.coverage.text_ink_px_vector, 0);
    assert_eq!(
        report.coverage.text_ink_px_raster,
        report.coverage.text_ink_px_total
    );
    assert!(report.coverage.text_ink_px_raster > 0);
    assert_eq!(
        report.fidelity.raster_ink_px,
        report.coverage.text_ink_px_raster + report.coverage.other_ink_px
    );
    assert!(report.fidelity.vector_ink_iou_min.is_none());
    assert!(report.fidelity.vector_ink_iou_mean.is_none());
    assert!(report.fidelity.preservation_ink_iou_min.is_none());
    assert_eq!(report.raster_ink_pixels_suppressed, 0);
    assert_eq!(report.antialias_fringe_pixels_suppressed, 0);
    assert_eq!(report.raster_bytes, input.rgb.len());
    let output = scanweave_io::convert::convert(&input, &policy).unwrap();
    assert_eq!(output.report.selected, "raster_baseline");
    assert_eq!(output.pdf_bytes, output.b0_bytes);
    assert_eq!(text_show_counts(&output.pdf_bytes), vec![(0, 1)]);
}

#[test]
fn document_routes_only_the_inverted_page() {
    let policy = Policy {
        profile: "clearscan".into(),
        ..Policy::default()
    };
    let inputs = [outlined_text_page(true), outlined_text_page(false)];
    let output = scanweave_io::document::convert_document("polarity", &inputs, &policy).unwrap();
    let reports = &output.report.page_reports;
    assert_eq!(reports.len(), 2);
    assert!(reports[0].polarity_inverted && reports[0].polarity_raster_baseline);
    assert!(reports[0].polarity_visible_occurrences > 0);
    assert!(!reports[1].polarity_inverted && !reports[1].polarity_raster_baseline);
    assert!(reports[1].polarity_visible_occurrences > 0);
    let counts = text_show_counts(&output.pdf_bytes);
    assert_eq!(counts.len(), 2);
    assert_eq!(counts[0].0, 0, "routed page must paint no text");
    assert!(counts[0].1 > 0, "routed page must retain invisible text");
    assert!(counts[1].0 > 0, "normal page must retain visible text");
}

#[test]
fn tonal_inverted_page_uses_explicit_compact_representation() {
    let mut input = outlined_text_page(true);
    let source = image::RgbImage::from_raw(input.width, input.height, input.rgb.clone()).unwrap();
    let scaled = image::imageops::resize(
        &source,
        input.width * 4,
        input.height * 4,
        image::imageops::FilterType::Nearest,
    );
    input.width *= 4;
    input.height *= 4;
    input.rgb = scaled.into_raw();
    let mut noise = 12345u32;
    for y in 0..input.height as usize {
        for x in 0..input.width as usize {
            noise = noise.wrapping_mul(1664525).wrapping_add(1013904223);
            let i = (y * input.width as usize + x) * 3;
            if input.rgb[i] == 245 {
                input.rgb[i..i + 3]
                    .fill((160 + (x % 85) as i32 + ((noise >> 24) % 5) as i32 - 2) as u8);
            }
        }
    }
    for span in &mut input.spans {
        for point in &mut span.polygon {
            point[0] *= 4.0;
            point[1] *= 4.0;
        }
        for symbol in &mut span.symbols {
            for point in &mut symbol.polygon {
                point[0] *= 4.0;
                point[1] *= 4.0;
            }
        }
    }
    input.raster_to_page_pt[5] = input.height as f64 * 0.24;
    let policy = Policy {
        profile: "clearscan".into(),
        ..Policy::default()
    };
    let (parts, report) = convert_parts(&input, &policy).unwrap();
    assert!(report.polarity_inverted && report.polarity_visible_occurrences > 0);
    assert!(report.polarity_raster_baseline);
    assert!(
        !parts.raster_baseline,
        "exact baseline contract remains distinct"
    );
    assert!(parts.compact_source.is_some());
    assert_eq!(report.selected, "raster_baseline_compact");
    assert_eq!(report.raster_fidelity, "clearscan_compact_lossy");
    assert_eq!(report.compact_decision, "accepted");
    assert!(report.compact_source_mae.is_some());
    assert!(report.compact_ink_recall.is_some());
    assert_eq!(report.fidelity.raster_ink_px, 0);
    let output = scanweave_io::convert::convert(&input, &policy).unwrap();
    assert_eq!(output.report.selected, "raster_baseline_compact");
    assert_eq!(output.report.raster_encoding, "jpeg");
    assert_ne!(output.pdf_bytes, output.b0_bytes);
    assert_eq!(text_show_counts(&output.pdf_bytes)[0].0, 0);
    assert_eq!(text_show_counts(&output.b0_bytes)[0].0, 0);
    let document = scanweave_io::document::convert_document(
        "compact",
        &[input, outlined_text_page(false)],
        &policy,
    )
    .unwrap();
    assert_eq!(document.report.page_reports[0].raster_encoding, "jpeg");
    assert_eq!(
        document.report.page_reports[0].raster_fidelity,
        "clearscan_compact_lossy"
    );
    assert_ne!(
        document.report.page_reports[1].raster_encoding,
        "pending_assembly"
    );
    let counts = text_show_counts(&document.pdf_bytes);
    assert_eq!(counts[0].0, 0);
    assert!(counts[1].0 > 0);
}
