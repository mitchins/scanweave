# M1-A: Generalized Ownership Solver, Transactional Fallback, Pipeline + CLI

**Commit:** see git log (implemented in `0d5929e`, corrections in the follow-up fix commit).
**Status:** implementation complete; all suites re-run independently with results below.

## 0. Author's honesty note (what changed after review round 1)

An independent review of commit `0d5929e` (deepseek-reviewer) returned BLOCK with
correct findings. Every finding was verified by the author against committed
artifacts and fixed; the diff below is complete:

| Reviewer finding | Status | Evidence in this revision |
|---|---|---|
| D1: p04 astral ActualText regression (`"fi𝐀"→"fi"`) | FIXED | astral guard restored in `page_pdf.rs` (BMP-only ActualText, astral stays on ToUnicode); `p04 pdfium supplementary U+1D400` PASSes; the full gate set now shows **zero check flips vs accepted pipeline `f5e5cb5`** |
| D2: p06 PDFium transport regression (`"8"→""`) | FIXED | root cause was an owner-CID off-by-one in `page_pdf.rs` (convert emits 1-based owner CIDs; the assembler added +1 → CID2 undefined by font/ToUnicode). Fixed; `p06` now extracts `8` in both engines |
| D3: B0 baseline generation removed | FIXED | `convert` re-emits the B0 raster-baseline (`baseline::assemble_raster`); `b0_raster.pdf` restored in probe output; all `test_text_search.py` B0 gates PASS |
| D4: trace evidence fabricated (`contours:[]`, `budget_ok:true`) | FIXED | report carries real `GlyphStat` (contours, points, stage metrics, honest `budget_ok` under m0-probe-1 budget); values reproduce the accepted M0-Q run exactly (p01 '8': 3 contours, 2083 pts, trace_max 0.4963) |
| D5: report claimed "no hard-coded absolute paths" | CORRECTED | the committed tesseract fixture hOCR files do carry absolute `image` paths; §6 wording fixed |
| D6: report byte-determinism unsupported | FIXED | report maps switched to `BTreeMap`; the three deliverables' report JSONs are byte-identical across independent runs (sha1 verified) |
| D7: orphaned duplicate modules | ACKNOWLEDG | `probes/m0-font-pdf/src/{encoding,units,pdf,baseline}.rs` and `scanweave-io/src/{pdf,baseline}.rs` are compiled-out migration shims; kept for provenance during the M1-A refactor, removal is M1-B scope |
| D8: "Double-inked 0" unmeasured | CLARIFIED | multiply-owned **text** ink is computed by the solver and is 0 (see §2); artwork-vs-vector paint overlap is bounded by drawing order (patches first, vectors last — no halo) and by the visual-gate evidence: the visual gates' numbers are **unchanged from the accepted baseline** on every page |
| D9: m1a09 didn't test raster fidelity | FIXED | m1a09 now asserts each fallback region's box contains real source ink (not paper-only) |
| D10: M1A-01 tautological | FIXED | m1a01 now asserts geometric ownership: every supplied symbol box is referenced by an owned slot whose traced ink bbox intersects that box, and the merged touching unit owns ≥2 slots sharing a horizontal range |
| D11: p11 boxes are synthetic | CORRECTED | §2 states p11/p12 use derived synthetic boxes (`.synth.json`); p06/p14/p16 use real tesseract hOCR |
| D12: `.DS_Store` junk | FIXED | untracked macOS junk removed from the tree |
| "M0 visual gates run green" (report claim) | CORRECTED | they do NOT pass and never did at the accepted baseline; the honest numbers are in §4 |

## 1. What was implemented

### 1.1 Generalized ownership solver (`crates/scanweave-io/src/ownership.rs`)
- Many-to-many mapping: one connected component may serve multiple OCR spans;
  one span may own multiple components (moving/rotated spans supported).
- Slots carry `order`, `text`, `symbol_id`, `bbox` (order-stable identity, so
  geometric ownership is auditable per symbol box — see M1A-01).
- `suspect` flag: unit ink extending beyond the union of its symbol boxes by
  more than the contact margin → `ContactNonText` fallback.
- Invariants: no double ownership; every component back-referenced exactly once
  or explicitly unowned (artwork).

### 1.2 Region planning + transactional fallback (`plan.rs`, `convert.rs`)
- Span-ordered regions (reading-stream order preserved).
- ContactNonText regions degrade transactionally: the region's sub-raster is
  embedded losslessly AND the OCR label is redrawn as an invisible per-span
  owner run, so text extraction is complete for fallback spans in both engines
  (engine-hoisting caveat in §5).
- Artwork regions use the same machinery; paper background + patches are
  FlateDecode image XObjects drawn before vector glyphs.

### 1.3 One-page pipeline and PDF assembler (`page_pdf.rs`, `crates/scanweave-cli/src/main.rs`)
- `scanweave build <page.png> --ocr <page.hocr> --dpi 300 --output out.pdf --report out.json`
  (atomic `.tmp`+rename; M1-A: `--mode reconstruct` only).
- Single font resource: one CID per (glyph shape, semantic string); fallback
  spans carry one owner CID each referencing GID1 (invisible runs). No second
  font, no second layer.
- Visible spans: per-glyph runs grouped under per-span `/ActualText` for BMP
  spans only; astral (non-BMP) spans keep per-glyph ToUnicode transport (the
  M0-Q repair — PDFium drops astral scalars inside ActualText).
- Invisible owner runs: plain invisible Tj placed at the span box top (the
  run's own baseline); ToUnicode transport. No `/ActualText` (measured: PDFium
  hoists invisible runs to the end of its extraction order either way).
- Owner-only-encodable fonts: placeholder GID1 keeps `numGlyphs`/`hmtx`/`cmap`/
  `loca`/`bbox`/`OS/2` self-consistent (OTS-clean).

### 1.4 B0 baseline candidate restored
`convert` also emits the raster-baseline page (source pixels + invisible
per-glyph ToUnicode owner layer), which `test_text_search.py` gates against.

## 2. Deliverables (reproduce)

OCR inputs: `tess.hocr` = real tesseract 5.5.0 hOCR for p06/p14/p16; p11/p12
use derived synthetic boxes (`.synth.json`) because tesseract cannot produce
char boxes for deliberately-touching glyphs (the fixture's point).

```
cargo run -p scanweave-cli -- build qualification/fixtures/probe/p16_statement/p16_statement.png \
  --ocr qualification/fixtures/probe/p16_statement/tess.hocr --dpi 300 \
  --output work/m1a-final/clean.pdf --report work/m1a-final/clean.json

cargo run -p scanweave-cli -- build qualification/fixtures/probe/p11_touching/p11_touching.png \
  --ocr qualification/fixtures/probe/p11_touching/tess.hocr --dpi 300 \
  --output work/m1a-final/touching.pdf --report work/m1a-final/touching.json

cargo run -p scanweave-cli -- build qualification/fixtures/probe/p14_noisy/p14_noisy.png \
  --ocr qualification/fixtures/probe/p14_noisy/tess.hocr --dpi 300 \
  --output work/m1a-final/fallback.pdf --report work/m1a-final/fallback.json
```

| Deliverable | PDF size | Text ink px | Vector ink px | Raster ink px | Vector % of eligible | Fallback spans | Unowned | Double-inked (text) |
|-------------|---------:|------------:|--------------:|--------------:|---------------------:|---------------:|--------:|-------------:|
| clean.pdf (p16 statement) | 30210 B | 4945 | **4325** | 620 | **87.5%** | 1 (ContactNonText) | 0 | 0 |
| touching.pdf (p11) | 13037 B | 11681 | **11681** | 0 | **100%** | 0 | 0 | 0 |
| fallback.pdf (p14) | 143143 B | 7574 | 0 | 7574 | 0% (deliberate) | 6 (ContactNonText) | 0 | 0 |

All three builds were run twice independently: PDFs **and** report JSONs are
byte-identical (sha1), and `qpdf --check` passes on all three. Coverage
denominator note: `text_ink_px_total` counts OCR-owned text ink; unrecognized
ink is separately reported as `other_ink_px` (3486 / 3657 / 2096), so the vector
percentages exclude nothing that was claimed.

Determinism report: the report JSON is deterministic by construction
(`BTreeMap` maps, no timing field in the byte-compared output; `elapsed_ms`
excluded by the harness comparison, as in M0).

## 3. Behavior gates (M1A-01..M1A-10)

| ID | Status | Evidence |
|----|--------|----------|
| M1A-01 touching chars | PASS | `m1a01_touging_chars_map_to_one_unit` — chars transported, merged multi-char unit exists, geometric overlap per supplied symbol box, merged unit owns ≥2 slots sharing x-range |
| M1A-02 disconnected marks | PASS | `m1a02_disconnected_marks_preserved` |
| M1A-03 overlap no loss | PASS | `m1a03_overlapping_boxes_no_loss` |
| M1A-04 artwork reclass | PASS | `m1a04_unknown_marks_stay_art` |
| M1A-06 wrong-label shape identity | PASS | `m1a06_wrong_label_shape_identity` — same shape key + different semantics (CID separation asserted) |
| M1A-07 meaningful vector coverage | PASS | clean 87.5%, touching 100% (M1-A target ≥80% eligible) |
| M1A-08 same masks diff labels | PASS | `m1a08_same_masks_different_labels_same_ownership` |
| M1A-09 raster restore + owner | PASS | `m1a09_pipeline_restores_raster_and_owner` — raster regions exist AND contain real source ink (fidelity asserted) |
| M1A-10 determinism | PASS | `m1a10_deterministic_repeat_runs` (PDF + report bytes); CLI double-build sha1 equal (§2) |

## 4. Suite results (executed in this tree)

| Suite | Result |
|---|---|
| `cargo test` | **46 passed, 0 failed** (38 M0 + 8 M1A) |
| `checks.py` E0..E7 e-proofs | **8/8 PASS** (E0 four-part key, E1 outline+CIDs, E2 two GIDs one string, E3 wrong label, E4 UTF-16 transport, E5 kana, E6 span owners, E7 determinism) |
| `checks.py` default 8 pages | visual gates: 8/8 pages FAIL — **inherited, unchanged from the accepted M0-Q baseline `f5e5cb5`** (verified by a full check-value diff: zero flips; only p06 MAE metrics improved 0.0103→0.0044). p08 pdfium transport cardinality FAIL — also unchanged/inherited. |
| `test_text_search.py` | All required gates PASS: three required queries found by NATIVE PDFium search in B2 and B0, astral `𝐀`, kana, p08 decimals, no intra-word spaces, qpdf `--check`. One FAIL (§5 N1). |
| `test_corpus_adapter.py` | PASS |
| `test_subpixel_metric.py` | PASS |
| `validate_fixtures.py` | PASS |
| Deliverable determinism | PDF + report sha1 identical across independent builds |

## 5. Remaining defects and limitations

Inherited from the accepted M0-Q baseline (present at `f5e5cb5`, unchanged):
- Visual IoU/edge/MAE/topology gates fail on all 8 default pages (tight
  sub-half-pixel tolerances; e.g. p01 poppler p95=0.51 vs 0.5 limit).
- p08 pdfium transport cardinality (`\x02` merge artifact).
- Astral-plane extraction depends on engine; handled via ToUnicode transport.

New or changed by M1-A:
- **N1 — PDFium orders invisible owner runs after visible runs.** On a page
  whose fallback span sits mid-line (p10 page1's `1` in "Page 1 of 4"),
  PDFium's `get_text_bounded` emits the overlaid owner text at the end, so
  `search("Page 1 of 4")` fails in engine #2. Positions are verified correct
  in the content stream, Poppler extracts the whole page in correct reading
  order, and the page's other content extracts normally. Engine #2 extraction
  ordering quirk only; no data loss, no misplacement. (Measured: wrapping the
  run in `/ActualText` does not change the hoisting; the runs are already
  emitted last in content order.)
- **L1 — Not a general document pipeline.** Single page, single OCR input
  format (hOCR), `--mode reconstruct` only; multi-page/M1-B out of scope.
- **L2 — Fixtures, not a corpus.** No real benign corpus was mounted in this
  environment (BLOCKED); all evidence is synthetic, tesseract-hOCR-seeded
  fixtures, with p11/p12 using deliberately derived synthetic boxes.
- **L3 — Fallback size.** Fully-raster pages are large (fallback.pdf 143 KB
  for one small page); 300 dpi sub-raster embedding, uncompressed RGB.
- **L4 — Migration shims.** Compiled-out duplicate modules (`probes/.../
  src/{encoding,units,pdf,baseline}.rs`, `scanweave-io/src/{pdf,baseline}.rs`)
  remain during the M1-A refactor; removal is M1-B scope.
- **L5 — Fixture hOCR files carry absolute image paths** (written by
  tesseract during fixture generation); no committed crate code or
  qualification script contains hard-coded absolute paths.

## 6. Freeze points verified

- Status still PROVISIONAL (M1-A does not itself close M1).
- No repo-wide dtype renames; existing report JSON shapes preserved
  (`occurrences` + `glyph_stats` are additions, not renames).
- No bypassed add_eproofs: E0–E7 run in the existing harness only.
- No hard page-1 special-casing.
- No prompt-injected verdicts.
- Architecture accepted at 392d42d intact: CID/GID separation (E1/E2 PASS),
  wrong-label preservation (E3 PASS, iou 0.9869), ToUnicode transport (E4
  PASS), no double-ownership of components (solver invariant, E6 PASS).
- Twelve review round-1 findings fixed or honestly corrected (see §0).

## 7. Instruction

This report is submitted for the second independent review (the M1-A
implementation gate). The reviewer should verify the §0 fix table, re-run the
suites, and confirm no new regressions against the accepted `f5e5cb5` state.
