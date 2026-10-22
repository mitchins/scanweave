# ACR-02 — Adobe anatomy and clean recomposition

22 October2026. Branch `product/acr02-clean-recomposition`, from verified ACR-01
`8f14cd329493ad0cc226e480d152d7a464fb4731`. Remote product main remains `0ca94ae`;
PR15 is open/green, not merged. PR14 is evidence only and remains unmerged.

**Outcome: useful Adobe anatomy; working derivative prototypes; no production
promotion.** The smaller representation introduces invented artwork structure
and colour/texture defects. This is a measured representation failure, not a
pixel-exact preservation veto. Production, faithful, fonts and OCR are unchanged.

## 1. Anatomy gate

[ADOBE_ANATOMY.md](ADOBE_ANATOMY.md) identifies exact emitted objects, codecs,
resolutions, coloured font paint, mixed raster/path rules and overlap handling.
All36 controlled Adobe pages have resource inventories and both-renderer ablations.
Ordered replay is pixel-identical on all36 in each renderer. Selected genuine
historical, form/signature and illustrated/Linn pages have additional ablations.

The important result is **selective object crops plus fonts and paper**, not a
universal MRC model. Most new pages use150DPI JPEG paper and300DPI visual crops;
shaded statement pages retain full300DPI images. Real frozen pages also contain
inline1-bit stencils. Adobe keeps printed ink crossing annotations inside the
same native raster region where font-only views have gaps.

## 2. Prototype design and boundaries

Both prototypes reuse the complete normal ScanWeave PDF's reconstructed fonts,
placement, invisible semantic owners and Unicode. These are **temporary derivative
PDF experiments**, not new public modes or an ordinary-converter implementation.
They use conventional Form/image/SMask resources, not a replacement PDF engine.
The experiment first renders the already-cleaned non-font page at300DPI, then:

1. Estimates paper with a31px channel maximum filter and Gaussian sigma8.
2. Derives normalized source coverage and foreground colour from that paper.
3. Stores paper at75DPI, foreground colour at150DPI and coverage at300DPI.
4. Retains original text operations over those recomposed resources.

The first setting uses native8-bit coverage and JPEG85 foreground. The smaller
setting uses16 coverage levels (still stored8-bit, Flate/PNG-Up) and16-colour
Indexed foreground (8-bit indices, Flate/PNG-Up). No OCR labels, pristine font,
paired evaluator paper or annotation truth enters paper/coverage estimation.

Early no-predictor variants and a JPEG/C16 control are retained locally; the final
code and accounting identify the selected reproducible outputs. Removing unused
original image resources is essential: clipping/replacing paint without dropping
unreferenced resource entries did not save their stored bytes.

### Matched document context

The anatomy fixture has36 unique pages. A full36-page ScanWeave run completed OCR
but was stopped after **905.46s /689,136KiB** without a PDF; no result or causal
runtime attribution is fabricated for that run.

The explicitly named four-page prototype document contains flat-logo/white,
photo-logo/annotation, statement/white and statement/annotation. **All four pages
were converted together by both ordinary ScanWeave and Adobe**, preserving that
document's donor context. It is not a selected-page result claimed for the36-page
run. Existing real historical and financial documents remain their full original
five/13-page collections, with their existing ACR-01 document-wide font dictionaries.

## 3. Actual complete-PDF results

| Document/representation | Complete bytes | Versus ACR-01 |
|---|---:|---:|
| Four-page image-only input | 658,396 | — |
| Matched Adobe ClearScan | 144,913 | — |
| ACR-01 normal four-page CLI | 431,287 | baseline |
| Recomposition: coverage256/JPEG | 743,860 | 72.48% larger |
| Recomposition: coverage16/Indexed16 | **392,624** | **8.96% smaller** |
| Historical ACR-01, five pages | 5,114,421 | baseline |
| Historical coverage256/JPEG, pages1/2/4 changed | 9,866,686 | 92.92% larger |
| Historical coverage16/Indexed16, pages1/2/4 changed | 5,638,094 | 10.24% larger |
| Financial ACR-01, all13 pages | 9,018,954 | baseline |
| Financial coverage16/Indexed16, all13 changed | **6,912,445** | **23.36% smaller** |
| Frozen financial OCRmyPDF-O3 | 5,166,004 | comparator |
| Frozen financial Adobe | 718,276 | comparator |

The earlier7,142,992-byte financial trial changed12 of13 pages, retaining page12
unchanged. The final6,912,445-byte run recomposes **all13**, preserves all13 pages
and is the collection result above. Single-page interventions also preserve the
full original document. All exact output SHA-256 values are in the versioned CSV.

### Encoded streams, not image-area estimates

| Four-page output | Raster bytes | Font-program bytes | Other streams + serialized remainder |
|---|---:|---:|---:|
| Adobe | 101,446 | 17,698 | 25,769 |
| ACR-01 | 382,124 | 15,030 | 34,133 |
| Coverage256/JPEG | 703,350 | 15,030 | 25,480 |
| Coverage16/Indexed16 | 351,350 | 15,030 | 26,244 |

The smaller prototype has12 image resources: three per page (paper, foreground
colour, coverage). The financial13-page prototype has39 images and5,661,984 encoded
raster bytes; fonts remain1,065,434 B. `qualification/acr02/byte-accounting.csv`
records every measured PDF. **Coverage/foreground include unreconstructed printed
text**, not merely non-text artwork. No compressed bytes are allocated to semantic
classes by percentage of image area.

## 4. Visual findings and precise failure

Both PDFium and Poppler show the following in fixed physical-coordinate sheets:

- Body amounts, decimal points, references, punctuation, crossing annotations and
  thin table rules remain readable in the inspected four-page regions.
- The smaller prototype invents nested contours/banding inside a uniform blue
  triangle. The higher-precision setting also creates weaker ripple/grid texture.
- On genuine history04, the indexed foreground turns a red seal brown/dark.
  History02 develops white flecks/mottling; history01's ornament/ink edges change.
- Financial figures remain readable in reviewed regions, but circular cleanup
  halos appear around some small background/underline features. A smaller file
  alone is insufficient evidence of an excellent rebuilt page.

**Causal diagnostic:** in the logo prototype, paper image **23 0** contains RGB
(20,85,149) at source pixel(1230,270), while coverage mask **30 0** is **zero** there.
That is the interior of the blue logo, not paper. The31px paper estimator treats
broad foreground colour as illumination; mismatched-resolution paper/colour and
coverage then produce artificial structure. Foreground palette reduction adds
colour damage. This is not repaired by changing the font or further JPEG tuning.

A separate inherited issue is visible: the blue logo's `S` is black already in
ACR-01, whereas source/Adobe keep it blue. The prototypes preserve that existing
font paint; it is **not a new colour regression**. Coloured glyph/object ownership
needs its own targeted correction before claiming general letterhead fidelity.

The tiny image-edge metrics are diagnostic only. Adobe changes MediaBox/CropBox
by fractions of a point; sheets preserve physical coordinates without registration,
not independent glyph normalization. Re-rendering the residual can also change
sampling phase. No page-wide MAE/SSIM threshold decides acceptance.

## 5. Semantics, validation and performance

- Poppler extraction and PDFium native text are **exactly unchanged** for both
  four-page candidates and the final historical/financial candidates.
- Font programs and ToUnicode hashes match their full original ScanWeave documents.
  Existing glyph identity/placement is retained; no donor or reconstruction method
  was modified. Text operators survive; only non-font composition is replaced.
- qpdf validates the four qualified mechanical comparisons. Native searchable
  content equality is not claimed to prove that every newly rendered mark is right.
- Two new ablation tests pass: nested Form/clipping/path separation in both engines,
  and explicit rejection of unsupported text-clipping modes. Source bytes remain
  unchanged. Both-renderer ordered replay passes on all36 controlled Adobe pages.
- All35 frozen input/comparator collection hashes were revalidated unchanged.
  The holdout remains sealed. No production or faithful code changed; established
  ACR-01 outputs are not regenerated or requalified as new product results.

The normal four-page CLI took47.56s,219,008KiB peak RSS. Adobe automation wall time
was81.22s for36 pages and82.26s for the matched four pages, including fixed UI waits;
the wrapper's RSS is **not Acrobat's resident memory**. No speed ranking is inferred.
The final13-page shadow recomposition took27.51s,436,296KiB peak RSS;
it is additional work after normal conversion, not a faster native converter.

## 6. Independent review and decision gates

A separate read-only reviewer inspected actual labelled comparisons in both engines,
including normal pages and enlarged logo, crossing, stamp and numerical regions.
It rejected general integration on visible content grounds, while confirming the
readable amounts/rules and separating the inherited black `S`. A second reviewer
checked code/evidence, font/text equality and geometry limitations. No blocking
mechanical defect was found for this bounded experiment. Reviews remain locally
hash-bound in the manifest; their conclusions are reproduced here.

- **Gate A: passed within the stated fixture/domain limits.** Actual Adobe objects,
  clips, paint order, rules, masks and paper behaviour are documented.
- **Gate B: partial, not a clean mixed-object solution.** Complete searchable PDFs
  with independent resources work, but the “paper” layer wrongly contains broad
  logo content. Emitting three layers is not proof of correct object extraction.
- **Gate C: failed.** Size improves on the financial and controlled documents, but
  invented logo structure, seal-colour damage and halos defeat the quality frontier.
- **Production integration: rejected.** ACR-01 remains the normal fallback/product;
  no new profile, codec architecture or unqualified compositor is shipped.

The full32-page corpus is **not rerun**, because the representative visual gate
failed. Its current product result remains18,556,766 B. The6.91MB financial shadow
is1.34× OCRmyPDF-O3 and9.62× Adobe on that collection; it is not a qualified product
improvement. We do not extrapolate a new32-page total.

## 7. What remains between ScanWeave and Adobe

With identical ScanWeave fonts/semantics, recomposition can reduce financial bytes
by23.36%, demonstrating a real composition opportunity. The experiment does **not**
isolate how much of Adobe's remaining gap comes from its higher font coverage,
object classification, crop encoding or discarded detail; no additive waterfall
is invented. Adobe's financial font/raster breakdown remains in the frozen forensic
inventory and must be compared with specific matched counterfactuals.

The next bounded operation, if authorized, should identify **broad flat-colour and
crossing objects before estimating paper**, preserve them as independently encoded
source-supported objects, and test the blue triangle/red seal counterexamples first.
Use the existing native JPEG fallback wherever that separation is uncertain. Do
not begin another global mask/threshold sweep. Until this operation is sound,
smaller low-frequency paper plus coverage layers will keep producing false edges
or colour damage. That is the demonstrated blocker, not a missing lossless codec.
