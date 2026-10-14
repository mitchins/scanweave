# M0-Q Gate Report — qualification closure

Date: 2026-10-14. Frozen baseline: commit `3172a32` (tag `m0-provisional-baseline`);
Q-phase work landed in commits after `9479414` (itemized in §2 and LEDGER.md).
Charter: operator message of 2026-10-14 (5 points). No architecture or interface
changes; THREE defect repairs are itemized in §2 (ink colour, ownership assignment,
hOCR 5.5 reader) — each is a concrete qualification-failure repair under the charter.

## 1. Reproduction (charter point 1) — PASS (re-run on the FINAL tree)

- Fresh clone → from-source build → full suite: **38 cargo tests pass** (incl. the E0
  four-part-key mutation property test), schema fixture layer green (3 positive / 6
  negative), checks.py 8 pages + 8/8 E-proofs, measure.py all B0 checks true.
- **32/32 acceptance artifacts byte-identical** between independent checkouts on the
  FINAL tree (out.pdf / out.ttf / b0_raster.pdf / b0_notext.pdf × 8 gate pages; full
  SHA-256 digests committed in `qualification/repro_hashcheck.json`; narrative in
  `qualification/REPRODUCTION.md`). An earlier truncated-digest spot-check existed only
  outside the tree (never committed); the committed record is the final-tree full-digest
  file produced after the §2 repairs.
- Commands, versions, exit codes recorded in REPRODUCTION.md.

## 2. Visual-failure characterization (charter point 2) — CHARACTERIZED; one defect REPAIRED; amendment DRAFTED (review pending)

**Defect repairs itemized (charter-sanctioned; disclosed per review finding B5):**
1. **Ink colour** (`mask.rs`/`pdf.rs`): reconstruction painted pure black over gray-30
   source ink — caught by the whole-page MAE gate; now repaints sampled source ink
   colour. Post-repair p01 poppler passes all criteria.
2. **Ownership assignment** (`units.rs`): greedy first-claim → tightest-containing-box
   (real OCR boxes overlap). This did NOT fix the touching-character loss (see §4 ⚠)
   and is disclosed as an algorithm-level repair in a freeze phase, taken because the
   prior assignment was measurably unfair on real OCR; the reproduction set was RE-RUN
   on the final tree (§1 note).
3. **hOCR 5.5 reader** (`hocr.rs`): char text directly inside cinfo spans (no `<u>`
   wrapper), single `x_conf`, word text = char concat when the word span has no direct
   text. Verified against real tesseract 5.5.0 output.

Evidence (`qualification/characterization.json`):

1. **600 dpi convergence: IoU 1.0 in BOTH engines** (p02 rendered at 600 dpi, downsampled
   to the 300 dpi grid vs source). The outlines and placement are geometrically correct;
   the 300 dpi binary-mask differences are rasterization detail.
2. **PDFium vs Poppler signed displacement** — per-page numbers from the committed
   `characterization.json` (NOT an aggregate): p01: mean |d| 0.257 px, 74.3% < 0.5 px,
   max 1.0 px, mean_dx −0.186; p04: mean |d| 0.475 px, 52.5% < 0.5 px, max 1.414 px
   (the `fi` page); p05: mean |d| 0.133 px, 86.7% < 0.5 px, max 1.0 px. Poppler-vs-
   source integer boundary displacement is 0.0 where the gate passes. Conclusion: PDFium's ~1.1 px p95 is AA-threshold wobble
   on shallow anti-aliased ramps (page-dependent), NOT a geometry or placement defect;
   p04's larger values track the disclosed 1 px `fi` placement deviation. No repair
   indicated for the wobble itself; no thresholds changed.
3. **p01 MAE 0.0206 — REAL DEFECT FOUND AND REPAIRED.** The decomposition showed the
   far-from-edge band contributing 60% of the absolute difference: the FIXTURE draws ink
   at gray 30 while the reconstruction painted PURE BLACK — a ~0.078–0.118 solid-ink
   colour change, i.e. a genuine visible-colour fidelity violation that the whole-page
   MAE gate correctly caught. REPAIR (charter-sanctioned): the probe now samples the
   source ink colour (median of foreground samples) and repaints glyphs in that colour
   (`mask.rs` `Segmentation.ink`, consumed by `pdf.rs`). Post-repair p01 poppler:
   IoU 1.000, edge p95 0.29 px, **MAE 0.0038** (pdfium 0.0052) — the page PASSES all
   dev-initial-1 criteria in Poppler. Lesson recorded: the gate was right; the defect
   was ours.
4. **p04 `fi` 1px**: sub-pixel metric confirms p95 1.01/1.07, max 1.32/1.07 — single-glyph,
   both engines, deterministic; unchanged from the M0 report disclosure.
5. **Caveat disclosed:** the planned rasterizer-independent outline ground-truth check
   (render the embedded TTF via PIL/cmap) produced no data — the probe's minimal nominal
   cmap maps OCR labels, and PIL resolved the test char to .notdef. Nominal-cmap
   completeness is deferred to M1; geometry ground truth is instead established by the
   600 dpi convergence (item 1).

**Proposed versioned policy amendment `m0-qual-1` (DRAFT — requires independent review
before adoption; current gates remain as-is until then; NARROWED after the ink-colour
repair removed the MAE driver):**
(a) geometric fidelity is judged by ink-mask IoU + sub-pixel symmetric edge distance
against the source ink;
(b) whole-page raw MAE stays as a gate (it caught a real defect) with the ink-weighted /
background-weighted split reported alongside (QUALIFICATION §4.2);
(c) the remaining pdfium edge p95 ~1.1 px is proposed to be treated as engine-AA
variance with an engine-paired criterion ONLY IF the M1 calibration data confirms the
outlines are sub-pixel accurate under pdfium at higher rendering resolutions. Nothing
is relaxed in this report.

## 3. Benign pilot corpus (charter point 3) — BLOCKED (environment)

- No corpus is mounted on this machine (checked 2026-10-14; filesystem scan recorded in
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

Committed numbers from `measurements.json` (`pages.p09_realtext`, harness-executed;
regenerated on the final revision):

| Tool (p09 single page) | bytes | ink IoU | transport |
|---|---|---|---|
| source PNG | 37,740 | — | — |
| IA MRC (recode_pdf, JP2 `-r 500/750`) | 45,020 | 0.8452 | 118 chars |
| OCRmyPDF 17.13 (`--force-ocr --output-type pdf --optimize 0`) | 40,122 | 0.7077 | 118 chars |
| **ours B2 (reconstruction)** | **25,005** | **0.8307** | **118 chars (post-repair)** |
| ours B0 (searchable raster) | 51,236 | (render-neutrality verified) | 118 chars (post-repair) |

(Historical: earlier §4 revisions carried 24,058/40,121/113-char figures from
before the item-2 repair and 24,110/40,119/50,341 figures from before the
ActualText repair; those are superseded by the values above, which match the
committed `measurements.json::pages.p09_realtext`. OCRmyPDF's output bytes vary
by a few bytes between runs (embedded timestamps) while ours are byte-
deterministic across independent checkouts; the table shows the committed
value.)

**Repeated-text 4-page document (p10)** — committed harness numbers
(`measurements.json` `pages.p10_multipage`, regenerated on the final revision):
source 164,141 B; ours B2 (per-page sum) **104,698 B** =
**0.6186× OCRmyPDF (169,241 B)** and
**0.5533× IA MRC (189,213 B)**; B0 220,800 B.
OCRmyPDF's bytes vary a few bytes per run (embedded timestamps); ours are
byte-deterministic across checkouts. Repeated-glyph sharing works on real OCR
(e.g. `o` reused across contexts: gid2 cids [1,33]). Caveat as before: external
tools ran on a true 4-page PDF; ours is a per-page sum (multi-page assembly is
M1) — recorded as an approximation direction, and the same touching-character
import loss (§4 ⚠) applies to our text layer on these 36-px pages.

**⚠ Known defect found and quantified (charter point 4's anti-fallback concern applies
to fidelity, and this is a fidelity-side loss):** on 36-px kerned text, touching
characters rasterize as ONE component; the M0 probe's disjoint ownership assigns the
component to one symbol and the paired symbol is dropped — **5 of 118 characters
(4.2%) lost in the normalized OCR import**, affecting OUR B0 and B2 text layers
EQUALLY (both extract 113 chars; the loss is in import segmentation, upstream of the
raster/reconstruction split — it is NOT a reconstruction-specific loss, and it is NOT
a tesseract misrecognition: tesseract's hOCR for this page is correct and the earlier
report examples that blamed tesseract were misattributed; corrected herewith).
B0's render still shows 100% of the ink (the pixels are all present in the raster);
the loss is text-layer-only. Component splitting / multi-symbol shared units is scoped
as the FIRST M1 ownership-solver item (SPEC §5.2/§5.3); an attempted text-merge repair
was REVERTED because it reordered characters (a §4.3 content-critical error class) —
revert verified by the reviewer's request and recorded here.

Settings caveat (recorded, per QUALIFICATION §3): OCRmyPDF ran with `--optimize 0`
(lossless image stage); its lossy modes would reduce size with fidelity cost. IA MRC
used default JP2 rates. No universal superiority over MRC is claimed; the operator's
expectation (when reconstruction helps) is what this table establishes on this material.

## 5. Consolidated gate list

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Pipeline end-to-end (synthetic, 8 gate pages) | PASS (qpdf/OTS/extraction/visual per page where applicable) | checks.py; probe_results.json |
| 1b | p08 pdfium span-ordering transport | **FAIL (preserved per operator directive)** — scattered-symbol layout: cardinality ✓, duplicates ✓, span ORDER ✗ | probe_results.json transport_pdfium; M0_Q_REPORT §2 |
| 2 | Independent reproduction (38 tests, 32/32 artifacts byte-equal, 8 pages) | PASS | REPRODUCTION.md; repro_hashcheck.json |
| 3 | E0–E7 font-graph proofs | PASS (8/8) | probe_results.json + QDF re-parse (prior review) |
| 4 | Six negative schema fixtures, dual layer | PASS | validate_fixtures.py + Rust tests |
| 5 | B0 raster baseline (transport/neutral/qpdf) | PASS | measurements.json |
| 6 | External MRC baselines executed on identical sources | PASS | §4 table |
| 7 | Repeated-glyph coverage (no raster-fallback success claim) | PASS | §4 repeated-text table |
| 8 | Real-tesseract UC-01 import path | PASS | §4 + hocr2json |
| 9 | dev-initial-1 visual gate, all pages | **FAIL (honest)** | probe_results.json (pdfium AA edge ~1.1px on all pages; p04 `fi` IoU/edge; p06 topology+outliers; MAE now passes on every page post ink-colour repair) |
| 10 | `m0-qual-1` policy amendment | **BLOCKED (review pending)** | §2 draft |
| 11 | Benign corpus qualification | **BLOCKED (not mounted)** | §3 |
| 12 | Touching-character character loss on small kerned text | **PASS (repaired in the hardening pass; regression tests red→green; 118/118 in both engines)** | probes/m0-font-pdf/tests/transport_regression.rs; measurements p09/p10 transport |
| 13 | MRC/OCRmyPDF full-quality matrix (lossy modes, JP2 rates) | **BLOCKED (M1/M3 scope; settings recorded)** | §4 caveat |

## 6. Disposition

PROVISIONAL baseline stands. M0-Q closes points 1, 4, 6, 7, 8 as PASS; points 9–13 are
FAIL/BLOCKED with evidence and scoped fixes. Per the operator table this does not
authorize M1: point 12's ownership solver is the first M1 deliverable, and point 11
unblocks on corpus mount.


---

## Appendix — M0-Q hardening pass (2026-10-14, reviewer-authorized)

Charter: "Targeted qualification-harness corrections and repairs of demonstrated
defects only. M1 remains unauthorized. Preserve the frozen architecture,
encoding contracts, existing thresholds and source evidence."

**Item 1 — sub-pixel edge interpolation: CORRECTED.** The interpolator had the
crossing mirrored to the opposite side of the inside→outside segment (analytic
tests: mid-ramp edges recovered at ~1.0 px error). Fixed to
`t* = (i50 − vi)/(vq − vi)` along the inside→outside direction, with a rigorous
sampling threshold: `i50 = (paper_ref + ink_ref)/2` per image (50%-coverage
contour; AA-invariant), degenerate ramps skipped. New analytical tests
(`qualification/test_subpixel_metric.py`): known sub-pixel edge positions
(phases 0/0.25/0.5/0.75), horizontal/vertical/inverted polarity, low-contrast
colour pairs, a known 0.3 px two-render offset, and a mirrored-implementation
regression guard — all pass within the derived linear-interpolation bias bound
((3/2−√2) = (√2−1)²/2 ≈ 0.086 px; tests assert 0.09 px). Regenerated visual results:
Poppler p95 now measures 0.50–0.52 px (the old mirrored metric read low at
0.25–0.29); pdfium 0.51–1.00 px. MAE: Poppler passes every page (p01 0.0038),
pdfium also passes MAE; the remaining gate failures are (a) Poppler edge p95
0.51–0.52 against the 0.5 policy on 4 pages (marginal, honest measurement — no
threshold relaxation made; the `m0-qual-1` draft is updated: the measured
0.51 is within the 0.086 px estimator bias of a ≤0.42 px true geometric
deviation, so an estimator-bias-aware criterion is the proposed amendment,
subject to independent approval) and (b) p04 `fi` and p06 (unchanged analyses).

**Item 2 — semantic transport loss: REPAIRED.** Regression tests first
(`probes/m0-font-pdf/tests/transport_regression.rs`): red at 113/118 carried
characters; green after repair. Root causes fixed: (i) touching characters →
one connected component → the paired symbol's slot left empty; now absorbed
into the owning unit as ONE visual unit carrying MULTIPLE semantic characters
(SPEC §3/§5.3), ordered by the OCR's own slot index (reading sequence) —
polygon x0 ordering was ambiguous when hOCR boxes overlap ('w'/'i' both at
x0=258, which corrupted the first repair attempt to "iwthin"); (ii) index bug
in the absorption scan (enumerated spans, indexed slots). **End-to-end: 118/118
characters extract in exact order through BOTH Poppler and PDFium on the
real-tesseract fixture (c00_page_01 through the corpus adapter as well).**
Also fixed en route: normalized-JSON export emitted `null` for schema-optional
fields (`source_geometry`, `baseline`, `parent_span_id`, dpi) that the schema
requires be ABSENT — a real interchange round-trip bug caught by the hardened
adapter's validation; committed fixtures re-generated schema-clean.

**Item 3 — extraction verification hardened.** Transport now verified against
the ORIGINAL OCR INPUT (fixture span texts in declared reading order), not a
hand-typed list: codepoint cardinality, duplicate detection and per-span
coverage through both engines, per page, recorded in
`probe_results.json.<page>.transport_{poppler,pdfium}`. p08 pdfium
span-ordering remains FAIL (coverage=False, cardinality=True) exactly as
directed — explicitly listed in §5, not waived.

**Item 4 — corpus qualification executable.** `corpus_adapter.py` upgraded:
SWRASTER1 pixel-hash binding per page (mismatch ⇒ fail-closed error), OCR
validation (hOCR via the real Rust import path; pre-normalized vs schema +
structural rules), document-level split isolation (deterministic SHA-256
bucket → train/development/calibration 60/20/20), sealed holdouts
(`*_holdout` strata / `holdout_` documents hashed and refused unless
`--include-holdout`). Runner `--pages` fixed to argparse (+ `--fixtures-dir`
over-ride). `qualification/test_corpus_adapter.py` exercises the WHOLE
adapter→runner interface on a miniature synthetic corpus (6 documents incl.
one sealed holdout, a deliberately broken binding, repair, per-page checks
`--pages` run): all green. The real benign corpus remains NOT MOUNTED; the
real-corpus gate stays BLOCKED.

**Item 5 — evidence/provenance reconciled.** Dates corrected (2024→2026).
External-comparison commands fail closed (`measure.py` `run_external`: prior
outputs deleted, tool failure raises a precise reason instead of silently
reusing stale outputs or reporting smaller totals). Measurements regenerated on
the final revision: p09 B2=25,005 B / IA MRC 45,020 B /
OCRmyPDF 40,122 B; p10 totals B2=104,698 B =
0.6186× OCRmyPDF, 0.5533× IA MRC. The
"non-quality-equivalent" mark for documents with missing OCR characters is
SUPERSEDED by the item-2 repair: p09/p10 now transport 118/118(and p10's
per-page sets) exactly in both engines, so the compression results above are
quality-equivalent on the transport dimension; the record of the earlier
defect is retained here and in the ledger.

**Gate list impact:** rows 1–8 unchanged PASS; row 12 (touching-character
loss) moves FAIL → PASS-BY-REPAIR with the regression tests as evidence; row
9 (dev-initial-1 visual gate) remains FAIL on the honest corrected-metric
margins (Poppler edge p95 ≈0.51 on 4 pages; pdfium ≈1.0 on all; p04/p06 as
before); the `m0-qual-1` amendment is a draft pending independent approval;
row 11 (corpus) remains BLOCKED. Disposition: PROVISIONAL unchanged. M1 not
authorized.


---

## Appendix 2 — M0-Q final correctness correction (2026-10-14)

Charter: repair demonstrated semantic-search and corpus-sealing defects against the
DeepSeek-accepted baseline `086bf57`. Red-before-green evidence for both defects is
recorded below; no architecture, threshold or M1 scope changes.

### A. PDF text search — DEFECT REPRODUCED, REPAIRED, GATED

**Red (recorded before repair):** the committed p09 artifact transported all 118
characters but extracted as `'Tota l a m o u nt d u e : 1 , 2 3 4 . 5 6 EU R...'` —
per-glyph `Tj` placements made both extractors insert intra-word whitespace;
PDFium search for `Total`, `1,234.56`, `INV-2026-0042` all MISSED. (The whitespace-
stripped transport check had masked this; that masking is itself the lesson that
made word-boundary integrity a PRIMARY criterion.)

**Repair (SPEC §6.2, no new layers):** each OCR span's glyphs are emitted as one
marked-content run `BDC /Span << /ActualText (span text)>> … EMC` whose ActualText
is the span's exact OCR text — the span's single semantic owner. The per-glyph
ToUnicode entries remain as the per-glyph fallback and keep the VS-01
wrong-label semantics; no duplicate invisible layer was introduced. Spans whose
text contains non-BMP scalars are excluded from ActualText wrapping (PDFium drops
astral scalars inside ActualText, measured: `fi` extracted, `𝐀` dropped) — those
keep the ToUnicode owner, which transports astral scalars exactly. CID/GID/Unicode
separation is unchanged (E-proofs 8/8 still pass).

**Green (after repair):** raw PDFium text reads `Total amount due: 1,234.56 EUR /
Invoice date: 13 October 2026 / Account holder: J. Garcia / Reference: INV-2026-0042
/ Please pay within 30 days.` — all three required queries FOUND in PDFium and
Poppler, in B2 AND the B0 baseline. Character transport remains exact and
non-duplicated (118/118). `qualification/test_text_search.py` extends the gate:
decimals, negative amounts (`-42`), invoice references, ligatures (`fi`), kana
(`ガ` intact), supplementary-plane (`𝐀`), the `1,234.56` token across p08/p10, and a
defect-signature guard. B2 size grew to 25,005 B on p09 (the BDC wrappers;
honest cost of a correct text layer; B2 still ~0.62× the OCRmyPDF 40,122 B baseline).

**Extracted verification (checks.py):** `word_boundary_ok` (every span text appears
contiguously in the raw extraction) and `no_intra_word_spaces` (no multi-char span
split by spaces) are now PRIMARY gates; whitespace-stripped cardinality remains a
supplementary signal. p08's pdfium span-ordering FAIL is preserved with a precise
cause (PDFium's span-merge artifact `\x02` plus layout order; cardinality=False,
coverage=False; poppler now passes p08's transport).

### B. Holdout sealing — DEFECTS REPRODUCED, REPAIRED, GATED

**Red (recorded):** (B1) default ingestion wrote the holdout's normalized OCR into
`bundle/normalized/receipts_holdout__holdout_zeta/` before excluding the document;
(B2) the seal hash changed with `--out` because it hashed an output-dependent path
(8ba9f7cb… vs 60b21ff3… on two different output directories).

**Repair:** holdout documents are now identified at document level BEFORE any page
processing and sealed from canonical relative identity + SHA-256 of the source
raster and OCR file bytes (`scanweave-holdout-seal/1`) — no copying, parsing,
normalization or rendering of holdout content occurs during ordinary development
ingestion. Holdout pages are skipped entirely unless `--include-holdout`.

**Green (after repair):** (B1) default ingestion produces no `normalized/` entry for
the holdout and a recursive byte-leak scan of the whole output tree finds none of
the holdout's bytes; (B2) the seal is identical across different `--out` paths
(e9eec5488f47…), changes when any sealed source byte changes (7b5d2e68c5ca… on a
mutated copy of the corpus, the original never touched), and `--include-holdout`
materialization preserves the same development seal. Additionally (B7) an explicit
`--out` can no longer target the committed gate artifact from a subset/overridden
run (fail-closed), guarding the evidence destination even against deliberate paths.

### C. Evidence

- 38 cargo tests, all analytical/search/corpus suites green.
- Reproduction on a fresh checkout at the final revision: 38 tests, 8/8 E-proofs,
  32/32 artifacts byte-identical against the committed `repro_hashcheck.json`
  (regenerated on this revision), pixel hash independently re-derived.
- Baselines regenerated (fail-closed externals): p09 B2 25,005 B / IA MRC 45,020 B /
  OCRmyPDF ~40,12 kB (varies a few bytes per run; committed value in measurements.json);
  p10 B2 totals with repeated-text ratios in measurements.json.
- Visual gates unchanged (honest margins); p08 pdfium transport FAIL preserved;
  p08's DEFECT-A fix evidence attached.
- PROVISIONAL stands; M1 NOT authorized. m0-qual-1 remains a draft pending
  independent approval; the real benign corpus remains sealed and unmounted.
