# Frozen development protocol

Before viewing any fresh-set candidate output, define a material OCR regression
as either a loss of at least five source-matched words on a page or a relative
loss of at least 10% where the default recalls at least ten words. Apply this
separately to complete-page and background-only OCR. Also flag a decrease of
more than 5 percentage points in the small-component survival proxy or rule
continuity, and any obvious damage in independent visual review. These are
screening thresholds rather than proof of legibility; Tesseract's English OCR
on historical print is noisy, and mark and line proxies include non-text.

Development split: all historical pages and financial pages 1–7 (one-based).
Held-out group split: remaining financial pages, forms, mixed and receipts.
The single-page, competitive and fresh inputs are additional checks, not
guard-training data. If guard design changes after held-out or fresh outcomes
are examined, the final fresh evaluation requires a newly seeded set and the
change must be disclosed. The layout cost computation stays at the established
200-DPI behavior.

Guard frozen before held-out and fresh result review: decode the 150-DPI JPEG,
resample it to the source residual dimensions, and require every channel of
every pixel to differ by at most five levels. For source horizontal edge pairs
two pixels apart with luminance difference at least 20, require mean absolute
luminance error at most one level (and at most 1% above five levels). Use the
existing encoding if decoding fails, the old representation was not reduced,
or the proposed image is not smaller. The five-level maximum also limits
changes to low-contrast marks and color; the edge measure addresses fine ink.
These deliberately strict engineering limits are not a calibrated guarantee.
The development evidence includes a substantial page-3 OCR regression despite
few errors of 20 or more levels, and small-component losses on all twelve
development pages. The stricter rule favors no saving over unknown damage.
