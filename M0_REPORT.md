# M0 Report — ScanWeave feasibility and contracts

Date: 2026-10-14 (implementation session started 2026-10-13)
Repository: /data/coding/scanweave (git, branch main)
Authorization: AGENT_BRIEF M0 only; plan approved by deepseek-reviewer (rev 2).

## 1. Revision and state

- Final revision at report time: see `git log --oneline` (post-repair commit following the
  final-gate review). Dirty-state at report time: report/ledger updates only (disclosed).
- Toolchain: rustc/cargo 1.99.0, pinned via `rust-toolchain.toml`; `Cargo.lock` committed;
  dependencies locked per `UPSTREAMS.lock.toml` (16 runtime crate entries, all MIT OR
  Apache-2.0; transitive audit: 224 packages, no copyleft).
- Environment: Ubuntu 24.04, 24 CPUs, 78 GiB RAM. No root access (recorded; shaped the
  validator provisioning below).

## 2. Work packages delivered

| WP | Deliverable | State |
|---|---|---|
| A | Repo init, toolchain pin, validator inventory (`TOOLCHAIN.md`) | DONE |
| B | `UPSTREAMS.lock.toml` (12 runtime crates + sha256s + licences + scopes; 7 qualification tools) | DONE |
| C | Normalized types, pixel-hash v1, hOCR reader, semantic validator; tests-first IN/NF suites | DONE — 35 Rust tests green (clippy clean) + Python Draft 2020-12 layer green |
| D | Vertical probe: mask → 2× supersampled VTracer trace → write-fonts TrueType → pdf-writer Type0/CIDFontType2 → render+extract | DONE — 7 synthetic pages end-to-end |
| E | GID/CID/Unicode separation proofs E0–E7, all proven from the font/PDF graph | DONE — 8/8 PASS |
| F | B0 searchable raster control + B2 reconstruction measurements; external baselines attempted/recorded | DONE (MRC/OCRmyPDF BLOCKED, reasons recorded) |
| G | This report, ledger, hypothesis preregistration, M1/M2 plan | DONE |

## 3. Commands and evidence (raw)

- `cargo test` — 35 tests pass (pixel_hash 5, ocr_page_validation 21, bundle_pairing 3,
  hocr 6). Tests were written first and observed failing (unresolved-import errors) before
  implementation.
- `python3 qualification/validate_fixtures.py` — 3 positive pass, 6 negatives rejected
  (JSON-Schema Draft 2020-12 layer, jsonschema 4.10.3).
- `qualification/.venv/bin/python qualification/checks.py` — per-page independent
  verification; results in `qualification/probe_results.json` (raw artifacts under
  `work/m0-checks/<page>/`: out.pdf, out.ttf, b0_raster.pdf, b0_notext.pdf, renders).
- `qualification/.venv/bin/python qualification/measure.py` — `qualification/measurements.json`.
- Validator versions: qpdf 12.4.2 (local build), ots-sanitize 9.3.0, Poppler 24.02.0,
  fontTools 4.46 (venv), pypdfium2 (PDFium, engine #2), tesseract UNAVAILABLE.

## 4. Pipeline evidence (WP-D)

Synthetic scans (PIL, system fonts, never committed) at 300 dpi-equivalent with normalized
OCR JSON (schema-valid, source_generated provenance, SWRASTER1 pixel-hash binding — the
binding check caught a real pairing mismatch during development).

Per-page independent verification (both engines where applicable):

Sub-pixel symmetric edge metric (review repair B3): boundary localized by linear
interpolation of the 50%-coverage crossing on the anti-aliased grayscale; distances in
continuous source pixels. Gate = dev-initial-1: IoU ≥ 0.98, edge p95 ≤ 0.5 px,
max ≤ 1.0 px, MAE ≤ 0.02, topology stable at thresholds 55/60/65.

| Page | qpdf | OTS | extraction (pop+pdf) | IoU pop/pdf | edge p95 pop/pdf | MAE pop/pdf | topo | gate |
|---|---|---|---|---|---|---|---|---|
| p01_latin | ✓ | ✓ | ✓/✓ | 1.000/0.983 | **0.29**/1.07 | 0.0206/0.0219 | ✓ | poppler: MAE fail (0.0206>0.02); pdfium: edge+MAE fail |
| p02_wronglabel | ✓ | ✓ | ✓/✓ | 1.000/0.985 | **0.27**/1.10 | 0.0063/0.0064 | ✓ | poppler PASS; pdfium edge fail |
| p03_kana | ✓ | ✓ | ✓/✓ | 1.000/0.961 | **0.28**/1.16 | 0.0049/0.0052 | ✓ | poppler PASS; pdfium edge fail |
| p04_ligature | ✓ | ✓ | ✓/✓ | 0.974/0.976 | 1.01/1.07 | 0.0100/0.0092 | ✓ | both: IoU+edge fail (see §7.2) |
| p05_colour | ✓ | ✓ | ✓/✓ | 1.000/0.988 | **0.25**/1.12 | 0.0060/0.0060 | ✓ | poppler PASS; pdfium edge fail |
| p06_degraded | ✓ | ✓ | ✓/✓ | 0.993/0.967 | 4.89/4.67 | 0.0161/0.0157 | ✗ | FAIL both (speckle outliers; §7.3) |
| p07_sharedcid | ✓ | ✓ | ✓/✓ | 0.996/1.000 | 0.37/0.29 | 0.0178/0.0172 | ✓ | poppler max 1.35 fail; pdfium PASS |

Counter-hole evidence (VS-06): p05 counters sampled — mean counter colour ≈ paper colour
(d_paper < d_white; probe_results.json `counter_colour`). Winding independently dumped via
fontTools (largest-magnitude contour negative/CW; recorded per glyph).

## 5. Font architecture proofs (WP-E) — reviewer focus area

All proven from the emitted font/PDF graph (CIDToGIDMap stream + ToUnicode CMap parsed
independently via qpdf --qdf), NOT inferred from pixels:

- **E1 (same outline, different character codes):** p07 — the two identical `8` shapes
  (labels `8` and `6`) produce ONE GID referenced by TWO CIDs; ToUnicode maps
  CID1→`8`, CID2→`6`. Glyph reuse is proven (CIDToGIDMap N→1), not assumed. PASS
- **E2 (different outlines, same Unicode):** p07 — regular and smaller `8` are distinct
  GIDs whose CIDs both map to `8`. PASS
- **E3 (VS-01, OCR mistake ≠ visual mistake):** p02 — observed `8` with OCR `6`:
  visible render IoU 1.000/0.985 vs source with sub-pixel edge p95 0.27/1.10 px (shape
  preserved; measured, see §4 gate split), extraction yields `6`, provenance recorded
  `ocr` (unreviewed). PASS
- **E4 (multi-codepoint + supplementary):** ToUnicode `fi` → `0066 0069`; `𝐀` → UTF-16BE
  surrogate pair `D835 DC00`; both extract correctly in both engines. PASS
- **E5 (kana, no normalization):** `ガ` traced as multi-component unit (base + two
  dakuten marks), extracts `ガ` in both engines. PASS
- **E6 (span cardinality + §6.2 owners):** one span covers two visual units (`18`);
  owner recorded `visible_tounicode` for text, `unmapped` for artwork. PASS
- **E7 (determinism):** repeat build → byte-equal font and PDF. PASS
- **E0 (four-part key property, executable):** `probes/m0-font-pdf/src/encoding.rs`
  implements the full SPEC §6.1 key `(visual_glyph_id, semantic_string, writing_mode,
  required_metrics)` — `WritingMode` (Horizontal/Vertical) and `MetricsKey
  {advance, units_per_em}` are real key components — with a Rust unit test that mutates
  each of the four components in turn and asserts CID separation, plus dedup for
  identical keys and 1-based dense allocation. `cargo test -p m0-font-pdf
  e0_four_part_key_property` passes and is executed by the harness. M0 fixes
  Horizontal/2048; vertical + metric variants are representable without schema change.
  PASS

## 6. Baselines and measurements (WP-F)

| Page | source PNG | B0 searchable raster | B2 reconstructed | baseline_ratio_B2 |
|---|---|---|---|---|
| p01_latin | 13,204 | 19,544 | 9,787 | **0.50** |
| p02_wronglabel | 6,528 | 10,408 | 5,822 | 0.56 |
| p03_kana | 6,669 | 11,318 | 6,218 | 0.55 |
| p04_ligature | 2,002 | 5,511 | 3,355 | 0.61 |
| p05_colour | 6,592 | 10,642 | 5,847 | 0.55 |
| p06_degraded | 19,253 | 33,391 | **44,343** | **1.33 — B2 LOSES** |
| p07_sharedcid | 11,660 | 16,962 | 8,176 | **0.48** |

- B0 verified: qpdf ✓, transport ✓, render-neutral ✓ (B0 vs its own text-less twin:
  byte-identical renders — invisible text paints nothing).
- Per-stream byte breakdowns are emitted per page to `breakdown.json` (writer
  instrumentation): font_file2, cid_to_gid_map, to_unicode_cmap, content_stream,
  page_image_flate (B0), xref/dict overhead, total; mirrored into
  `qualification/measurements.json` (review repair B4).
- **No size advantage is claimed.** These are utility-internal ratios on synthetic pages.
  p06 demonstrates the spec-predicted no-gain case (noise → glyph complexity → font
  overhead beats raster).
- External baselines: Internet Archive PDF Tools / OCRmyPDF / tesseract — BLOCKED
  (no root; recorded in measurements.json with reasons). MRC comparison remains a
  corpus+tool-dependent item.

## 7. Findings, deviations and unresolved items (honest list)

1. **Sub-pixel edge metric implemented (review repair B3); measured outcomes are mixed
   and honest:** Poppler renders meet the edge criterion outright on p01/p02/p03/p05
   (p95 0.25–0.29 px, max ≤ 0.43 px) — the traced fonts are genuinely sub-pixel accurate
   there. PDFium shows p95 ≈ 1.07–1.16 px on the same files (heavier anti-aliasing at
   the 60-luminance threshold). p01 MAE is 0.0206 vs the 0.02 policy (3% over) in BOTH
   engines. The visual gate therefore genuinely FAILS on pdfium-edge (all pages) and
   poppler-MAE (p01) by small margins — recorded as the calibration baseline for the
   M0/M1 policy revision (QUALIFICATION §4.2), not waived. p06 fails topology + edge
   outliers (§7.3); p04 fails IoU/edge (§7.2).
2. **Single-glyph 1px placement deviation:** p04 `fi` renders ~1 source pixel high in
   BOTH engines (identical ink count, pure translation, deterministic; survives the
   sub-pixel metric: p95 1.01/1.07, max 1.32/1.07). Root cause narrowed to rasterizer
   fill-boundary behaviour at the construction-box edge; per-glyph, quantified;
   regression-fenced via probe_results.json.
3. **p06 topology gate:** synthetic speckle noise (900 dots) — component-count
   topology is AA-threshold-sensitive on 1–2 px marks; ink preserved within 0.7%
   (IoU 0.993). Rendered as vector artwork for unowned ink (VS-05 preserve path);
   gate outcome recorded FAIL and analyzed rather than suppressed.
4. **PDFium IoU consistently below Poppler** (0.96–0.99 vs 0.97–1.0): rasterizer AA
   differences at threshold — recorded; engine deltas matter for threshold calibration.
5. **VTracer parameter coupling (SPEC §11.1 risk, materialized):** stock smoothing
   (corner 60°, length 4.0) produced 1.5–2.5 px trace deviations — trace-stage allocation
   (0.5 px) was NOT met by defaults. Resolution: corner_threshold=0, length_threshold=1.0,
   2× supersampled tracing → measured trace error 0.496 px ≤ 0.50 allocation
   (budget_ok=true in all trace logs). Recorded as the m0-probe-1 parameterization
   evidence; spline-mode smoothing remains an adapter risk for M1 (polygon mode measured
   worse — 2–27 px — and rejected).
6. **CID 0 and codespace:** initial PDFs were blank in independent renderers — two real
   bugs found BY the independent-verification discipline: (a) CID 0 must be reserved for
   .notdef (CIDs now start at 1); (b) the ToUnicode codespace range must cover all
   allocated CIDs (was `<0000> <0000>`, rendering every CID out-of-codespace). Both fixed;
   kept as regression evidence.
7. **tesseract unavailable** (no root): convenience-OCR routes untested; recorded.
8. **Six negative schema fixtures:** HANDOFF_CHECKS claimed them; originals were not in
   the packet — reconstructed as NF-01..NF-06 per operator condition 2 and validated at
   BOTH layers (JSON-Schema + typed).
9. **MRC baseline blocked** (see §6) — expected PROVISIONAL contributor.
10. **Corpus:** not mounted; all evaluation is synthetic. Real-document evaluation
    remains blocked (recorded, never substituted).

## 8. Product-value hypothesis (preregistered per QUALIFICATION §7)

Hypothesis: **vector benefit at near-parity** — at least 80% median vector coverage with
no more than 15% median size overhead against the best fidelity-qualified external MRC
comparator in explicit reconstruction mode, plus independent zoom/readability evidence,
on a preregistered clean printed-text subset (synthetic clean-text pages now; corpus
subset when mounted). Rationale: the probe shows reconstruction at 0.48–0.61× of our own
searchable raster on clean text (internal ratios only), while the noise page shows the
fallback case works as designed. This hypothesis is recorded BEFORE any M1 tuning; the
compression-benefit alternative was not chosen because external MRC comparators are
unavailable in this environment and raster-native sizes on real scans remain unmeasured.

## 9. M1/M2 plan (bounded sketch)

- M1: core/io split of probe logic; asset-store trait; candidate render verification
  (per-occurrence + composited); distinct-output + atomic publication; CLI `build` slice;
  corrections of the E0 mutation test to all four key components; sub-pixel edge metric;
  multi-engine budget calibration proposal (review-gated); word-only OCR path planning.
- M2: segmentation/ownership map; protected regions + financial presets; word-only
  input mapping; mixed visible/invisible semantics; receipt/statement/bill fixtures;
  unowned-ink policy generalization (artwork vs fallback).

## 10. Exit decision (proposed, pending final independent review)

**PROVISIONAL** — feasibility of the full scanned-glyph → reconstructed-font →
searchable-PDF pipeline is demonstrated with independent evidence (§4–§5), but:
corpus-dependent qualification is blocked (no corpus), external MRC/OCRmyPDF baselines
are blocked (no root), and the dev-initial-1 numeric policy requires sub-pixel metric
implementation + calibration review (§7.1) before its thresholds can gate. Per the
operator exit table, PROVISIONAL does not authorize M1.
