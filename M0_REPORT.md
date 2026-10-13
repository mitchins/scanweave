# M0 Report — ScanWeave feasibility and contracts

Date: 2026-10-14 (implementation session started 2026-10-13)
Repository: /data/coding/scanweave (git, branch main)
Authorization: AGENT_BRIEF M0 only; plan approved by deepseek-reviewer (rev 2).

## 1. Revision and state

- Final revision at report time: see `git log --oneline` (HEAD = WP-F commit). Working tree
  contains only the report/ledger updates (dirty-state disclosed here).
- Toolchain: rustc/cargo 1.99.0, pinned via `rust-toolchain.toml`; `Cargo.lock` committed;
  dependencies locked per `UPSTREAMS.lock.toml` (all MIT OR Apache-2.0; transitive audit:
  224 packages, no copyleft).
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

| Page | Content | qpdf | OTS | extraction (poppler+pdfium) | ink IoU poppler/pdfium | edge p95 | topo |
|---|---|---|---|---|---|---|---|
| p01_latin | 8,6,8(identical),a | ✓ | ✓ | ✓/✓ | 1.000/0.983 | 1px | ✓ |
| p02_wronglabel | 8 labelled 6 (VS-01) | ✓ | ✓ | ✓/✓ ("6") | 1.000/0.985 | 1px | ✓ |
| p03_kana | ガ multi-component + dakuten | ✓ | ✓ | ✓/✓ ("ガ") | 1.000/0.961 | 1px | ✓ |
| p04_ligature | fi ligature + U+1D400 | ✓ | ✓ | ✓/✓ | 0.974/0.976 | 1px | ✓ |
| p05_colour | 8 on coloured paper | ✓ | ✓ | ✓/✓ | 1.000/0.988 | 1px | ✓ |
| p06_degraded | blurred noisy 8 + speckle | ✓ | ✓ | ✓/✓ | 0.993/0.967 | 1px (max 11-13 outliers) | ✗ (see §7) |
| p07_sharedcid | shared-shape/label proofs | ✓ | ✓ | ✓/✓ | 0.996/1.000 | 1px | ✓ |

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
  visible render IoU 1.000/0.985 vs source (shape preserved), extraction yields `6`,
  provenance recorded `ocr` (unreviewed). PASS
- **E4 (multi-codepoint + supplementary):** ToUnicode `fi` → `0066 0069`; `𝐀` → UTF-16BE
  surrogate pair `D835 DC00`; both extract correctly in both engines. PASS
- **E5 (kana, no normalization):** `ガ` traced as multi-component unit (base + two
  dakuten marks), extracts `ガ` in both engines. PASS
- **E6 (span cardinality + §6.2 owners):** one span covers two visual units (`18`);
  owner recorded `visible_tounicode` for text, `unmapped` for artwork. PASS
- **E7 (determinism):** repeat build → byte-equal font and PDF. PASS
- **E0 (four-part key property):** same glyph + same string → single CID;
  same glyph + different string → additional CID (never a second GID). PASS
  (`writing_mode`/`required_metrics` are carried as explicit fields, fixed for M0; the
  executable mutation property test across all four components is an M1 item.)

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
- **No size advantage is claimed.** These are utility-internal ratios on synthetic pages.
  p06 demonstrates the spec-predicted no-gain case (noise → glyph complexity → font
  overhead beats raster).
- External baselines: Internet Archive PDF Tools / OCRmyPDF / tesseract — BLOCKED
  (no root; recorded in measurements.json with reasons). MRC comparison remains a
  corpus+tool-dependent item.

## 7. Findings, deviations and unresolved items (honest list)

1. **dev-initial-1 edge metric implementation gap:** the policy specifies symmetric edge
   p95 ≤ 0.5 px; the harness implements an integer-pixel distance transform whose floor
   is 1.0 px for any non-identical raster. Measured p95 = 1 px everywhere (floor). A
   sub-pixel (anti-aliased edge distance) metric implementation is required before the
   0.5 px threshold is meaningful. CALIBRATION ITEM for review — not silently relaxed.
2. **Single-glyph 1px placement deviation:** p04 `fi` renders exactly 1 source pixel
   high in BOTH engines (identical ink count, pure translation, deterministic). Root
   cause narrowed to rasterizer fill-boundary behaviour at the construction-box edge;
   per-glyph, quantified; regression-fenced via probe_results.json.
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
