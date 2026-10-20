# Donor repair closure

The unchanged `cargo test -p m0-font-pdf --test m1d_reconstruction` failed before correction. The 10 intact primary e witnesses and style compatibility were already present. Candidate discovery compared the damaged s00 only with medoid s05 (normalized IoU .69312169), missing actual members s03/s07/s11 (each .83679525). Alternate serif e witnesses remain .567–.601. Registration alone did not fix the medoid fit.

One targeted correction: only for a density-marked damaged target whose existing medoid misses the existing .78 gate, inspect actual members of that already-qualified cohort. Require at least three distinct members to meet the unchanged .78 gate. Trace the selected actual witness and record its provenance separately; immutable source shape keys prevent a previously remapped shape key from overwriting the medoid outline. Ordinary healthy reuse is unchanged. Repair reporting retains the original `repaired_from_document_donors` decision name. No thresholds, OCR hypotheses or faithful logic were changed.

The original test now passes without deleting or relaxing an assertion. Additional assertions bind emitted prototype geometry to the original selected witness key. Exactly s00 is repaired; actual witness s11, similarity .83679525, source-mask IoU .78805970, traced-prototype IoU .95899054. The alternate face and damaged targets are excluded from the intact donor cohort.

Evaluator-only pristine typography confirms a genuine rendered repair at the original page coordinates: degraded-source IoU .81372549; completed ClearScan Poppler .97115385 and PDFium .97435897. PDFium extraction is unchanged; Poppler differs only in whitespace, native search succeeds, qpdf/OTS pass. See `repair-evaluation.json` and `donor-comparison.png`.

The old standalone evaluator additionally assumes faithful-to-source IoU must exceed repaired-to-source IoU. That assertion fails with Poppler source-patch sampling (faithful .76791809 vs repaired .79421222), despite the visibly recovered crossbar and higher pristine-relative accuracy. Its failure is retained in `donor-render-evaluation.log`; the evaluator was not weakened. The new comparison records both source and pristine errors and both renderers. PDFium's 32-bit page-size rounding is bounded at the whole-page canvas (effective DPI 299.99999188 rather than ceil to 471 rows); no glyph-wise alignment is used.

This is one implementation approach, not a threshold reduction. Independent review diagnosed the representative-only miss and required immutable witness provenance. Full unfiltered CI contracts are executed separately; no skips are added.

Independent review found no blocking threshold/provenance issue. Its follow-up suggestions were implemented: selected donor membership is tied to the intact primary cohort, and source-key snapshots avoid duplicating all masks/grayscale buffers.
