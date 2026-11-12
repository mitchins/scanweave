# HVC-41F Phase 2 — HOLD: Type 3 text leaks into extraction

**The completed 38-glyph trial is not a qualified final PDF.** It adds control characters to PDFium and Poppler extraction on historical p1. The original OCR content stream, fonts, CID/ToUnicode resources and image streams remain unchanged, but the new Type 3 text shows inside a Form are themselves extracted. This violates the unchanged-semantics and no-additional-copied-text requirements. No product change or PR was made. The research diagnostics and corrected fail-closed guard are at commit `f091a63`.

The correct choice under the requested A4 decision rule is **A3 path-only**, because A4 fails with the frozen 38-glyph font codes. The one permitted final assembly has already been used for A4. Switching to A3 would require another final assembly, whereas the authorised rebuild is for dropping failing glyphs. No such representation-changing rebuild was made. The earlier A3/B1 size-measurement PDF remains a separately labelled diagnostic; it is not relabelled as a final result.

## Why the initial A4 decision was wrong

The first three isolated A4 tests used a one-glyph font where each tested character had code `01`. `/Artifact` preserved extraction there and the renderer checks met the numeric comparison: [initial attempts](a4-attempts.json), [renderer comparisons](a4-render.json). On that evidence the one-shot assembler selected A4. The assumption did not hold for the actual 38-glyph font. Its reviewed proposals 18, 38 and 243 use codes `01`, `04` and `23` respectively, with the complete frozen font and encoding.

A corrected isolated test copied the actual complete font and used those exact codes and placements, while retaining the B1 patches. Its [full results](a4-frozen-codes-attempts.json) are:

| Suppression strategy | PDFium extraction | Poppler extraction | MuPDF extraction | Six PDFium searches |
|---|---|---|---|---|
| `/Artifact` | changed on all 3 | changed on all 3 | changed on all 3 | same on all 3 |
| Empty `/ActualText` | changed on all 3 | same on all 3 | same on all 3 | same on all 3 |
| No ToUnicode | changed on all 3 | changed on all 3 | changed on all 3 | same on all 3 |

The third method was also checked with an intentionally unmapped glyph name and no ToUnicode: [explicit unmapped results](a4-unmapped-attempt.json). It still changed PDFium, Poppler and MuPDF extraction for all three. No fourth suppression strategy was attempted. The original selection was a test-design defect, not a valid demonstration that A4 passed. After discovering it, the research assembly script was given an additional frozen-code extraction guard; running that guard now fails closed before assembly.

The composed trial confirms the defect. PDFium p1 extraction increases from 1,110 to 1,214 characters, and Poppler p1 from 1,112 to 1,159. The differences are inserted control characters and line breaks; the original extracted content remains in sequence, but the additional copied text is a failure. Exact offsets and Unicode code points are in [semantic differences](final-semantic-differences.json). Pages 2–5 have identical extraction in both engines. `Bacharias` and six additional PDFium searches have identical hit lists; that does not excuse the extraction failure. Full native checks and original-resource hashes are in [semantics](final-semantics.json).

## Visual and ownership evidence for the rejected trial

The numerical frozen validator passed each of 38 actual completed-font glyphs, and the per-glyph source-space `patch & ~owned`, other-glyph foreign reference ink and pairwise overlap counts are zero: [glyph ledger](final-glyphs.json). Two vector masks differ from HVC-41E by 2 and 1 source pixels respectively. The final vectors overlap 7,654 of 208,768 pixels of the frozen source-reference proxy; this is a proxy, not ground-truth ink coverage. Contour counts and the 4× raster component/hole counts before and after C encoding match for all 38 in [assembly data](final-assembly.json); this is not a proof of continuous geometry or a substitute for semantic qualification. No glyph was dropped. Because the page fails extraction, none is claimed as a fully qualified final emitted glyph.

The full five-page PDFs were rendered at 96 and 300 DPI in Splash default, Splash-AA, Cairo, PDFium and MuPDF. Pages 2–5 have zero changed pixels in all ten comparisons against #39. For p1, “inside” is changed pixels within the mapped owned masks; “band” is outside ownership within one 8-connected render pixel; “beyond” is farther away. The HVC-41E columns use the same comparison to #39.

| Renderer | DPI | Trial inside | Trial band | Trial beyond | HVC-41E band | HVC-41E beyond |
|---|---:|---:|---:|---:|---:|---:|
| Splash default | 96 | 806 | 744 | 4 | 989 | 45 |
| Splash-AA | 96 | 806 | 744 | 4 | 989 | 45 |
| Cairo | 96 | 805 | 767 | 9 | 786 | 3 |
| PDFium | 96 | 806 | 743 | 1 | 753 | 1 |
| MuPDF | 96 | 805 | 699 | 3 | 716 | 5 |
| Splash default | 300 | 7,717 | 2,559 | 0 | 3,216 | 167 |
| Splash-AA | 300 | 7,717 | 2,559 | 0 | 3,216 | 167 |
| Cairo | 300 | 7,718 | 2,804 | 0 | 2,799 | 0 |
| PDFium | 300 | 7,718 | 1,105 | 0 | 1,105 | 0 |
| MuPDF | 300 | 7,717 | 2,550 | 0 | 2,545 | 0 |

[Renderer data](final-render.json) list every beyond-band pixel with coordinates and signed luminance delta; they are not automatically judged harmless. The local median B1 patch retains a paper-tone discontinuity, documented in [Phase 1](PHASE1.md). [HOLD-labelled panels](final-panel-index.json) include the whole page, four line strips, the 38-glyph contact sheet and six worst boundary grids. These are images of the rejected trial, not evidence of semantic acceptance.

## Structure, bytes and safeguards

Original page image stream bytes, original raw and decoded content streams, ToUnicode, CID mappings and original TrueType font signatures match #39 on all five pages. `/ActualText` remains in the identical original streams; donors were not rebuilt. `qpdf --check` and OTS on the original TrueType passed. `pdffonts` reports the original embedded CID TrueType and a separate embedded Type 3 research font; OTS is not applicable to Type 3 charprocs. The additional Type 3 text shows are the semantic failure despite those unchanged resources.

The failed trial PDF is 2,326,582 bytes, SHA-256 `a327845e4665935df26f9eb8b63b7000ab069235d9fd1db9bd2abbfb600525cc`, compared with #39's 2,247,390 bytes: **+79,192 bytes**. The delta is 62,268 compressed font/Form bytes, 12,589 compressed patch bytes, 29 invocation-stream bytes, and 4,306 structural/serialization bytes. Assembly took 1.79 s wall and 263,776 KiB peak RSS, using existing frozen artifacts. Append-only overlays cannot deliver net source-raster compression.

The frozen ledger SHA-256 `391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef`, HVC-41E PDF and baseline hashes were checked before assembly. OCR remained locked with a failing Tesseract stub; no invocation was observed. With research switches off, the [fresh 32-page replay](final-default-replay.json) is byte-identical to `ab7dfba`. No thresholds, ownership masks, source placement, paper/ink decisions or donor logic were altered.

**Disposition:** HOLD. An A3-based final assembly needs separate authorisation because this run's one assembly has already occurred and the requested A4 selection test was unsound. The Phase 1 A3/B1 size-only evidence supports that next evaluation, but cannot stand in for a new final qualification.
