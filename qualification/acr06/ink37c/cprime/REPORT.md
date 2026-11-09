# Issue 37: C-prime all-compact candidate

**Verdict: HOLD pending Claude’s independent review.** The three routed pages use compact lossy source raster. The automatic checks cannot establish preservation of every stroke or artwork feature; the visual panels and source comparison remain part of acceptance. This report does not claim source-pixel identity for JPEG.

## Design and decisions

The qualified polarity and final visible-occurrence gate is unchanged. The affected pages are historical 2 and 5 and receipts 4, covering the 65 known wrong-colour visible glyph locations (22, 36 and 7). Their images start from the canonical source RGB, not main’s cleaned residual; the visible text shows are suppressed and searchable text remains invisible. The seven other inverted pages and all normal pages keep the existing representation. The encoder remains the existing 200-DPI JPEG85 4:2:0 path, including its eligibility policy and at least 5% savings against the source-exact patch.

The OCR-box chromatic veto was removed at the owner’s direction: OCR boxes can overlap ornament and the veto was calibrated on only three pages. Page RGB MAE ≤10, OCR-box dark-pixel recall ≥0.98, nonempty ink evidence, encoder eligibility and savings remain mandatory; rejection retains the source-exact baseline. These checks do not assess all artwork or guarantee every fine stroke. The destructive high-frequency ink test continues to exercise exact fallback. There is no change to segmentation, donors, geometry, q3 or OCR semantics.

| Page | Selected | Fidelity / encoding | Decoder MAE | Dark-pixel recall | Decision |
|---|---|---|---:|---:|---|
| historical 2 | raster_baseline_compact | clearscan_compact_lossy / jpeg | 6.7781 | 0.999958 | accepted |
| historical 5 | raster_baseline_compact | clearscan_compact_lossy / jpeg | 3.9768 | 0.999996 | accepted |
| receipts 4 | raster_baseline_compact | clearscan_compact_lossy / jpeg | 1.7785 | 1.000000 | accepted |

All 32 route decisions and luminances: [page-decisions.json](page-decisions.json). These admission metrics are source-resolution JPEG decode/upsample measurements; completed-PDF source-render MAE, SSIM and dark-pixel recall are in [final-fidelity.json](final-fidelity.json).

## PDF and image bytes

| Document | A main | B #38 | C mixed | C-prime |
|---|---:|---:|---:|---:|
| historical | 2,246,646 | 13,762,217 | 5,994,232 | 2,247,390 |
| financial | 2,842,414 | 2,842,414 | 2,842,414 | 2,842,414 |
| mixed | 920,248 | 920,248 | 920,248 | 920,248 |
| receipts | 1,266,836 | 2,374,622 | 1,266,953 | 1,266,953 |
| forms | 831,974 | 831,974 | 831,974 | 831,974 |
| **Total** | **8,108,118** | **20,731,475** | **11,855,821** | **8,108,979** |

Expected C-prime total 8,108,979 bytes; measured 8,108,979 (matches). Document SHA-256 hashes, encoded-image filters, sizes and dimensions are in [bytes.json](bytes.json). Page totals count encoded image streams and do not apportion shared PDF overhead.

| Page | A bytes | B bytes | C bytes | C-prime bytes |
|---|---:|---:|---:|---:|
| historical 1 | 451,336 | 451,336 | 451,336 | 451,336 |
| historical 2 | 306,274 | 4,053,348 | 4,053,348 | 306,608 |
| historical 3 | 252,220 | 252,220 | 252,220 | 252,220 |
| historical 4 | 629,404 | 629,404 | 629,404 | 629,404 |
| historical 5 | 558,993 | 8,327,288 | 559,403 | 559,403 |
| financial 1 | 168,983 | 168,983 | 168,983 | 168,983 |
| financial 2 | 118,923 | 118,923 | 118,923 | 118,923 |
| financial 3 | 154,805 | 154,805 | 154,805 | 154,805 |
| financial 4 | 159,351 | 159,351 | 159,351 | 159,351 |
| financial 5 | 141,195 | 141,195 | 141,195 | 141,195 |
| financial 6 | 160,726 | 160,726 | 160,726 | 160,726 |
| financial 7 | 144,818 | 144,818 | 144,818 | 144,818 |
| financial 8 | 189,804 | 189,804 | 189,804 | 189,804 |
| financial 9 | 151,487 | 151,487 | 151,487 | 151,487 |
| financial 10 | 131,041 | 131,041 | 131,041 | 131,041 |
| financial 11 | 167,809 | 167,809 | 167,809 | 167,809 |
| financial 12 | 115,613 | 115,613 | 115,613 | 115,613 |
| financial 13 | 170,890 | 170,890 | 170,890 | 170,890 |
| mixed 1 | 253,560 | 253,560 | 253,560 | 253,560 |
| mixed 2 | 256,604 | 256,604 | 256,604 | 256,604 |
| receipts 1 | 83,699 | 83,699 | 83,699 | 83,699 |
| receipts 2 | 66,397 | 66,397 | 66,397 | 66,397 |
| receipts 3 | 168,476 | 168,476 | 168,476 | 168,476 |
| receipts 4 | 122,528 | 1,230,205 | 122,638 | 122,638 |
| receipts 5 | 48,912 | 48,912 | 48,912 | 48,912 |
| receipts 6 | 485,445 | 485,445 | 485,445 | 485,445 |
| receipts 7 | 60,807 | 60,807 | 60,807 | 60,807 |
| receipts 8 | 58,362 | 58,362 | 58,362 | 58,362 |
| receipts 9 | 59,408 | 59,408 | 59,408 | 59,408 |
| receipts 10 | 71,595 | 71,595 | 71,595 | 71,595 |
| forms 1 | 386,679 | 386,679 | 386,679 | 386,679 |
| forms 2 | 351,145 | 351,145 | 351,145 | 351,145 |

## Woodcut and glyph review

The woodcut initial region is the source-coordinate rectangle [95, 410, 350, 690] at 300 DPI. Mean RGB error is per channel on 0–255 samples; p99 is the per-pixel mean absolute RGB difference. ΔE is CIE76; ΔC is absolute CIELAB chroma difference. These are matched-geometry PDFium renders, so they also include renderer sampling.

| Comparison | RGB MAE | p99 pixel RGB difference | mean ΔE | p99 ΔE | mean absolute ΔC |
|---|---:|---:|---:|---:|---:|
| C-prime versus main | 0.170 | 3.333 | 0.135 | 4.272 | 0.070 |
| Main versus source | 15.031 | 46.667 | 14.773 | 46.926 | 9.013 |
| C-prime versus source | 14.977 | 46.000 | 14.759 | 46.618 | 9.009 |

The source has sharper coloured boundaries and engraved strokes than both main and C-prime. In this region C-prime versus main changes 1509 of 71,400 pixels; the 99th-percentile maximum-channel difference is 6 levels. The changed pixels are confined to source coordinates [190, 478, 229, 530], where main paints a paper-coloured glyph over the ornament; C-prime restores underlying ornament, with local JPEG and edge differences as well. No meaningful additional lost woodcut feature relative to main was identified during engineering inspection, though this is a visual judgment requiring independent review. [Reading size](/data/coding/scanweave/qualification/acr06/local/ink37c/cprime/woodcut/woodcut-0.32x.png), [300 DPI](/data/coding/scanweave/qualification/acr06/local/ink37c/cprime/woodcut/woodcut-1x.png), [4×](/data/coding/scanweave/qualification/acr06/local/ink37c/cprime/woodcut/woodcut-4x.png), and [difference heat map](/data/coding/scanweave/qualification/acr06/local/ink37c/cprime/woodcut/main-vs-cprime-heat-x4.png); scales and hashes are in [woodcut.json](woodcut.json).

The [panel index](panel-final-index.json) identifies and hashes all 65 glyph locations, named Chicken, Nos, quod, ingenui and ad, and three whole-page sheets. The [panels](/data/coding/scanweave/qualification/acr06/local/ink37c/cprime/panels-final/) show source / main / lossless / C-prime at reading-size approximation, 300 DPI and 4× nearest-neighbour enlargement. The engineer inspected the corresponding byte-identical earlier all-compact output; visible counters, punctuation and Fraktur strokes are readable in the reviewed locations, with expected compact-image softening. These are not pixel-exact to source and this assessment is subject to Claude’s independent review. The supporting Tesseract word-sequence agreement for main versus C-prime is 0.890, 0.810 and 0.955 on the three pages; source versus main and C-prime on historical p5 is 0.567 and 0.568 respectively. OCR is imperfect on this source and cannot alone establish visual loss, but the differences are an uncertainty ([OCR measurements](ocr.json)).

## Other pages, resources, semantics

The 29 non-routed pages have zero changed pixels relative to main in PDFium, Poppler and MuPDF at 96 and 300 DPI. Full per-page results: [PDFium](render-pdfium.json), [Poppler](render-poppler.json), [MuPDF](render-mupdf.json). [Text modes](text-modes-final.json) confirm zero visible text shows on each routed page, so none of the 65 paper-coloured vector glyphs is painted.

PDFium and Poppler extraction and PDFium search are compared against main per page in [semantics-final.json](semantics-final.json). [Donors and reconstruction](donors.json) match the #38 route. [Font, CID-to-GID, widths and ToUnicode comparisons against main](cids-main.json), plus [resource hashes against main](resources-main.json) and [against #38](resources-final.json), record the structural differences. Against main, the only changed named page resource is `/Im0` on historical 2, historical 5 and receipts 4: each becomes a compact encoding of the full source instead of the cleaned residual. Those three content streams also change to suppress visible vectors and preserve invisible text. All font, CID-to-GID, width and ToUnicode comparisons match; all other named resources match. The seven inverted no-vector pages do not route.

The receipts q3 run has identical content streams on all ten pages; only page 4’s encoded image resource differs from #38 ([q3.json](q3.json)). All five faithful-mode outputs are compared byte for byte with #38; qpdf and OTS outcomes are in [pdf-checks-final.json](pdf-checks-final.json). Original inputs use Flate image streams rather than verified source JPEG passthrough, which was larger than the recompressed lossless fallback ([prior passthrough measurements](../passthrough.json)).

## Runtime and memory

Complete-document `/usr/bin/time -v` wall times and peak RSS for A, B, C and C-prime are in [runtime.json](runtime.json). Runs overlapped other work, so these are observations rather than controlled performance benchmarks.

## Gates and review

`cargo test --workspace --locked`, requested Clippy with `-D warnings`, and all 20 Python CI gates passed. Focused tests cover compact routing, retained destructive fallback and coloured artwork without the rejected veto. Local changed-line LLVM coverage is 191/206 (92.7%) ([coverage-new.json](coverage-new.json)); this is an approximation, not the hosted Sonar metric. Local CodeRabbit reviewed the change with no findings.

Before the update, Sonar PR #39 reported `rust:S3776` at 32 versus 30 ([sonar-before.json](sonar-before.json)); its flow assigns 15 points to the removed veto, giving an estimated 17 for the remaining function. The post-push issue is closed ([sonar-after.json](sonar-after.json)), and the hosted Sonar quality gate passed with 92.9% new-code coverage ([sonar-gate.json](sonar-gate.json)). Hosted Rust, Python, publication hygiene and GitGuardian checks passed. The hosted CodeRabbit check skipped on the draft; the local CodeRabbit review completed with no findings. PR #39 remains draft as explicitly instructed; no PR was opened, merged or changed to ready. Claude has not yet independently reviewed this candidate.

Product implementation commit: `af76404` on `exp/ink37-compact-raster`.
