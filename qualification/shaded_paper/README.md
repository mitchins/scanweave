# Shaded-page ownership evidence

**Rejected trial; no product code enabled.** See `../../CLEARSCAN_SHADED_PAPER_REPORT.md`.

Base: `8bc191e`; catch-up review checkpoint: `5fe99c1`. A and B use exactly the existing `history-02` image-only PDF, normal Tesseract engine and `scanweave input.pdf output.pdf` path. The sealed holdout was not accessed. Existing dataset attribution remains under `../pdf_packaging/`.

## Inspect

- `illumination.png`: source, original decision, local paper field, residual confidence and candidate mask.
- `accepted-glyphs.png`: PDFium source/vector/final/raster/Adobe at matched physical coordinates.
- `poppler-glyphs.png`: independent high-zoom Poppler final/vector/raster crops.
- `rejected-vector-only.pdf`: actual B embedded font and placements; unused image resources and the paper fill were removed for inspection. It is not a deliverable converter output.
- `audit.json`: actual CID/GID paint counts, byte decomposition, timings and extraction comparison.
- `results.json`: proposals, rejection reasons, observation bounding boxes and native text.
- `manifest.json`: original, frozen comparator and local full-output hashes. The Adobe file is a five-page collection, rendered page index 2.

Complete `a.pdf`, `b.pdf`, their raster-only derivatives and large full-page/zoom renders are preserved locally but ignored. They are not advertised as remotely hosted. Patches, hashes, run logs, focused PNGs and the 82 KB actual-font PDF are committed instead.

## Reproduce either rejected candidate

Use an isolated checkout/worktree; do not enable rejected code in a user's working converter:

```sh
git worktree add --detach /tmp/scanweave-shaded-replay 8bc191e
# Use absolute paths to this evidence folder and the existing development input.
gzip -dc /path/to/scanweave/qualification/shaded_paper/candidate-a.patch.gz |
  git -C /tmp/scanweave-shaded-replay apply -
cargo build --release --manifest-path /tmp/scanweave-shaded-replay/Cargo.toml \
  --target-dir /tmp/scanweave-shaded-target
/tmp/scanweave-shaded-target/release/scanweave \
  /path/to/scanweave/qualification/pdf_packaging/real/input/history-02.pdf \
  /tmp/shaded-a.pdf
```

For B, start another clean detached checkout at the same commit and apply **only** `candidate-b.patch.gz` (it contains the whole B delta, not an incremental patch on A). The original source/evidence must be present from the established licensed development corpus. These commands intentionally do not fetch new data or touch holdouts.

`diagnose.py`, `render_results.py`, `glyph_crops.py` and `audit.py` use the existing pikepdf/NumPy/Pillow/pypdfium2/fontTools environment and Poppler. They expect the local A/B PDFs at this folder's recorded paths; exact conversion commands are in the GNU-time logs. `render_results.py` removes images for vector inspection and text objects for raster inspection without changing glyph matrices. The vector inspection additionally removes the solid paper rectangle so dark ink can be seen on white. Large 864-DPI Poppler page renders are derived local artifacts; committed crops retain the useful evidence.

Normal product was restored and rebuilt. `restored.pdf` is byte-identical to `../real_convergence/outputs/history-02.pdf`. Because the primary candidate failed, no failed path was propagated to the secondary page, controls or full corpus. Previous successful corpus results are preserved, not claimed as a fresh run.
