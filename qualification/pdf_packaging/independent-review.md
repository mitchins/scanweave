# Independent implementation and measurement review

Reviewer: independent agent `/root/independent_review`, read-only review of implementation commit `80b2a42`, actual PDFs, machine tables and report. The reviewer did not implement the changes.

## Implementation

Found and corrected during development:

- Compressed font/content stream sizes were initially still reported as decoded sizes. The helper now returns encoded lengths; document stats/candidates use those lengths.
- Sparse free entries needed a complete PDF cross-reference free-object chain. The final implementation rebuilds it, with a bounded-object-group/free-chain test.
- The sidecar path could alias the input. Canonical alias rejection and a regression test protect it.
- Per-page limits now agree with the existing 80M-pixel normalization limit and are checked before OCR. A 512MiB accumulated sample budget is explicit.
- JSON publication is staged before PDF publication, and Poppler/Tesseract identity, arguments and actual hOCR are retained. Two final renames are explicitly not a transaction.

Final source review found no blocking serializer/CLI defect. The compactor is constrained to our own writer output; it is not a third-party PDF parser. CropBox/90-degree rotation geometry was independently checked, then exercised in the executed CLI integration checks.

## Measurements

Confirmed separately:

- pikepdf reference sizes **181,540 / 258,021 B**; shipped Rust output **185,119 / 258,890 B**. These are never conflated.
- Decoded stream equality, complete extraction equality, unchanged sampled native search results and old/new Poppler/PDFium render hashes. The 600-DPI render was strengthened to matched 600 DPI; MediaBox/CropBox/rotation checks are explicit.
- Five-collection / 32-page byte totals: input81,969,566; Adobe4,178,103; ScanWeave81,309,831; OCRmyPDF-O1 82,093,571; O3 15,315,903; archive3,059,648.
- Known CORD numeric results: ScanWeave11/49, Adobe24/49, O1/O3 15/49, archive13/49.
- The 84 source-Tesseract probes: ScanWeave76, Adobe53, O1/O3 66, archive84. The archive arm consumes the same hOCR, so 84/84 is transport, not an independent recognition result.
- Ten worst-case values and the archive glyphless-font OTS failure match saved evidence. Adobe CFF was not asserted to pass standalone TTF OTS.

Reviewer qualifications incorporated into the report:

1. Four pages differ by one pixel between the embedded image and converter-internal rasterization. Shared imagery/physical geometry is not a claim of sample-identical internal rasters.
2. Adobe qpdf status-3 linearization/hint warnings remain disclosed with successful rendering.
3. GNU-time command RSS is not an aggregated process-tree memory peak. A separately labelled sampled process-tree observation was subsequently added; it is not PSS.

The atlas is a negative control: 272B saved with changed rendering, not a product improvement. The later tiny two-tone stencil control is also negative: larger serialized PDF and four changed Poppler pixels; neither control is enabled in the converter.

The review supports the lossless packaging and ordinary-workflow claims. It does **not** support claiming real-domain compression parity with Adobe/OCRmyPDF-O3, universal text correctness or general mask equivalence.

Final counting correction: the form has 500 converter visible-owned glyph occurrences (293 + 207), versus 678 PDFium paintable text characters. Collection converter counts total 4,967; PDFium paintable characters total 5,360. Both are reported separately, without equating text-character counts to outline draws.
