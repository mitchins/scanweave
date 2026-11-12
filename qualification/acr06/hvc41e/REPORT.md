# HVC-41E: composed historical p1 research trial

**Research result, not a product qualification.** The single assembly emitted all 38 glyphs independently accepted by Claude; no neighbour interaction was found and no rebuild was made. The composed embedded-font masks cover **7,655 / 208,768 = 3.667%** of the frozen page-level reference-ink proxy. The unchanged semantic layer and the 29 other corpus pages pass the checks below. The new glyphs have visibly flatter colour and sharper edges than the scan at enlargement, and Poppler has outside-footprint darkening beyond the one-pixel boundary; these differences require continued visual and renderer investigation. They must not be described as source-exact.

The baseline was #39 at `ab7dfba`. The research assembly runner is commit `529617e` on `research/hvc41-feasibility`; it is not a product change. The independent ledger at `fbf6714` was checked against SHA-256 `391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef` before the one-shot assembly. The runner validates the frozen OCR, canonical source and baseline hashes, requires the HVC-41E switch and ownership checks, and refuses a second assembly. Its original Type 3 visual overlay and clipped paper patches preserve baseline streams and semantics. No thresholds, proposal pool, or donor decisions were changed. There was no fresh OCR.

## Outcomes E1–E7

1. Of 54 numerically passing proposals, Claude accepted **38** and rejected **16**, with individual reasons in [the frozen ledger](review-decisions.json).
2. All **38** passed the owned-mask clipping and ownership guards: `patch & ~owned = 0` for every glyph.
3. All **38** survived composition: no accepted patch/vector intersected another accepted glyph's reference ink, no patch/patch, vector/vector, patch/vector or vector/patch overlap was measured, and each font mask agreed with its single-glyph trial. No composition interaction justified a drop or rebuild. See [composition checks](composition-check.json) and [halo checks](halo-composition.json).
4. **38** actual embedded Type 3 glyph visuals are emitted. Their per-glyph independent decisions, final frozen checks, measurements and panel references are joined in [the final ledger](final-glyph-ledger.json). Individual review occurred on single-glyph trials; final composition was inspected using the panels, and the recorded measurements are not a substitute for an additional independent review of the completed page.
5. The deduplicated overlap of the completed-font vectors with the page-level source reference proxy is **7,655 pixels**, or **3.667%** of 208,768. This is a proxy for recovered text ink, not a count of independently labelled true ink. The proxy can include artwork and noise and omit faded text; overlaps do not establish perfect placement, legibility, or an absence of halos.
6. The earlier **9,930** is the sum of `ref_pixels` for 54 independently constructed *local glyph reference masks* in [HVC-41D's coverage diagnostic](../hvc41d/p1-coverage-diagnostic.json); it is not a deduplicated global coverage measurement. **10,285** is the union of the 54 single-glyph trial vector masks intersected with the *global page reference proxy*. They use different masks and operations. Neither is this run's 38-glyph final coverage.
7. No semantic, unchanged-page rendering or detected foreign-ink deletion regression was found by these checks. Flattened glyph tone, changed edge shape and the outside-footprint renderer differences below remain visible/quantified limitations. The document grows by **273,611 bytes**.

The source-reference proxy and the frozen metrics are deliberately retained, not tuned for these glyphs. The measured neighbourhood “ghost ink” is 10–92 pixels per glyph; it counts nearby reference ink touching the vector and is not by itself proof of an actual doubled stroke, because nearby legitimate marks are included. Under-replaced pixels range 0–15. Paper-ring mean absolute luminance difference ranges 11.07–15.35 (maximum individual delta up to 36.31). These were present in the reviewed single-glyph trials and do not worsen due to neighbours. They are recorded per glyph rather than silently called zero.

## Rendering and ownership

All five pages were rendered at 96 and 300 DPI with PDFium, Poppler and MuPDF. Pages 2–5 have **zero changed pixels** in all six comparisons with #39. The p1 table compares baseline to candidate. Ownership is mapped from source to rendered pixels; “boundary” means outside the mapped owned footprint but within one 8-connected render pixel of it. “Other” is everything farther away. These are geometric classifications, not a finding that all boundary changes are harmless. Luminance delta is candidate minus baseline in Rec.709 units.

| Engine | DPI | All changed | Outside: boundary | Outside: other | Boundary ΔL range | Other ΔL range |
|---|---:|---:|---:|---:|---:|---:|
| PDFium | 96 | 1,560 | 753 | 1 | −36.35 to +4.78 | −7.72 |
| Poppler | 96 | 1,840 | 989 | 45 | −150.0 to +86.8 | −56.00 to −1.00 |
| MuPDF | 96 | 1,527 | 716 | 5 | −62.6 to +20.8 | −6.72 to −0.93 |
| PDFium | 300 | 8,822 | 1,105 | 0 | −62.9 to −1.0 | — |
| Poppler | 300 | 11,101 | 3,216 | 167 | −145.9 to +79.4 | −91.56 to −2.00 |
| MuPDF | 300 | 10,262 | 2,545 | 0 | −70.8 to +40.4 | — |

Every outside pixel, with coordinates and signed luminance delta, is listed in `outside-pixels-{pdfium,poppler,mupdf}-{96,300}.json`; the [render results](render-phase2.json) contain the paths and hashes. All “other” deltas are darkening, not proof of deleted foreign ink. In the enlarged Poppler crops red marks identify pixels beyond the one-pixel band; they occur along glyph outlines. The magnitude and spatial distribution mean that they should not simply be dismissed as antialiasing. Source-pixel patch ownership remains exact; renderer behavior is a separate measurement.

The [panel index](final-panel-index.json) records SHA-256 hashes for the [whole-page reading-size comparison](../local/hvc41e/final/panels/whole-page-96.png), four line strips, each of the 38 final composed glyph panels, six largest-difference boundary crops, and the [16 rejected glyph contact sheet](../local/hvc41e/final/panels/rejected-contact-sheet.png). Five additional composed-glyph contact sheets are listed in [their index](composed-review-index.json). The panels use actual completed PDF renders. Labels are separate from images. Source/baseline/candidate enlarged comparisons show that the contours are recognisable but the single-colour replacement loses some scanned texture and tonal variation; this is an appearance change even where the character remains readable.

## Semantics, resources and checks

PDFium and Poppler extraction is byte-identical to baseline on all five historical pages. PDFium search hit lists match for `Bacharias`, `Boect!`, `Wud`, `Dat`, `fram`, and `Ber)` (the latter five are frozen OCR strings associated with accepted words, not claims that OCR labels are correct). The Type 3 pattern adds no extracted text. Original raw and decoded content streams, image stream bytes, original font program, ToUnicode and CID mapping signatures match on every page; `/ActualText` is in the unchanged original content. The overlay adds a separate Type 3 font and visual streams, without rebuilding donors. `qpdf --check` passed; `pdffonts` reports the embedded Type 3 and original embedded CID TrueType. OTS passes the original TrueType; OTS is not applicable to Type 3 charprocs. Detailed hashes, search hits and check outputs are in [semantic and resource results](semantic-phase2.json).

With research switches off, the OCR-locked replay produced byte-identical complete PDFs for **all 32 pages** in the five documents; [document hashes, time and RSS](default-replay-phase2.json). The failing Tesseract stub was first on PATH and was not invoked; the runner also requires matching frozen OCR sidecars. Clipping tests (4), ownership tests (3), and six OCR-lock negative cases passed. The Phase 1 clipping/foreign-ink tests and [Phase 1 report](PHASE1.md) remain applicable.

## Bytes, timing and disposition

| Document | #39 bytes | Trial bytes | Δ bytes |
|---|---:|---:|---:|
| Historical, 5 pages | 2,247,390 | 2,521,001 | +273,611 |
| 32-page corpus, sum of complete PDFs | 8,108,979 | 8,382,590 | +273,611 |

Of the increase, 269,204 bytes are new raw PDF streams (Type 3 glyph charprocs, pattern, patches, and invocation); 4,407 bytes are other objects/serialization. Patch data are 83,795 decoded bytes. The measured one-shot assembly took **0.57 s wall**, peak RSS **111,532 KiB**; it reused the existing baseline and frozen research data, so this is not end-to-end conversion runtime. The default OCR-locked historical conversion took 1:03.46 and 740,936 KiB peak RSS; the other document measurements are in the replay JSON. The completed PDF SHA-256 is `9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0`.

This establishes a bounded multi-glyph overlay research demonstration with unchanged text resources and no detected inter-glyph interactions, not production readiness or source-identical appearance. A next separately authorised architectural experiment should investigate source-appearance preservation and Poppler's outside-footprint edge darkening while retaining the isolated baseline streams and independent ownership/semantic checks; it should also address the considerable per-glyph font overhead. No p3/p4 expansion or product-default change is proposed here.
