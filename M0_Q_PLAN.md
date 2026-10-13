# M0-Q Plan — qualification closure (evidence gaps only)

Status: executing under operator charter of 2026-10-14. Commit `3172a32` (tag
`m0-provisional-baseline`) is the frozen baseline. NOT a development milestone: no
architecture, algorithm or interface changes. Defect repairs allowed only where a
concrete qualification failure demonstrates one; any metric/threshold change is a
versioned policy amendment requiring independent review — never auto-relaxed.

## Q1 — Independent reproduction
- Fresh `git clone` of the frozen tag into a clean directory; execute the full committed
  suite there: `cargo test` (36 incl. E0 property), `validate_fixtures.py`, `checks.py`,
  `measure.py`.
- Record exact tool versions, commands, exit codes, and SHA-256 of every acceptance
  artifact (PDFs, TTFs, renders, result JSONs). Output: `qualification/REPRODUCTION.md`.
- This closes the "reviewer could not execute" distinction in the ledger.

## Q2 — Visual-failure characterization (localized, no threshold relaxation)
- **PDFium ~1.1 px displacement**: per-edge signed displacement histograms vs Poppler on
  the same files; glyph-geometry ground truth via fontTools outline rendering
  (rasterizer-independent) to separate (a) outline geometry, (b) placement transform,
  (c) renderer AA. Localized crops: counters, punctuation, kana dakuten, currency/decimal
  symbols.
- **p01 MAE 0.0206 vs 0.02**: localize contributing pixels (expected: AA edge band);
  quantified breakdown (edge-band vs interior vs background).
- Outcome: (a) defect repair if the geometry/placement is at fault (allowed, then re-run
  affected gates), or (b) a draft versioned policy amendment (`m0-qual-1`: e.g. engine
  AA-aware comparison or metric normalization) submitted for independent review — not
  silently applied. Unchanged gates keep FAIL/BLOCKED status.

## Q3 — Benign pilot corpus
- Environment check performed 2026-10-14: no corpus mounted anywhere on this machine.
- Deliver the turnkey adapter (`qualification/corpus_adapter.py`): expected layout
  `<corpus-root>/<stratum>/<document>/page.*` + `.hocr`/`.json`, document-level split
  manifest with holdout isolation, conversion into probe page bundles (pixel-hash bound).
- Execution BLOCKED pending operator mount; recorded as such, never substituted.

## Q4 — External MRC baselines (bounded, no-root)
- Build leptonica + tesseract 5 from pinned sources into `tools/` (no root required);
  then OCRmyPDF into the qualification venv; attempt Internet Archive `archive-pdf-tools`
  build. Every attempt records exact revision/hash/config or the precise blocker.
- On success: run on the SAME synthetic sources as B0/B2; measure file bytes, text
  extraction, fidelity (same metrics), retained non-text content, and repeated-glyph
  coverage so reconstruction cannot claim success via raster fallback. On failure:
  BLOCKED with reasons.

## Q5 — Consolidated gate report
- `M0_Q_REPORT.md`: every acceptance criterion from SPEC/QUALIFICATION/operator charter
  marked PASS / FAIL / BLOCKED with reproducible evidence and artifact hashes. No
  implicit waivers. Submitted to deepseek-reviewer for sign-off.

## Anti-scope
No engine redesign, no new features, no interface changes, no threshold relaxation
without review, no corpus fabrication, no synthetic-for-real substitution.
