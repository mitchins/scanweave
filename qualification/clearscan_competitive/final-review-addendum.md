# Final report consistency addendum

Reviewed the report, refreshed scorecard, run manifest, validity records, final renderer outputs, semantic audit, ownership audit, and full-source-font control against commit `08431a778f4373f7761ba796fdf631962738e5ae`.

## Consistency result

The main reported measurements and qualifications agree with the current artifacts:

- `scorecard.json` names starting head `c20a8a9…`, implementation head `08431a7…`, and current 300/600 PDF hashes and byte sizes. Those match the PDFs on disk and `run-manifest.json`.
- Table glyph scores match exact-size isolated metrics in the scorecard. The Poppler source values (0.85458 at 300 and 0.91652 at 600) match the rendered image-only PDF metrics; raw input sample IoUs (0.94516 and 0.97807) are presented separately. The report's footnote explains this distinction.
- The 300/600 stage means, final vector coverage, stream accounting, ownership totals, and final PDF sizes agree with the JSON evidence. The raster-only audit reports zero dark raster pixels in emitted vector-occurrence crops at both DPIs, with 744/5,443 source-dark pixels outside the audited vector-or-raster union, as stated.
- The semantic audit covers 17 documents and 31 pages; all 31 have exact nonspace CID-to-ActualText sequences. This supports the stated transport result while leaving the separate real-renderer reading-order, underscore, and U+FFFE limitations explicit.
- `validity.json` contains 21 PDFs: all 19 ScanWeave files and Adobe 300 have qpdf status 0; Adobe 600 alone has status 3 with the preserved linearization/hint-table warnings. The 21 corresponding Poppler/PDFium render artifacts exist. The report does not claim a clean qpdf pass for Adobe 600.
- The report's full-source-font control values (6,642,247 B; 0.85807 Poppler / 0.82821 PDFium on 515 accepted occurrences) match `300/source-font-control/metrics.json`. The embedded source TTF hashes match the original licensed files; OCR extraction matches under both renderers.
- The exact 300-DPI deterministic rerun currently at `/tmp/scanweave-final-repeat.pdf` hashes to `515294f52a947153357a30a518f6bf7fb9b4eeb4ed1ed44f9fefd966897df725`, matching the final PDF. This supports the report's determinism statement.

## Evidence maintenance notes

1. The earlier `final-review.md` still contains the prior stale-scorecard finding (old 5f88c66 hash/sizes). The final report now cites that file as an independent review artifact, so readers may see an apparent contradiction. Treat that specific finding as superseded by this addendum and the refreshed scorecard. Updating `final-review.md` or adding a prominent superseded note would make the evidence set self-consistent.
2. The final repeat PDF used to verify determinism is in `/tmp`, while the persistent manifest lists only the final canonical output. For durable reproducibility, record the repeat output hash and command in a qualification artifact (or preserve the repeated PDF); the current hash comparison itself passes.
3. “Genuine 300/600 DPI” refers to the fixture's actual raster pixel density at its declared 432 × 216 pt physical size. These are generated synthetic pages, not scans acquired on a physical scanner. The report identifies the fixture as synthetic elsewhere; retaining that wording nearby avoids implying scanner-acquisition provenance.

No material numerical contradiction was found in the final report or updated Adobe summary. The remaining notes concern superseded review text and artifact durability/wording, not a failure of the measured product results.
