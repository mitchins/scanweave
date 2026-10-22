# ACR-03 independent full-financial visual review

## Scope and method

Reviewed the actual complete thirteen-page shadow PDF
`financial-all-masked/complete.pdf`, not thirteen separately converted pages.
Compared source `financial-input.pdf`, frozen Adobe XI, ACR-01 product financial
PDF and candidate B. Rendered every page in PDFium and Poppler at 300 DPI using
the existing reviewed fixed-MediaBox/original-CropBox-clip helper. No alignment,
content resizing or candidate-dependent crop fitting was used for measurements.

All thirteen page overviews in both engines were inspected. Actual 300-DPI detail
windows were additionally examined across every page: an upper-body window in
PDFium, and a lower-body or numeric-column window in Poppler. This is sampled
local inspection, not transcription of every number or inspection of every pixel.
Source/Adobe/ACR-01/B sheets and local narrow ACR-01/B crops were used. Render
sheets are retained under `local/financial-all-review/`; the temporary read-only
render script is `/tmp/acr03-financial-review-render.py`.

Fixed normalized source-coordinate windows were:

- upper body: `[0.10, 0.24, 0.48, 0.39]`;
- lower body/table: `[0.10, 0.68, 0.48, 0.83]`;
- right numeric column: `[0.76, 0.63, 0.97, 0.92]`.

No prototype, production code, frozen input or holdout was modified. Only local
rendering artifacts and this review were written.

## Visual findings

**No material new readability or layout defect was identified on the thirteen
completed pages.** Names, body serif text, table columns, currency symbols,
separators/ditto punctuation, rules and inspected totals remain readable. Examples
include $138 55 / $596 05 / $600 00, 373 87 / 421 25, the multi-column fund table,
428239 16 / 8207 58 / 436446 74, and the 185-to-204 vital-statistics total.

Both engines show coherent page geometry. No large rectangular paper hole, lost
column, duplicated text or obvious tile seam was found in the complete page
views. The previous annual-111 circular halo is not conspicuous in the inspected
B total/rule view. Minor warm/soft edge-tone changes and occasional faint local
background variations remain around printing/marks. They do not establish an
observed wrong digit, erased meaningful mark or loss of functional readability
under the revised lossy-output contract. They should not be advertised as perfect
source preservation or as a demonstrably cleaner font.

Adobe remains substantially smaller. Its render often has smoother/heavier glyph
shapes and different paper tonal detail. Candidate B does not establish a new
typographic clarity advantage over the working ACR-01 output on this collection.
The visual pass here does not withdraw the earlier shaded historical-page B
failure or prove that its unknown-paper fallback is correct on arbitrary pages.

## Size and integration judgment

Actual complete-document totals: **9,018,954 B to 8,442,537 B**, a saving of
**576,417 B (6.39%)**. This is a genuine modest shadow-document gain, not an
area-based estimate or a sum of separately embedded page PDFs. It is not rejected
for failing an invented numeric threshold.

The full-financial subset has no material visual blocker in this review.
Nevertheless, **this modest gain alone does not provide a convincing justification
for general production integration of a new object/paper/mask pipeline**. It
shows one fairly uniform-paper collection can retain readability while becoming
slightly smaller. It does not establish broad source-object classification,
unknown-paper eligibility, compositing safety, implementation cost or a substantial
competitive gap closure. Historical shade still requires fallback and other
historical candidates grow. Those costs/risks require their own qualification and
cannot be canceled by a successful financial overview.

Recommendation: preserve this as a positive but limited financial shadow result;
do not infer general product promotion from it. If an operator elects to promote
a narrowly scoped implementation, independent code, semantics, error handling,
determinism, resource limits, fallback and normal CLI qualification are still
required. This visual review neither authorizes new methods nor requests further
codec tuning. No sealed evidence was accessed.
