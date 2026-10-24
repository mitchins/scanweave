Run on macOS in R3, after receiving the three **Rust** PDFs and their SHA-256 manifest:

```sh
shasum -a 256 default.pdf cover-2.0.pdf cover-1.5.pdf
swift check.swift results default.pdf cover-2.0.pdf cover-1.5.pdf
```

Uses system Foundation, AppKit and PDFKit; no third-party packages. Renders every
page at 300 dpi and compares page strings and `PDFDocument.string` exactly.
Return `results/report.json`, text files, PNGs, macOS version, input hashes and
visual judgments. Inspect all pages and dense text at enlarged zoom for missing,
garbled or misplaced glyphs. Compare with PDFium at the same resolution, using
default as the rasterization control. Record Preview open/search/copy results
separately. This kit has not been compiled or executed on Linux; a prepared kit
is not a compatibility pass. No P2 input is used.
