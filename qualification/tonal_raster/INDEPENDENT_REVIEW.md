# Independent review

Reviewer: existing `/root/independent_review`, separate from implementation.

- Product source-import review found default-colour overrides and cumulative hint decode allocation gaps; both corrected in 99ec072 and retested. No remaining merge blocker found.
- Tonal implementation review checked unchanged-page eligibility, decoded sample/source binding, full-PDF size selection, deterministic resource separation, preserved JPEG passthrough, faithful and native-exception exclusion.
- Requested light-ridge checks in addition to dark ridges and a bounded 16 MP image cap; both implemented without relaxing existing thresholds.
- Inspected source/Q100 primary pages in both renderers at normal and enlarged scales; zero lost qualifying dark/light ridges independently measured. No apparent missing faint strokes, receipt punctuation, fine rules or artwork.
- Reviewed additional CORD06/07/08 and history00 source/output comparisons in both renderers. History00 preserves faint show-through, blackletter, ornament, red stamp and texture (MAE 0.673, max channel difference 8 in both renderers). No objectionable artifact found. All eight changed pages covered.
- Checked matched collection sums, non-image-stream equality and unchanged vector counts. No JPEG-related glyph improvement claim is supported or made.

No blocking implementation or measured-evidence finding remains. This is bounded development-corpus review; it does not prove safe lossy encoding on every possible document. Current OCR and partially reconstructed-page raster costs remain limitations.
