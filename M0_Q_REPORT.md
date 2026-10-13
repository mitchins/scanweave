# M0-Q Gate Report — qualification closure

Date: 2024-10-14. Frozen baseline: commit `3172a32` (tag `m0-provisional-baseline`);
post-review repairs and Q-phase tooling landed in subsequent commits (listed below).
Charter: operator message of 2024-10-14 (5 points). No architecture/algorithm/interface
changes were made; defect repairs are itemized in §2.

## 1. Reproduction (charter point 1) — PASS

- Fresh clone → from-source build → full suite: **36 cargo tests pass** (incl. the E0
  four-part-key mutation property test), schema fixture layer green (3 positive / 6
  negative), checks.py 7 pages + 8/8 E-proofs, measure.py all B0 checks true.
- **28/28 acceptance artifacts byte-identical** between independent checkouts
  (out.pdf / out.ttf / b0_raster.pdf / b0_notext.pdf × 7 pages; SHA-256 table in
  `repro_hashcheck.json`, narrative in `qualification/REPRODUCTION.md`).
- Commands, versions, exit codes recorded in REPRODUCTION.md.

## 2. Visual-failure characterization (charter point 2) — CHARACTERIZED; policy amendment DRAFTED (review pending)

Evidence (`qualification/characterization.json`):

1. **600 dpi convergence: IoU 1.0 in BOTH engines** (rendered at 600 dpi, downsampled to
   the 300 dpi grid vs source). The outlines and placement are geometrically correct; the
   300 dpi binary-mask differences are rasterization detail.
2. **PDFium vs Poppler signed displacement** (p04/p05/p08): mean |d| 0.199 px, 80% of
   boundary points < 0.5 px, max 1.0 px, no systematic direction (mean_dx −0.146 px).
   Poppler-vs-source integer boundary displacement is 0.0. Conclusion: PDFium's
   ~1.1 px p95 is AA-threshold wobble on shallow anti-aliased ramps, NOT a geometry or
   placement defect. No repair indicated; no thresholds changed.
3. **p01 MAE 0.0206 decomposition**: the flat background differs by ~0.02/255 (negligible);
   the difference concentrates in the anti-aliased ramp band where the SOURCE fixture's
   PIL rasterization is softer than the font rasterizer's crisp edges (masks are
   pixel-identical at the threshold; the raw-value MAE measures fixture rasterization
   softness as much as reconstruction). The p01 miss is 3% over the 0.02 limit.
4. **p04 `fi` 1px**: sub-pixel metric confirms p95 1.01/1.07, max 1.32/1.07 — single-glyph,
   both engines, deterministic; unchanged from the M0 report disclosure.

**Proposed versioned policy amendment `m0-qual-1` (DRAFT — requires independent review
before adoption; current gates remain as-is until then):**
(a) geometric fidelity is judged by ink-mask IoU + sub-pixel symmetric edge distance
against the source ink (the measures that isolate geometry from rasterizer AA);
(b) raw-channel MAE is reported ink-weighted and background-weighted separately (as
QUALIFICATION §4.2 already requires) and the flat 0.02 whole-page MAE criterion is
replaced by background MAE ≤ 0.01 and solid-region MAE ≤ 0.03 on the same data.
Rationale: the current whole-page MAE conflates the reference fixture's own
anti-aliasing softness with reconstruction error, and cross-engine AA differences
(documented above) dominate at 300 dpi. No threshold is relaxed in this report; the
amendment takes effect only after review.

Localized evidence for counters/punctuation/kana/financial symbols: `p08_symbols`
fixture added (`. , - $ %`, `1,234.56`, `-42`): qpdf/OTS/extraction pass; per-symbol
trace metrics within budget (trace ≤ 0.497 px); gate results in probe_results.json
(same AA-dominated pattern as other pages).

## 3. Benign pilot corpus (charter point 3) — BLOCKED (environment)

- No corpus is mounted on this machine (checked 2024-10-14; filesystem scan recorded in
  the session ledger). Nothing was fabricated or substituted.
- Turnkey adapter delivered: `qualification/corpus_adapter.py` (expected layout,
  document-level manifest, split isolation, pixel-hash binding; see file header).
- When mounted: `<corpus-root>/<stratum>/<document>/*.png + *.hocr` → adapter → page
  bundles → the committed suite runs unchanged.

## 4. External baselines (charter point 4) — PASS (executed, settings recorded)

Built from pinned sources without root: libtiff 4.6.0 (sha256 88b3979e…) → leptonica
1.85.0 (sha256 3745ae3b…) → tesseract 5.5.0 (sha256 f2fb34ca…), OpenJPEG 2.5.2
(sha256 90e3896f…); OCRmyPDF 17.13.0 (venv); InternetArchive archive-pdf-tools 1.5.7
(commit 8fe8b5b7…) with ONE recorded 6-line compatibility shim (PyMuPDF ≥ 1.22 removed
`getPageImageList`; Python 3.12 has no legacy build — shim recorded in LEDGER.md).
Language data: eng.traineddata (tessdata_fast, sha256 7d4322bd…).

**Real-tesseract end-to-end (UC-01)**: Tesseract 5.5.0 `-c hocr_char_boxes=1` on a
realistic 300-dpi text page → hOCR (118 chars, 118 x_conf values) → `hocr2json`
(normalized, validated, granularity symbol) → reconstruction: 47 glyph shapes /
113 occurrences; qpdf ✓; OTS ✓; B0 transport full text.

**Comparative table — identical sources, same tesseract OCR:**

| Tool (p09 single page) | bytes | ink IoU | transport |
|---|---|---|---|
| source PNG | 37,740 | — | — |
| IA MRC (recode_pdf, JP2 `-r 500/750`) | 45,024 | 0.8485 | 118 chars |
| OCRmyPDF 17.13 (`--force-ocr --output-type pdf --optimize 0`) | 40,127 | 0.7076 | 118 chars |
| **ours B2 (reconstruction)** | **24,003** | **0.8312** | 113 chars ⚠ |
| ours B0 (searchable raster) | 50,291 | 0.8508 | 113 chars ⚠ |

**Repeated-text 4-page document (p10):** source 164,141 B; ours B2 (sum of pages)
**100,174 B** = **0.66× OCRmyPDF (150,077 B) and 0.52× IA MRC (189,221 B)**; B0
216,444 B. Repeated-glyph sharing works on real OCR (e.g. `o` reused across contexts:
gid2 cids [1,33]).

**⚠ Known defect found and quantified (charter point 4's anti-fallback concern applies
to fidelity, and this is a fidelity-side loss):** on 36-px kerned text, touching
characters rasterize as ONE component; the M0 probe's disjoint ownership assigns the
component to one symbol and the paired symbol is dropped — **5 of 118 characters
(4.2%) lost in reconstruction text** on p09 (e.g. `Accounthlder`, `IV-2026`). The B0
raster baseline carries the full text. Component splitting / multi-symbol shared units
is scoped as the FIRST M1 ownership-solver item (SPEC §5.2/§5.3); no incorrect
half-repair was kept (an attempted text-merge mangled character order and was reverted).
Additionally, tesseract itself misrecognized two words (`Accouthlder`, `IV-2026` in its
hOCR) — present in ALL tools' text layers equally (same OCR); ours keeps the visuals
correct and marks the text unreviewed, per VS-01.

Settings caveat (recorded, per QUALIFICATION §3): OCRmyPDF ran with `--optimize 0`
(lossless image stage); its lossy modes would reduce size with fidelity cost. IA MRC
used default JP2 rates. No universal superiority over MRC is claimed; the operator's
expectation (when reconstruction helps) is what this table establishes on this material.

## 5. Consolidated gate list

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Pipeline end-to-end (synthetic, 8 pages) | PASS | checks.py; probe_results.json |
| 2 | Independent reproduction (36 tests, 28/28 artifacts byte-equal) | PASS | REPRODUCTION.md |
| 3 | E0–E7 font-graph proofs | PASS (8/8) | probe_results.json + QDF re-parse (prior review) |
| 4 | Six negative schema fixtures, dual layer | PASS | validate_fixtures.py + Rust tests |
| 5 | B0 raster baseline (transport/neutral/qpdf) | PASS | measurements.json |
| 6 | External MRC baselines executed on identical sources | PASS | §4 table |
| 7 | Repeated-glyph coverage (no raster-fallback success claim) | PASS | §4 repeated-text table |
| 8 | Real-tesseract UC-01 import path | PASS | §4 + hocr2json |
| 9 | dev-initial-1 visual gate, all pages | **FAIL (honest)** | probe_results.json (pdfium AA edge; p01 MAE 3% over; p04 fi; p06 topology) |
| 10 | `m0-qual-1` policy amendment | **BLOCKED (review pending)** | §2 draft |
| 11 | Benign corpus qualification | **BLOCKED (not mounted)** | §3 |
| 12 | Touching-character character loss on small kerned text | **FAIL (known defect, M1-scoped)** | §4 ⚠ (5/118 chars; B0 carries full text) |
| 13 | MRC/OCRmyPDF full-quality matrix (lossy modes, JP2 rates) | **BLOCKED (M1/M3 scope; settings recorded)** | §4 caveat |

## 6. Disposition

PROVISIONAL baseline stands. M0-Q closes points 1, 4, 6, 7, 8 as PASS; points 9–13 are
FAIL/BLOCKED with evidence and scoped fixes. Per the operator table this does not
authorize M1: point 12's ownership solver is the first M1 deliverable, and point 11
unblocks on corpus mount.
