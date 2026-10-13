# Upstream evidence register

Reviewed on **13 October 2026**. These links establish documented building blocks and comparison tools, not tested combinations or measured performance. GitHub default branches move; M0 must record immutable revisions and source/licence hashes. No upstream code, font files, model weights, PDFs or scans are redistributed in this handoff.

The specification's requirements and proposed thresholds are design decisions. They are not quoted upstream guarantees. External projects' compression and compatibility claims have not been independently reproduced here.

## S01 — Smoothscan

Source: `https://github.com/ncraun/smoothscan`

README describes a 0.1.0 tool that classifies scanned symbols, vectorizes them, builds a TrueType font and embeds it in PDF. It documents arbitrary character mappings and 1-bit input. Repository identifies GPLv3+. Establishes prior art; not a ready production replacement or permissively licensed implementation to import.

## S02 — OCRmyPDF optimization

Source: `https://ocrmypdf.readthedocs.io/en/latest/optimizer.html`

Documents optimization levels, lossless/lossy distinctions, codec-dependent behaviour and the possibility of output growth. Record exact output-type/codec/settings in any baseline. Do not assume every setting described as optimization preserves original pixels.

## S03 — Tesseract API and command-line usage

Sources: `https://tesseract-ocr.github.io/tessdoc/APIExample.html` and `https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html`

Documents symbol iteration, confidence/boxes, language arguments, hOCR, word-level TSV and searchable-image PDF output. Older API examples must be tested against the pinned release. Tesseract scores are not automatically calibrated correctness probabilities.

## S04 — Tesseract character-box hOCR

Source: `https://github.com/tesseract-ocr/tesseract/blob/main/src/api/hocrrenderer.cpp`

The renderer reads `hocr_char_boxes`; this supports the proposed `-c hocr_char_boxes=1 hocr` input workflow. Pin the implementation and verify actual emitted geometry, including Unicode clusters, rather than assuming one box equals one scalar or one connected component.

## S05 — VTracer

Source: `https://github.com/visioncortex/vtracer`

MIT-licensed raster-to-vector project in Rust. Its output styles/contour handling must be adapted for real font contours, especially holes. No particular current crate API or new tracing-engine version is frozen by this document.

## S06 — Fontations

Source: `https://github.com/googlefonts/fontations`

Documents `write-fonts` for modifying/serializing OpenType tables, `read-fonts` for parsing, and related outline tooling. Repository identifies MIT/Apache-2.0 licensing. `kurbo` appears in the documented dependency graph; the exact curve conversion API is an M0 probe, not an assumed function signature.

## S07 — pdf-writer

Sources: `https://github.com/typst/pdf-writer`, `https://docs.rs/pdf-writer/latest/pdf_writer/writers/struct.Type0Font.html`, `https://docs.rs/pdf-writer/latest/pdf_writer/writers/struct.CidFont.html`, and `https://docs.rs/pdf-writer/latest/pdf_writer/writers/struct.PropertyList.html`

Rust PDF-writing primitives. The proposed CID/Unicode/ActualText output must be demonstrated in independent readers; availability of dictionary writing is not proof of extraction correctness.

## S08 — Internet Archive PDF Tools

Source: `https://github.com/internetarchive/archive-pdf-tools`

README describes MRC decomposition, hOCR text layers and existing operational use. Most code is AGPL-3.0; the README identifies an Apache-2.0 exception for one renderer module. Use the tool as a black-box comparator; no code import is required. Its README notes limitations around recoding existing PDFs, so use image-stack inputs for a fair early baseline.

## S09 — lopdf

Source: `https://github.com/J-F-Liu/lopdf`

Rust PDF manipulation library, considered for source-PDF/object copying. Actual preservation of document features is an application-level test requirement, not guaranteed merely by choosing the library.

## S10 — hayro

Source: `https://github.com/LaurenzV/hayro`

Rust PDF interpreter/renderer. The inspected README calls it experimental/work-in-progress and identifies unsupported edge cases. Use a pinned qualified subset and independent validation, not an unconditional all-PDF support claim.

## S11 — Scribe OCR

Source: `https://github.com/scribeocr/scribeocr`

A text-recognition/proofreading/fully-digitized-document application. Optional reconstruction baseline, not a claim that its font strategy reconstructs original glyph outlines. Pin the engine and exact export mode before comparison.

## S12 — qpdf

Source: `https://github.com/qpdf/qpdf`

A PDF transformer/inspection tool used as an independent structural checker. Structural validity is not visual or semantic correctness.

## S13 — FontTools

Source: `https://github.com/fonttools/fonttools`

Python font inspection/manipulation library. Development/qualification-only alternative parser/oracle; no mandatory Python runtime is introduced by choosing it for tests.

## S14 — Leptonica

Source: `https://github.com/DanBloomberg/leptonica`

Established image processing/analysis primitives. Optional native adapter only if a measured need justifies it. Exact packaging/features/licences remain part of M0's shipped dependency audit.

## S15 — OpenType Sanitizer

Source: `https://github.com/khaledhosny/ots`

README describes parsing, validation and sanitization of OpenType and command-line `ots-sanitize`. Independent validation tool, not proof of correct PDF semantic mapping or faithful visual reconstruction.

## S16 — TrulyFreeOCR

Source: `https://github.com/msmarkgu/TrulyFreeOCR`

Authors describe a Java CLI with MRC PDF output and local OCR integration. Optional current-tool baseline; no independent reproduction or endorsement of its comparative/licensing claims is implied. Not selected as a mandatory runtime dependency.

## S17 — PdfCraft source inspection

Sources: `https://github.com/storytold/pdfcraft/blob/main/Cargo.toml` and `https://github.com/storytold/pdfcraft/blob/main/crates/ocr/src/lib.rs`

Fetched through the GitHub connector. Observed **file blob** hashes (not repository commit hashes):

- Cargo.toml: `169af97f28825a8722b4f545b346dc7f17e2dd5b`.
- crates/ocr/src/lib.rs: `8d56fa4aa447cc6f4f93ded8f58ac49cb724f762`.

The OCR module describes invisible text over retained pixels, contains a word/line geometry interface and a Latin-oriented recognition alphabet. The workspace identifies `MIT OR Apache-2.0` and existing PDF-related crates. Integration should consume host-supplied/external OCR without inheriting the current recognizer's alphabet restriction. M0 must resolve a full repository commit before relying on a particular host API.

## S18 — PDF specification reference to consult during implementation

Index: `https://pdfa.org/resource/pdf-specification-archive/`

Adobe-hosted PDF 1.7 equivalent: `https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf`

The archive/index was verified. Fetching the full Adobe PDF was blocked by the research tool's file-size limit, so it was **not fully inspected** for this handoff. The implementer must consult the applicable composite-font, ToUnicode, text-extraction and replacement-text sections directly, and qualify ActualText/vertical/glyphless behaviour through actual reader tests. No claim of a completed standards-conformance audit is made.
