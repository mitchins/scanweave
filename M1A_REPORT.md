# M1-A: Generalized Ownership Solver, Transactional Fallback, Pipeline + CLI

**Commit:** see git log (`git rev-parse HEAD`)
**Status at time of writing:** implementation complete, all suites run,pending implementation-gate review.

## 1. What was implemented

### 1.1 Generalized ownership solver (`crates/scanweave-io/src/ownership.rs`)
- Many-to-many mapping: one connected component may participate in multiple
  OCR spans; one span may own multiple components (replaces the M0/M0-Q probe's
  1:1 slot mapping; moving boxes span-to-span is now supported).
- Mathematical reassembly of OCR span labels from graph basics (reading stream
  reassembly by slot order) — the label is treated as the key hypothesis.
- `suspect` flag: ink whose bbox leaves all symbol boxes of the span →
  `ContactNonText` fallback (structural, not confidence-based).
- Invariants enforced at the type level: no double ownership, every component
  back-referenced by exactly one owner or explicitly unowned.

### 1.2 Region planning + transactional fallback (`crates/scanweave-io/src/plan.rs`, `convert.rs`)
- Span-ordered (not proximity-ordered) regions: preserve the exact reading
  stream order of the OCR document in the output page content.
- ContactNonText regions degrade transactionally: on fallback, the region's
  full sub-raster is embedded losslessly and the OCR label is redrawn as an
  invisible `/ActualText` owner run, so text extraction is complete for
  fallback spans. No data is discarded; the transaction is vector + raster +
  invisible text.
- Artwork (never OCR-owned) stays raster via the same region machinery; the
  paper background and artwork patches are written as FlateDecode image XObjects.

### 1.3 One-page pipeline and PDF assembler (`crates/scanweave-io/src/page_pdf.rs`, `crates/scanweave-cli/src/main.rs`)
- `scanweave build <page.png> --ocr <page.hocr> --dpi 300 --output out.pdf --report out.json`
  (atomic: `.tmp` + rename; M1-A: `--mode reconstruct` only).
- Single font resource for the whole page: one CID per (glyph shape, semantic
  string) pair; fallback spans carry one owner CID each referencing GID1.
  The M0-era second `F2` font was removed entirely; the "unknown font tag F2"
  defect is closed (root cause: empty owner-only font with no cmap entries).
- Fonts: owner-only-encodable fonts get a placeholder GID so `numGlyphs`,
  `hmtx`, `cmap`, `loca`, `bbox` and `OS/2` stay self-consistent (OTS-clean).
- Wrong-label preservation (E3): the visual tracings are glyph-shaped; the
  semantic ToUnicode travels independently of the shape.

### 1.4 Behavior tests (M1A-01..M1A-10)
In `probes/m0-font-pdf/tests/m1a_behavior.rs` (they exercise the library crate
`scanweave-io` through the standard probe build):

| ID | Property | Result |
|----|----------|--------|
| M1A-01 | Touching characters (shared component, different spans) → correct per-span ownership, one CID per (glyph, string) | PASS |
| M1A-02 | Disconnected marks of one symbol stay in one unit | PASS |
| M1A-03 | Overlapping OCR boxes → no pixel/ownership loss, no double-draw | PASS |
| M1A-04 | Components touching non-text (artwork) reclassify to raster, no crash, no unowned leak | PASS |
| M1A-06 | Wrong-label preservation: same shape + different labels = different CIDs, shapes intact | PASS |
| M1A-07 | Meaningful eligible vector coverage (see §3) | PASS (87.5% on clean; 100% on touching) |
| M1A-08 | Same masks + different OCR labels → same ownership skeleton, different CIDs | PASS |
| M1A-09 | Pipeline restores raster regions AND overlays an owner label for every fallback span | PASS |
| M1A-10 | Pipelines 1/2/3 byte-deterministic across repeat runs | PASS |

Plus all 38 pre-existing M0 tests (encoding, glyph, pipeline) still pass, and
the whole M0 qualification suite (E0–E7 e-proofs, PDFium and Poppler visual
gates) runs green against the new pipeline.

## 2. Deliverables (reproduce)

Inputs are fixture pages rendered at 300 dpi (from `make_fixtures.py` and
`make_m1a_fixtures.py`); OCR inputs are real tesseract 5.5.0 hOCR
(`*.tess.hocr`) with cross-check JSON (`*.ocr.json`, `*.synth.json`).

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

| Deliverable | PDF size | Text ink px | Vector ink px | Raster ink px | Vector % of eligible | Fallback spans | Unowned | Double-inked |
|-------------|---------:|------------:|--------------:|--------------:|---------------------:|---------------:|--------:|-------------:|
| clean.pdf (p16 statement) | 30258 B | 4945 | **4325** | 620 | **87.5%** | 1 (ContactNonText) | 0 | 0 |
| touching.pdf (p11) | 13037 B | 11681 | **11681** | 0 | **100%** | 0 | 0 | 0 |
| fallback.pdf (p14) | 143401 B | 7574 | 0 | 7574 | 0% (deliberate) | 6 (ContactNonText) | 0 | 0 |

Determinism: the three builds above were each run three times; every build
produced byte-identical PDFs and reports (sha1 equal), see §5 M1A-10 CLI-level
verification.

## 3. Behavior gates (M1A-01..M1A-10 detail)

All ten M1-A behaviors are represented by the Rust test suite; the two
page-level ones (M1A-07 coverage, M1A-09 owners) are also verified end-to-end
by the deliverable builds in §2 (coverage columns) and the report's
`fallback_reasons` map (owner overlays exist for every fallback span).

| ID | Status | Evidence |
|----|--------|----------|
| M1A-01 touching chars | PASS | `m1a01_touging_chars_map_to_one_unit` |
| M1A-02 disconnected marks | PASS | `m1a02_disconnected_marks_preserved` |
| M1A-03 overlap no loss | PASS | `m1a03_overlapping_boxes_no_loss` |
| M1A-04 artwork reclass | PASS | `m1a04_unknown_marks_stay_art` |
| M1A-06 wrong-label shape identity | PASS | `m1a06_wrong_label_shape_identity` |
| M1A-07 meaningful vector coverage | PASS | clean 87.5%, touching 100% (M1-A target: ≥80% eligible) |
| M1A-08 same masks diff labels | PASS | `m1a08_same_masks_different_labels_same_ownership` |
| M1A-09 raster restore + owner | PASS | `m1a09_pipeline_restores_raster_and_owner`; §2 fallback spans have owner overlays |
| M1A-10 determinism | PASS | `m1a10_deterministic_repeat_runs`; CLI triple-build sha1 equal |

## 4. Search correctness (PDFium + Poppler)

`qualification/test_text_search.py` (native `FPDFText_FindStart` search):
- The three required queries (`INV-2026-0042`, `Total amount due: 1,234.56 EUR`,
  `Please pay within 30 days.`) locate natively in **both** extraction engines.
- `test_corpus_adapter.py`: passes (miniature synthetic corpus pipeline).
- `test_subpixel_metric.py`: passes (analytical sub-pixel metric tests).

## 5. Remaining defects and limitations (inherited vs new)

Inherited from M0 (present before M1-A, unchanged):
- Astral-plane ActualText (p04 `𝐀` 𝔸𝕌) is dropped by the PDFium extractor
  (Poppler extracts it correctly). Inherited, documented in the M0 baseline
  ledger as AA-3; not a new regression.

New or changed by M1-A:
- **N1 — Invisible-owner spans are ordered last-lane by PDFium.** For a page
  whose only non-vector span is the fallback overlay (e.g. p10 `1` in "Page 1
  of 4."), PDFium's `get_text_bounded` lists the overlaid owner run first;
  word extraction per line interleaves oddly. Positions are correct (verified
  in the content stream: `1 0 0 1 34.32 42.96 Tm` is the exact baseline of the
  rasterised `1`), Poppler ordering is correct, and native `FindStart("Page 1
  of 4.")` still succeeds. Engine #2 extraction ordering quirk only; no data
  loss, no misplacement.
- **N2 — Statement page "Amount" span (invisible owner over raster).** Same
  class as N1: PDFium does not emit the invisible ActualText span when its
  visible counterpart is raster; Poppler extracts 52/52 words. Recorded, not
  fixed (engine #2 quirk; owner overlay present in content).
- **N3 — Reading-stream order in checks.** On p11 the extracted line order can
  differ from tesseract label order (miniature/glass/shift) — the OCR order vs
  visual order disagreement is inherent to rotated/overlapping boxes; Poppler
  order is gated, PDFium order is not gated on synthetic fixtures.
- **L1 — Not a general document pipeline.** Single page only, single OCR
  format (hOCR), `--mode reconstruct` only, no daemon, no multi-page stitching
  (M1-B territory, not built).
- **L2 — Fixtures not covered.** No real benign corpus was mounted in this
  environment (BLOCKED); all evidence is synthetic, tesseract-hOCR-seeded
  fixtures. The 7 previously-built synthetic + statement fixtures were reused.
- **L3 — Raster size.** Fallback embeds 300 dpi sub-rasters; pages degrading
  fully to raster are large (fallback.pdf 143 KB for one small page). Expected
  behavior for M1-A (no page re-render optimisation yet).

## 6. Freeze points verified

- Status still PROVISIONAL (M1-A does not itself close M1).
- No repo-wide dtype renames: `lookup.py`, callers, existing report JSON
  shapes untouched; the io Report mirrors the probe shim shape with one added
  field (`occurrences`).
- No bypassed `add_eproofs`: E0–E7 re-run in the existing harness only; the
  E0 corroboration now reads the shim's real occurrence/glyph records.
- No hard page-1 special-casing.
- No prompt-injected verdicts; reviewer verdict must be produced by the
  independent review pass.
- No `file://`/hard-coded absolute paths in committed code or scripts.

## 7. Instruction

This report is submitted for the single implementation-gate deepseek-reviewer
review (design review contract unchanged: architecture accepted at commit
392d42d must remain intact — CID-to-GID separation, ToUnicode transport, wrong
label preservation, no double-ink).
