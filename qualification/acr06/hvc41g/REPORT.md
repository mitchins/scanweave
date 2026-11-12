# HVC-41G — 38-glyph path-only research evidence

This report records the completed A3/B1/C research PDF and measurements for Claude's independent visual disposition. The visible glyphs are ordinary Bézier graphics in a Form XObject, **not embedded-font glyphs**. The existing invisible OCR layer remains the semantic owner. No cross-glyph deduplication, production-default change, or new glyph was introduced. The research code is commit `fb7c8c0`.

## Frozen representation and preflight

The preflight built the complete five-page historical PDF from the 38 independently reviewed HVC-41E proposals. It checked ledger SHA-256 `391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef`, the #39 baseline and HVC-41E hashes, frozen OCR sidecar, source dimensions and pixel hashes, every glyph's outline, identity, matrix, fill and owned mask. The complete PDF's actual Form stream was compared byte-for-byte with the 38 regenerated frozen path commands. Its three new streams were tokenised: none contains `BT`, `ET`, `Tj`, `TJ`, quote, double quote or `Tf`; the new Form has no resources or Font dictionary, and no page Font resource was added.

On the **complete PDF**, PDFium, Poppler with and without `-layout`, and MuPDF extraction matched #39 on every page. PDFium search hits matched for `Bacharias`, the six earlier queries and every distinct nonempty frozen OCR word containing an accepted glyph: 24 distinct queries in total, including any with zero hits. [Preflight data](preflight.json) record page hashes, all queries and results, token sets and each glyph's frozen data.

After preflight, the exact tested file was copied and hash-checked as the frozen qualification input. Its SHA-256 is `e408daab686fd47f05451627620a79dc8770e5c299654eba4f76bb5454ef7a4b`; the concatenated decoded patch, invocation and Form streams hash to `bc952bbfb07715c2508f253ef00cc413311bc1ee4622721639a54fbde7a04fe2`. The one-shot qualification marker records both hashes, and qualification scripts check them. The first render-script invocation encountered a variable-name collision **before** the marker was created or any qualification render ran; after that engineering error was corrected, one guarded qualification render was run. The frozen PDF was not rebuilt.

The builder generated the patch path directly from the validated owned masks. As an additional independent qualification check, [patch verification](qualification-patches.json) reconstructs all 38 source-cell union paths and local paper colours from the frozen masks and recorded B1 samples, and confirms byte-for-byte equality with the actual frozen patch stream. This explicit stream reconstruction was run after the qualification marker, rather than as a separate preflight assertion; the preflight had already bound the builder's exact PDF bytes and checked each mask. No patch pixel lies outside ownership. The frozen individual review reports zero other-OCR and artwork reference-ink pixels covered, and the actual composed-vector check finds zero other accepted-glyph reference-ink intersections.

## Glyphs, geometry and paper

All 38 actual Form paths pass the frozen numerical glyph validator. The [joined glyph ledger](glyph-ledger.json) contains the independent identity decisions, exact masks, topology, actual vector measurements, ghost and under-replacement proxies, and per-renderer halo values. The 38 final paths overlap 7,654 of 208,768 pixels in the frozen source text-ink reference proxy (3.666%). This proxy may include non-text or miss faded ink; it is not ground-truth coverage. Two actual PDFium vector masks differ from HVC-41E by 2 and 1 source pixels. No patch/patch, vector/vector, cross-glyph patch/vector, or other accepted-glyph reference-ink intersection was measured.

C retains the previously accepted 0.001-font-unit quantisation and ≤0.01-source-pixel control-hull line replacement. All 38 retain contour counts and 4× raster component/hole counts. The maximum conservative quantisation-plus-simplification bound is 0.011593 source pixel; this raster topology check does not constitute a proof of continuous topology. The [build measurements](preflight-build.json) include per-glyph sampled errors and component/hole counts.

B1 uses a locally sampled median from the decoded #39 background; it remains a flat fill within each exact owned-mask patch. Patch-only renders give the following mean of the 38 glyphs' mean absolute boundary-to-nearby-paper ΔL; the parenthesised value is the largest glyph mean in that engine. The measurement is affected by rendering and mask mapping and is not a standalone visual acceptability decision.

| DPI | Splash-AA | Cairo | PDFium | MuPDF |
|---:|---:|---:|---:|---:|
| 96 | 20.59 (35.49) | 17.93 (25.45) | 18.14 (25.28) | 21.29 (35.25) |
| 300 | 14.63 (23.53) | 19.82 (24.97) | 6.79 (10.30) | 19.87 (25.30) |

All 380 engine/resolution/glyph measurements, sample counts and signed values are in [halo evidence](qualification-halo.json). The contact sheet and grids show more uniform glyph fill than the scanned source in several enlarged examples. The residual paper-tone differences and their visual significance are left to independent review.

## Completed-page rendering

The frozen PDF was rendered at 96 and 300 DPI in Splash default, Splash-AA, Cairo, PDFium and MuPDF. Historical pages 2–5 had zero changed pixels against #39 in all ten combinations. For p1, “inside” counts changed pixels within the mapped ownership mask; “band” is outside it within one 8-connected render pixel; “beyond” is farther away. HVC-41E and the failed HVC-41F Type 3 trial were rendered with the same settings and compared with #39.

| Renderer | DPI | G inside | G band | G beyond | E band / beyond | F band / beyond |
|---|---:|---:|---:|---:|---:|---:|
| Splash default | 96 | 806 | 746 | 4 | 989 / 45 | 744 / 4 |
| Splash-AA | 96 | 806 | 746 | 4 | 989 / 45 | 744 / 4 |
| Cairo | 96 | 805 | 697 | 2 | 786 / 3 | 767 / 9 |
| PDFium | 96 | 806 | 745 | 1 | 753 / 1 | 743 / 1 |
| MuPDF | 96 | 805 | 699 | 3 | 716 / 5 | 699 / 3 |
| Splash default | 300 | 7,717 | 2,562 | 0 | 3,216 / 167 | 2,559 / 0 |
| Splash-AA | 300 | 7,717 | 2,562 | 0 | 3,216 / 167 | 2,559 / 0 |
| Cairo | 300 | 7,717 | 2,566 | 0 | 2,799 / 0 | 2,804 / 0 |
| PDFium | 300 | 7,718 | 1,135 | 0 | 1,105 / 0 | 1,105 / 0 |
| MuPDF | 300 | 7,717 | 2,547 | 0 | 2,545 / 0 | 2,550 / 0 |

[Renderer evidence](qualification-render.json) enumerates every beyond-band pixel for G, E and F with zero-based coordinates, signed Rec.709 ΔL and nearest owned glyph. The likely cause is noted as renderer edge sampling near that glyph; the exact mechanism is not proven, and the exceptions are not pre-judged. The [panel index](panel-index.json) includes hashes for the [whole-page reading-size comparison](../local/hvc41g/panels/whole-page-96.png), the four matching HVC-41E line contexts, the [38-glyph 2× nearest-neighbour context sheet](../local/hvc41g/panels/all-38-context.png), six worst halo grids and six worst beyond-band grids. Halo ranking uses each glyph's largest 300-DPI mean absolute boundary-to-ring ΔL among the four engines; beyond ranking counts nearest-glyph exceptions across those engines and both resolutions, breaking ties by halo. Yellow marks the band and red marks beyond-band pixels. All 38 contexts were inspected for presentation and are provided for Claude's individual visual review.

## Resources, semantics and cost

[Structure evidence](qualification-structure.json) confirms matching original raw and decoded content streams, source image stream bytes, original font program, CID mapping and ToUnicode signatures on all five pages. `/ActualText` remains in the unchanged original streams. No donor reconstruction or donor collection was run. `qpdf --check` and OTS on the original embedded TrueType passed; the new Form has no font to run through OTS. The exact-mask contour, clipping and ownership guard test suites passed ([test output](tests.json)). No OCR invocation was observed with a failing Tesseract stub first in PATH. The fresh [research-disabled replay](default-replay.json) produced byte-identical complete PDFs for all 32 pages.

| Complete historical PDF | Bytes | Increase vs #39 |
|---|---:|---:|
| #39 baseline | 2,247,390 | — |
| HVC-41G frozen PDF | 2,319,452 | 72,062 |

The delta comprises 59,174 compressed Form bytes, 12,589 compressed patch bytes, 29 invocation bytes and 270 structural/serialization bytes. The measured preflight build took 2.46 s wall and 261,008 KiB peak RSS while reusing frozen source and OCR data; this is not full conversion runtime. The [PDF](../local/hvc41g/historical-frozen.pdf) is a local research artifact. Append-only overlays cannot deliver net source-raster compression.

No final visual disposition is made here. The 96-DPI beyond-band pixels and the B1 paper-tone measurements remain explicitly available for Claude's review.
