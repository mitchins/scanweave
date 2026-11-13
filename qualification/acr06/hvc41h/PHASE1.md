# HVC-41H Phase 1 — background recomposition economics

HVC-41G is recorded as a PASS for the standalone historical-vector representation in Claude's [disposition](../hvc41g/DISPOSITION.md), commit `af1dab1`. The research code is commit `8c96b6a`. This study measures the background economics only. It does not build a composed PDF or assess a vector/background composite.

The unmodified encoder control reproduces #39's embedded p1 JPEG **byte-for-byte**. Removing the frozen 38 owned footprints before downsampling saves **2,886 bytes** of JPEG data; the conservative native-resolution edit makes the JPEG **421 bytes larger**. The existing vector Form and estimated invocation/structure cost is **59,473 bytes**, excluding patches. These measurements and the residual ink below are available for Claude to decide whether Phase D is economically promising; no Phase D PDF was built.

## Encoding control

For this p1, the existing `convert.rs` branch at `needs_raster_recomposition`/`patches` takes the unmodified `input.rgb` as a whole-page patch when no emitted vector supersedes source ink (around lines 1420 and 1571). The ClearScan whole-page tonal path in `page_pdf.rs` (`whole_page_tonal_candidate` and `assemble_document_impl`, around lines 1287 and 1391) encodes those emitted patch samples. For this page the exact byte reproduction below establishes that the samples are canonical source RGB: there was no text-ink cleanup or inpainting in the encoded p1 image. This is a page-specific finding, not a claim about pages that do emit vectors.

The existing `tonal_image.rs::encode_residual` first evaluates the native compact candidate, then downsamples using `image` 0.25.10 `Lanczos3` to the maximum of 200 DPI without upscaling, and selects the reduced candidate only when it saves at least 5%. For the 1738×2355 RGB source and 416.88×564.96 pt page, the emitted image is 1158×1569. The selected `jpeg-encoder` 0.7.1 path uses Q85, 4:2:0 chroma, optimized Huffman tables and progressive RGB scans; there is no additional colour conversion in our wrapper. The research Rust example invokes the existing `encode_residual` for the control and B-pre. Its B-native branch uses the same pinned `jpeg-encoder` options on the **unencoded** native-resolution samples. We did not recompress the decoded #39 JPEG. All four JPEGs have matching quantisation tables, progressive mode and 4:2:0 sampling; [verification](verification.json) records tool and code hashes.

| JPEG stream | Bytes | SHA-256 |
|---|---:|---|
| Original embedded #39 p1 | 451,336 | `4f5734599b697f9bf6f43522a3e005d08d60b1908cdb03e8428d309af95453a3` |
| Unmodified control | 451,336 | `4f5734599b697f9bf6f43522a3e005d08d60b1908cdb03e8428d309af95453a3` |
| B-pre | 448,450 | `6369e7abd5ce91fdeade4881d67ef554a72023ba54de645809c703d609ec1c81` |
| B-native | 451,757 | `a0d61093a722da67f2b9bbb8f73214f64b47b8da6c96b463a19eb4198152fd7f` |

[Provenance](provenance.json) includes decoder versions and all stream hashes. No quality, chroma or geometry settings were changed.

## Frozen edits and residual ink

The 38 HVC-41G removal masks equal their recorded ownership masks and contain 7,718 distinct source pixels. B-pre changes exactly those 7,718 source pixels and zero others. Each glyph's replacement is the median RGB of the brighter half of a 12-source-pixel annulus, excluding the frozen text-ink reference proxy, all frozen OCR character boxes, recorded artwork components and every owned footprint. This is source-supported local paper evidence; the reference and artwork masks are imperfect proxies and do not prove that every annulus pixel is paper. The independently reviewed masks report zero foreign OCR/artwork ink inside the footprints. The canonical source PNG and input PDF hashes were rechecked unchanged.

For native mapping, an output cell is *any-overlap* if any intersected source pixel belongs to a glyph; this 5,069-pixel union is used for residual and containment accounting. B-native edits only a stricter *fully contained* cell: every intersected source pixel must be owned by that same glyph. It changes 1,817 native pixels, with zero changes outside that strict mask. This conservatism keeps the source ownership boundary but leaves partially covered native cells untouched. [Preparation data](prepared.json) and [native data](native-prepared.json) record each glyph and the source- and native-space guards.

Residual ink is measured on decoded JPEG pixels inside each glyph's any-overlap mapped footprint: a pixel is counted when its Rec.709 luminance is more than 30 below that glyph's source-supported local paper luminance. This is a dark-pixel proxy, not an optical or semantic proof of ghost strokes. Mixed edge cells and nearby unowned ink can contribute. Counts are unique over the union; per-glyph counts sum to the same totals here.

| Background | Dark proxy pixels inside mapped footprints |
|---|---:|
| Original #39 / control | 4,112 |
| B-pre | 65 |
| B-native | 2,261 |

Thus the #39 background does retain substantial dark ink under the 38 proposed footprints. B-pre substantially reduces the proxy but does not make it zero; B-native retains much more. [Ghost data](ghost-ink.json) contains all 38 per-glyph thresholds and counts. The six largest residual cases across either variant are proposals 18, 38, 70, 262, 83 and 140.

## JPEG containment and source-relative appearance

JPEGs were decoded consistently with Pillow 13.0.0/libjpeg 6.2. The table counts decoded RGB pixels changed against the byte-identical control outside the any-overlap native footprint. Both conventional 8×8 blocks and 16×16 4:2:0 MCU footprints are shown. “Beyond” is outside every touched block of the stated size. Maxima are absolute Rec.709 ΔL.

| Variant | Outside total / max ΔL | Within touched 8×8 / max | Beyond touched 8×8 / max | Within touched 16×16 MCU / max | Beyond touched 16×16 MCU / max |
|---|---:|---:|---:|---:|---:|
| B-pre | 21,357 / 41.24 | 9,850 / 41.24 | 11,507 / 18.78 | 19,064 / 41.24 | 2,293 / 14.50 |
| B-native | 15,626 / 32.15 | 8,220 / 32.15 | 7,406 / 1.87 | 14,607 / 32.15 | 1,019 / 1.07 |

The categories in [containment data](containment.json) partition outside pixels separately for each block size. Lanczos filtering before encoding, JPEG blocks and chroma reconstruction can spread decoded differences; the table does not establish which mechanism caused each pixel. Although the source edits themselves do not touch unowned pixels, the decoded JPEG changes are real. Using the nearest-mapped source reference-ink proxy outside the mapped footprints, 28 B-pre pixels and 35 B-native pixels became more than 10 luminance levels lighter than the control, with maxima 20.15 and 23.00 respectively. These are proxy flags for possible neighbouring-ink effects, not a visual judgement or proof of deleted characters.

Whole-page SSIM against the canonical source after Lanczos upsampling is 0.87675 for control, 0.87234 for B-pre and 0.87406 for B-native. The deliberately removed glyph ink lowers these background-only scores, so they must not be interpreted as a completed vector-composite comparison. Outside a four-source-pixel dilation of the owned masks, mean SSIM-map values are 0.87549, 0.87533 and 0.87539 respectively. Definitions and RGB MAE are in [source-relative data](source-relative.json).

The [panel index](panel-index.json) records SHA-256 hashes for six worst-residual five-way crops, the [`alſs` context for 207/208](../local/hvc41h/panels/als-207-208.png), and the [containment map](../local/hvc41h/panels/containment-map.png). Each crop shows source / original #39 background / same-encoder control / B-pre / B-native, at 4× nearest-neighbour. Background JPEG samples are nearest-neighbour mapped to source geometry before enlargement. The panels show that B-native leaves dark contours at the conservative cell boundary; B-pre is much cleaner by the proxy but still has some dark residual pixels. No vector overlay is present in these images.

## Economics and projection

The compact A3 cost from HVC-41G is 59,174 compressed Form bytes + 29 invocation bytes + 270 bytes of observed structure, or **59,473 bytes** excluding paper patches. The structure figure is an estimate when the PDF is reassembled without patches. Predicted document sizes below substitute the actual variant JPEG byte count into the #39 PDF and add that vector estimate. They are **not actual completed-PDF measurements**: Phase D composition is explicitly outside this run.

| Item | Bytes |
|---|---:|
| #39 historical PDF | 2,247,390 |
| Original #39 p1 JPEG / control | 451,336 / 451,336 |
| B-pre JPEG; image saving | 448,450; **2,886 saved** |
| B-native JPEG; image saving | 451,757; **−421** (growth) |
| A3 Form + invocation + estimated structure | 59,473 |
| B-pre predicted complete PDF / net change | 2,303,977 / **+56,587** |
| B-native predicted complete PDF / net change | 2,307,284 / **+59,894** |

B-pre reaches 4.85% of the measured 59,473-byte break-even. The 38 source masks contain 7,695 pixels in the frozen source-reference ink proxy, giving **0.375 JPEG bytes saved per owned reference-ink pixel** for B-pre. The strictly native-owned cells cover 5,802 source-reference pixels, giving **−0.073 bytes per such pixel** for B-native. These denominators describe removal footprints; the HVC-41G actually rendered vectors overlap 7,654 / 208,768 reference pixels, or 3.666%. They are not the same measurement.

As a deliberately simple extrapolation, hold the observed 0.375-byte saving per source-reference pixel, the current average reference-ink area per glyph, and the **1,565-byte vector cost per glyph** constant. Scaling the 7,695 owned reference pixels to the full 208,768-pixel proxy implies roughly 1,031 similar glyphs, 78 KB of image savings and 1.61 MB of vector cost, or roughly **+1.54 MB** before other overhead. This assumes uniform glyph density, independent marginal JPEG savings and no reuse, none of which is established. If the existing vector cost could somehow stay fixed while coverage increased, about 158,574 similarly productive ink pixels would be needed to offset it; that assumption ignores the cost of adding glyphs and is not a realistic measurement. The observed per-glyph saving is about 76 bytes against about 1,565 bytes of vector cost. The results therefore do not demonstrate a plausible compression-positive scaling of this representation under the stated assumptions. Broader coverage or different architectures would require separate authorisation; this run does not change quality or geometry to pursue them.

## Guards and stop point

The frozen ledger, HVC-41G PDF and #39 baseline hashes were checked before processing. The seven research entry-point switch checks failed closed as expected ([guard tests](guard-tests.json)); the release encoder example built with `cargo build --release --locked -p scanweave-io --example hvc41h_encoder`. The source input PDF and canonical PNG remain unchanged; all source modifications are inside the 38 verified ownership masks. The preparation, encoding, measurement, panel, verification and corpus-replay jobs used a failing Tesseract stub first in PATH; no invocation was observed. A few read-only Python inspections of the PDF, image metadata and sidecar were run outside that stub wrapper; their code only read those artifacts and did not invoke OCR. With research switches off, the fresh [32-page replay](default-replay.json) matches `ab7dfba` byte-for-byte. No composed PDF, new OCR, product-default change, PR, merge or release was made. The JPEG experiments stop here for Claude's economics review.
