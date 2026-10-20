# ScanWeave M1-D Report

Status: **IN PROGRESS / NOT COMPLETE**. M1-D completion gate is not met.

## Scope and revisions

- Frozen baseline: `66f00b1` (`M1-C-R4`).
- Implementation revision: `50bbbda` (`M1-D: add guarded visual glyph dictionary checkpoint`).
- Policy hash (clearscan, representative): `0e7fe93b858b8b151d734c9cc2bbe5e866bdb9b313ebd57a822c2bb2f4c6ba3d`.
- Policy: faithful default remains `min_ink_iou = 0.98`; ClearScan profile is enabled with `--profile clearscan` / `--glyph-dictionary visual`.
- Benign development corpus: **BLOCKED / unavailable**. All evidence below is synthetic.
- Sealed holdout: untouched.

## Implementation delivered

- `crates/scanweave-io/src/visual_dict.rs`: document/page visual dictionary. Candidate groups require exact dimensions, topology, density compatibility and mask IoU >= 0.96. The representative is traced once and every member is rechecked at the configured outline-fidelity gate (floor 0.98).
- `crates/scanweave-io/src/convert.rs`: visual dictionary invocation in `convert_parts`; `glyph_ink_iou` exposed as `pub(crate)` for pre-validation.
- `crates/scanweave-cli/src/main.rs`: `--profile faithful|clearscan`, `--glyph-dictionary off|visual`.
- `Policy` now serializes `profile` and `glyph_dictionary`.

## Measured results

All outputs were generated at 300 DPI with `--mode auto --min-ink-iou 0.98`. 600 DPI source scans were not available in the fixture corpus; running `--dpi 600` on the existing 300 DPI rasters would not change pixel geometry and is not reported as authentic 600 DPI evidence.

| Document | Baseline bytes | Faithful bytes | ClearScan bytes | Vector coverage | Min fidelity | Font glyphs | Selected |
|---|---:|---:|---:|---:|---:|---:|---|
| p01_latin | 10109 | 10109 | 10109 | 1.0000 | 0.9964 | 4 | reconstruct |
| p03_kana | 6427 | 6427 | 6427 | 1.0000 | 0.9905 | 2 | reconstruct |
| p15_decorative | 11866 | 11866 | 11866 | 1.0000 | 0.9828 | 16 | reconstruct |
| doc4_mixed | 105259 | 105259 | 105259 | 0.4905 | 0.9828 | 69 | reconstruct |
| doc4_repeat | 92184 | 92184 | 92184 | 0.0000 | none | 104 | raster_baseline |
| doc4_invoice | 168727 | 168727 | 168727 | 0.0000 | none | 196 | raster_baseline |
| p06_degraded | 22304 | 22304 | 22304 | 0.0000 | none | 1 | reconstruct |
| p16_statement | 31536 | 31536 | 31536 | 0.0000 | none | 26 | raster_baseline |

External baselines:
- OCRmyPDF: **not installed**.
- IA MRC: **not available**.
- qpdf: available at `tools/dist/bin/qpdf`; `qpdf --check` succeeds on representative outputs.
- OTS: not built in this environment (CI builds it from source).
- PDFium/Poppler text extraction: available and used by the existing qualification gates.

## Dictionary findings

- The dictionary does not yet produce any non-exact cluster on the available documents.
- Distinct same-size, same-topology glyph pairs above the 0.96 mask-IoU threshold: **0**.
- Distinct exact-mask shapes before and after clustering are unchanged on every measured document.
- Visual clusters and representatives: effectively 1:1 with exact-mask shapes.
- False merges: 0.
- False splits: all distinct source observations remain separate.
- Accepted candidate substitutions: 0.
- Rejected substitutions: 0 measured (no candidates reached the fidelity gate on real documents).
- Actual font bytes saved by the new dictionary: **0 bytes** on all measured documents.
- A dictionary that merely deduplicates identical masks is already handled by the existing shape-key table; the new dictionary adds no measured benefit.

## Fidelity profile findings

- `--profile clearscan` is currently byte-identical to faithful mode on every measured document.
- The established faithful 0.98 threshold remains unchanged.
- ClearScan does not yet implement an independently qualified contour-smoothing, topology, or typography change. It enables the dictionary only; since the dictionary has no effect, ClearScan has no effect.
- Small/degraded text falls back to raster at 0.98 (p06, p16, invoice/repeat), as recorded above. This is explicit: useful qualified vector coverage is absent for those documents.

## Search and correctness

- Existing Rust workspace tests: pass.
- Clippy (`-D warnings` on core/io/cli): pass.
- Python qualification gates executed and passed: sub-pixel metric, corpus adapter, fixture schema, text search, paint fidelity, document search.
- qpdf structural check: pass on representative outputs.
- Poppler/PDFium extraction: available; existing text-search gate covers p09/p10 and related fixtures.
- Native PDFium search on ad hoc outputs was not separately added; inherited gates remain green.
- Determinism: repeated conversions of the same inputs produced identical bytes in the measured batch.

## Failures and limitations

- M1-D completion gate **not met**.
- No material compression improvement over frozen baseline on any measured document.
- No similar-but-different glyph observations were safely reused.
- No distinctive source-font preservation improvement was demonstrated.
- ClearScan profile does not yet differ from faithful mode.
- 600 DPI evidence is blocked by fixture availability.
- Real-document qualification is blocked by corpus unavailability.
- OCRmyPDF and IA MRC baselines are unavailable in this environment.
- OTS was not run locally (CI builds it from source).

## Commands used

```bash
cargo build --workspace
cargo test --workspace
cargo clippy -p scanweave-core -p scanweave-io -p scanweave-cli -- -D warnings

# Representative conversion
scanweave-cli build qualification/fixtures/probe/p01_latin/p01_latin.png \
  --ocr qualification/fixtures/probe/p01_latin/p01_latin.ocr.json \
  --dpi 300 --mode auto --min-ink-iou 0.98 --profile clearscan \
  --output work/m1d-evidence/p01_latin.clearscan.pdf \
  --report work/m1d-evidence/p01_latin.clearscan.json

# Structural check
LD_LIBRARY_PATH=$PWD/tools/dist/lib tools/dist/bin/qpdf --check work/m1d-evidence/p01_latin.clearscan.pdf
```

## M1-D5 update (supersedes this report's earlier checkpoint)

The earlier checkpoint above predates the document-wide reconstruction work and
must not be read as the current experimental result. Commit `c4a61ea` adds a
12-page synthetic oracle demonstration at 300/600 DPI: donor-supported `e` and
`a` repairs improve the matched final-PDF pristine IoU, and the 600-DPI `8`
case has a small gain. The 300-DPI `8` is rejected and retained as raster, but
its local PDF fallback rendering is materially worse than the whole-page raster
baseline. The exact source crop is present in the PDF; the rendering discrepancy
is still unresolved.

M1-D remains **IN PROGRESS / NOT COMPLETE**. The current ClearScan candidate
has 2.23%/3.98% text-ink vector coverage at 300/600 DPI, accepts no intact
document-wide reuse candidates under the 0.98 faithful reuse gate, and is
31,597/29,253 bytes larger than the searchable-raster baseline. The new
best-donor path demonstrates reconstructed typography, but does not qualify
compression or production acceptance. Evidence fusion (A4), risk-calibrated
acceptance (A5), realistic degradation calibration, independent font/document
FIT/DEV cohorts, and real-domain validation remain incomplete. No LOCKBOX was
opened. See `qualification/evidence/m1d_document/qualification.md` and its
machine-readable evaluation JSONs for the corrected matched-PDF metrics.

The current independent review approves **CONTINUE RESEARCH**, not promotion.
Keep faithful mode and the 0.98 threshold unchanged. Fix and regress the
fallback rendering discrepancy, validate faithful-mode appearance against the
source baseline, build realistic held-out synthetic and legally usable real
scan cohorts, then qualify A4/A5 and document-wide reuse before requesting any
LOCKBOX evaluation.
