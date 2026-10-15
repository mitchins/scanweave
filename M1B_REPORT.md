# M1-B: searchable multi-page documents, economical fallback, honest measurement

**Commit:** see `git log` — implementation frozen at `5462593` (+ deliverable commit
`85e1564`, report commits after it). **Status: implementation complete; suites run.**

## 0. N1 — root cause and fix (the M1-A open defect)

**M1-A's diagnosis was incomplete.** The M1-A report attributed the failure to
"PDFium hoisting invisible runs". A controlled experiment
(`qualification/n1_experiments.py`, four variants on the exact failure
geometry) found the real mechanism: **PDFium merges text runs into a line by
BASELINE and then sorts the line's characters by x.** The M1-A owner run was
placed on the OCR *polygon box* bottom, which sits ~1pt off the visible line's
glyph-ink baseline, so the label formed its own line and was appended out of
order. Evidence: the synthetic variant with the invisible run on the *exact*
shared baseline extracts inline in both engines; the real page's off-baseline
run is hoisted.

**Fix** (no visual change, verified pixel-identical): owner runs stay INVISIBLE
(`3 Tr`, they paint nothing) and are placed on the span's traced **ink
baseline** (`place_px` = the first unit's ink bbox), emitted INLINE in reading
order inside the text object, each with its own per-span `/ActualText`.

Two intermediate approaches were tried, measured, and rejected:
- *visible owner runs on the paper-coloured placeholder*: the placeholder is a
  real filled box (the qualification harness rejects degenerate contours), so
  this painted an ink rectangle — caught by the p06 render diff and the winding
  gate. Provenance kept in the commit history.
- *collinear placeholder*: the harness flags degenerate contours by design.

**Verified:** `test_text_search.py` 49/49 pass (p10 page1 `Page 1 of 4` native
search now passes); M1-A vs M1-B renders of p10 page1 are **pixel-identical
(0 differing pixels)** — the owner run provably paints nothing.

## 1. Economical raster fallback

- `coalesce_patches` merges overlapping/adjacent patches transitively; each
  merged patch re-copies the full source rect of its union, so every emitted
  pixel stays byte-identical to the source (`m1b02`, sha per patch).
- **p14_noisy: 143,143B → 45,878B (204 image XObjects → 1)**, zero new gate
  flips, p06's inherited visual metrics *improved* (pdfium IoU 0.9465→0.9564,
  MAE-ink 0.0453→0.0315).
- `--mode auto` ranks **both** candidates by actually-serialized bytes
  (`reconstruct` vs whole-page searchable raster baseline) and picks the
  smaller; the report records both candidates with their bytes, so the
  evaluation is auditable. The noisy page selects the raster baseline
  (44,999B vs 45,878B).
- No lossy background processing was added.

## 2. Multi-page CLI and document assembler

`scanweave build --bundle document.json [--mode reconstruct|auto] --output … --report …`

- Uses the existing normalized bundle contract (`verify_pairing` — hash-verified
  source+OCR binding per page) and the existing one-page path (`convert_parts`).
- `assemble_document` emits ONE PDF with N pages: **one shared font program**
  (document-wide `(shape, label)` encoding union in first-appearance order, so
  identical content across pages shares CIDs — measured: doc4_repeat is smaller
  than the same four pages built separately, by at least the duplicated fonts,
  `m1b04b`), deterministic object numbering, 16-bit CID bound, atomic publication.
- Per-page MediaBox (dimensions/rotation are the source page's), page order =
  bundle order, per-page and document-level report with coverage, search plan,
  bindings, and honest byte accounting (`image_xobjects`, `raster_encoded_bytes`,
  `content_bytes`, `font_bytes` — actual serialized sizes from an assembly
  side-channel, not estimates).
- Fixtures (hash-verified bundles): `doc2_min`, `doc4_invoice`, `doc4_repeat`,
  `doc4_mixed`, `doc10_mixed` — 2/4/10 pages composing the already-qualified
  single-page fixtures (invoice, repeated statement, noisy, decorative,
  horizontal kana).

## 3. Test evidence (all run in this tree)

| Suite | Result |
|---|---|
| `cargo test` | **53 passed, 0 failed** (46 inherited + 7 M1B) |
| `checks.py` E0–E7 e-proofs | **8/8 PASS**, zero gate flips vs accepted M1-A |
| `test_text_search.py` | **49/49 pass** (was 48/49; the N1 gate now passes) |
| `test_m1b_paint_fidelity.py` | all pass (owner runs paint nothing — 0 px outside patches in both engines; patch reproduces source above measured M1-A baselines; **explicit M1A-05 rule/stamp/barcode regression**: every contacted-region label stays searchable in both engines, exactly as the OCR has it) |
| `test_m1b_document_search.py` | **88/88 pass** (page count/order/dims, per-page native PDFium search incl. `Page N of 4`, kana intact, no duplicates, qpdf --check, report honesty) |
| `test_m1b_baselines.py` | all gates pass (see §4) |
| `test_corpus_adapter.py`, `test_subpixel_metric.py`, `validate_fixtures.py` | pass |
| Determinism | all 5 documents byte-identical (PDF **and** report) across repeat builds, both modes; single-page p10/p14/p16 identical (PDF+report); qpdf --check clean; OTS-sanitize clean |

## 4. External baselines (document level, actual bytes)

| Document | scanweave | OCRmyPDF | IA MRC (per-page sum) |
|---|---:|---:|---:|
| doc4_invoice | **54,592 B** | 174,549 B | 154,867 B |
| doc4_repeat | **41,781 B** | 93,299 B | 95,295 B |
| doc4_mixed | **79,175 B** | 117,248 B | 115,042 B |
| doc10_mixed | **175,297 B** | 306,801 B | 302,085 B |
| doc2_min | **62,057 B** | 80,760 B | 72,471 B |

scanweave is 1.5–3.2× smaller than both external baselines at equal content,
with ink IoU 0.79–1.00 per page (OCRmyPDF at `--optimize 0` reaches 1.0 by
embedding the source losslessly — at 2–3× the bytes; IA MRC is lossy on the
noise-heavy pages). Gates: scanweave ≤ both baselines on every document, and
scanweave's per-page ink IoU ≥ 0.75 everywhere. IA MRC is a per-page tool; the
document number is the sum of per-page runs, stated as such.

## 5. Required demonstrations

1. **Native PDFium search for `Page 1 of 4` on the mixed line** — PASS (single
   page and inside doc4_invoice page 1, both engines).
2. **Statement rows / financial tokens searchable in correct groupings** —
   PASS (`Total amount due: 1,234.56 EUR`, `INV-2026-0042`, `Amount`; native
   search per page on all documents).
3. **All architectural E-proofs green** — 8/8 (E0 four-part key, E1 outline/CID,
   E2 two GIDs one string, E3 wrong-label preservation, E4 UTF-16 transport,
   E5 kana, E6 span owners, E7 determinism).
4. **No unowned or multiply-owned ink** — 0/0 on every page and document (real
   pixel census in `convert.rs`).
5. **Noisy example auto-selects the economical candidate** — auto picks the
   raster baseline by real bytes (44,999B < 45,878B); both candidates recorded.
6. **Four-page repeated text → one independently valid, searchable PDF** —
   doc4_repeat: 4 pages, one font, every page native-searchable, deterministic.
7. **Byte-identical output on repeated runs** — verified for all 5 documents
   (PDF + report), both modes, and for the three deliverables.
8. **Font validity / Poppler / PDFium+native search / qpdf** — OTS-sanitize
   clean, Poppler extraction correct and ordered on every page, PDFium native
   search per page, qpdf --check clean (all three deliverables).
9. **Existing visual FAILs recorded, not relaxed** — the inherited visual-gate
   failures and the p08 transport cardinality failure are unchanged (zero
   flips vs 392d42d/f5e5cb5/650dafa); thresholds untouched.
10. **Corpus holdout sealed** — not mounted, not accessed; the M1-B fixtures
    compose existing qualified single-page fixtures only.

## 6. Defects found and fixed during M1-B (by the regression run, before review)

- N1 root cause corrected as above (baseline, not rendering mode).
- The union CID remap remapped CIDs but not glyph indices → the document drew
  local indices into the global shape table (wrong glyph outlines; caught by
  an ink-IoU anomaly on a mixed-size document).
- The single-page B0 candidate was emptied by the `convert`/`convert_parts`
  refactor → all B0 search gates failed; restored (B0 keeps every span's text
  invisibly over the whole-page source patch).
- The owner-runs-before-patches experiment painted an ink box (placeholder is
  a filled contour) — rejected, not shipped.

## 7. Remaining limitations

- **L1 (inherited, engine-specific):** PDFium appends a *separate-line* run at
  the end of its extraction when a fallback owner's span has no visible glyph
  on its line (e.g. an all-fallback page's lines). All such labels still
  extract in Poppler in correct order and in PDFium as text (searchable, no
  duplication); only PDFium's line *interleaving* for those lines differs.
  p10's mixed line (visible+fallback) is fixed; an all-fallback line remains
  PDFium-order-only. Recorded, not concealed.
- **L2:** single-image sources only in the bundle path (PDF/multipage TIFF
  sources return a clear error); multi-page stitching from one asset is not
  implemented.
- **L3:** auto selection is whole-document (reconstruct vs raster baseline);
  per-page hybrid selection is not implemented (the candidates are measured
  and recorded, so this is a policy extension, not a missing measurement).
- **L4:** document-level IA MRC is a per-page sum (the tool is per-page);
  OCRmyPDF is document-level.
- **L5:** the fixtures are synthetic (no benign corpus mounted — BLOCKED);
  all documents compose already-qualified single-page fixtures.
- **L6:** `work/m1b-deliverables/` was force-added past `.gitignore`; a
  regeneration is not auto-tracked (manifest must be re-committed).

## 8. Instruction

Submitted for the independent completion-gate review. The reviewer should
verify the §0 mechanism claim by running `qualification/n1_experiments.py`,
re-run every suite, confirm zero gate flips vs `650dafa`, and attempt to break
the document assembler (mixed page sizes, CID bound, determinism, search
duplication).
