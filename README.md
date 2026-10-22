# ScanWeave

ScanWeave reconstructs document-specific vector typography from scanned PDFs, rather than only adding invisible OCR text over page images.

This free, open-source, scriptable ClearScan-like converter has a working Rust CLI and reusable library components. It learns supported glyph shapes from repeated observations within your document; it does not require the original font.

- Reuse reconstructed outlines for clearer, scalable text where the evidence supports replacement.
- Produce searchable PDFs using Tesseract recognition and embedded Unicode fonts.
- Reduce redundant raster storage while retaining unsupported text and artwork as images.

## Build and convert

Install [Rust with rustup](https://rustup.rs/), Git and the platform dependencies below. There are no prebuilt downloads to install.

```sh
# Debian / Ubuntu
sudo apt install build-essential pkg-config poppler-utils tesseract-ocr tesseract-ocr-eng
# macOS, with Homebrew
brew install poppler tesseract

git clone https://github.com/mitchins/scanweave.git
cd scanweave
cargo build --release --locked
export PATH="$PWD/target/release:$PATH"
scanweave input.pdf output.pdf
```

Conversion defaults to ClearScan at 300 DPI; the adjacent `output.pdf.json` records provenance and conversion results. Install additional Tesseract language data before selecting another language.

Use `--profile faithful` for the independent preservation profile without ClearScan's lossy residual-image encoding.

OCR can fail, not every page vectorizes or becomes searchable, and ClearScan is not pixel-exact; real-document quality and size still vary.

[Technical guide](docs/DEVELOPER_GUIDE.md) · [Measured results](ACR_04_REPORT.md) · [MIT](LICENSE-MIT) / [Apache-2.0](LICENSE-APACHE)
