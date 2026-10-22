# ACR-04 — Selective residual JPEG encoding

## Decision and completed output

The ordinary ClearScan CLI now produces **12,454,682 bytes** on the frozen
32-page development corpus, down from ACR-01's **18,556,766 bytes**:
**6,102,084 bytes / 32.88% saved**. This is below frozen OCRmyPDF -O3's
15,315,903 bytes, but still **2.98× Adobe XI's 4,178,103 bytes**.
This is a codec/resolution improvement, not a new segmentation or font pipeline.
Minor softness and paper-texture changes are intentional; faithful is unchanged.

| Collection | ACR-01 bytes | ACR-04 bytes | Wall seconds | Peak RSS KiB |
|---|---:|---:|---:|---:|
| Historical, 5 pages | 5,114,421 | 2,278,050 | 67.76 | 721,912 |
| Receipts, 10 pages | 2,208,177 | 1,288,188 | 28.81 | 538,604 |
| Financial, 13 pages | 9,018,954 | 6,898,862 | 477.11 | 1,371,484 |
| Mixed, 2 pages | 1,355,690 | 1,130,058 | 108.45 | 298,468 |
| Forms, 2 pages | 859,524 | 859,524 | 42.94 | 433,472 |

The financial result saves 23.51%, without adopting the rejected ACR-02
composition. It remains larger than OCRmyPDF's 5,166,004 and Adobe's 718,276 bytes.
Actual complete PDFs are retained locally under
`qualification/acr04/local/product/{collection}.pdf`, with adjacent reports,
logs and `/usr/bin/time -v` measurements. The financial PDF SHA-256 is
`8a8d5d32b710177c37b2fff4b2ad472ffc462f355626b5ac98f10d11bcae4182`.

## Provenance and boundaries

Branch: `product/acr04-selective-raster`, based directly on accepted ACR-01
`8f14cd329493ad0cc226e480d152d7a464fb4731` (PR #15), not ACR-02/03 research.
Remote main was `0ca94aecd74c35ea1b28bcebe7e11e863aae7f08`.
PRs #14/#16 remain research, unmerged. The implementation PR is stacked on #15.
All 35 frozen input/comparator hashes were revalidated; no frozen PDF was changed.
No sealed holdout, annotation truth or pristine font entered conversion.

All final collections were converted through the ordinary PDF-to-PDF CLI with
normal document-wide OCR/donor context, using immutable binary SHA-256
`dde0d1da4fc94e69ad291edcc7cc96d9ad52b57b7acbe2e1f9d753b996401556`.
The scripts, commands, tool provenance, hashes and local source-archive identity
are indexed in [the reproduction manifest](qualification/acr04/reproduction-manifest.json).
Large PDFs/renders remain ignored locally. This is a development-corpus result,
not a guarantee for unseen scans.

## What actually cost bytes

ACR-01 retained 42.89 MB before its JPEG85 milestone; this mission starts from
its already compact 18.56 MB outputs. At that baseline the financial collection
alone retained 5,131,859 bytes of non-whole-page raster, largely native exception
crops. Historical pages retained 5,034,620 bytes of whole-page raster.
Full-page placement does not prove native resolution: reduced paper is classified
from the converter's patch provenance, not image area. No compressed image's
bytes are allocated to text/artwork by covered pixel percentage.

Final unique encoded streams:

| Class | Bytes |
|---|---:|
| Whole-page residual/native imagery | 4,579,419 |
| Existing reduced paper | 1,589,328 |
| Native exception imagery | 3,774,218 |
| Font programs | 1,632,820 |
| Page content streams | 349,979 |
| Other PDF structures/resources | 528,918 |
| **Complete PDFs** | **12,454,682** |

There are 2,385 unique image resources. Per-page references, actual raster bytes and classification are in
[results.json](qualification/acr04/results.json) and
[page-accounting.csv](qualification/acr04/page-accounting.csv).
Repeated placements are not charged twice in collection totals. Full object identities
remain in the hash-bound local inventory and per-collection verification files.

## Controlled experiments and selection

Adobe anatomy predicted that subsampled JPEG and lower spatial resolution could
be useful; it did not establish an equivalent libjpeg quality setting.
The first shadow controls held decoded ACR-01 residual pixels, fonts, placement
and page operators fixed, and rewrote only eligible full-page streams:

| Full 32-page shadow control | Complete bytes |
|---|---:|
| Save-only serialization | 18,499,568 |
| Optimized 4:4:4 Q85, native | 17,417,590 |
| 4:2:0 Q85, native | 16,027,146 |
| 4:2:0 Q80, native | 15,513,152 |
| 4:2:0 Q85, two-thirds dimensions (~200 DPI) | 13,241,525 |

These use already JPEG-decoded residuals, not raw original encoder samples.
The 57,198-byte save-only difference is serialization, not a codec saving.
Native 4:4:4 versus 4:2:0 holds encoder quality/dimensions fixed and isolates
sampling more closely; the reduced arm changes resolution too. These effects
interact and are not an additive savings waterfall.

Independent blinded selected-region review found all four image arms acceptable
in both renderers. The reduced Q85 arm was the strongest simple size/quality
trade-off. Blind review's directory-listing limitation is disclosed in its notes.
The cheaper Q80 arm was not selected simply to chase bytes.

A second controlled experiment addressed financial native exceptions, preserving
source dimensions/placement and 4:4:4 colour. Q95 produced 7,887,505-byte financial
PDFs; Q90 produced 6,996,071 bytes, compared with save-only and lossless crops.
Independent selected-detail review accepted both, including amounts, commas,
minus signs and fine print. Q90 was selected with a minimum saving gate.
These are complete shadow PDFs, not isolated JPEG-buffer claims.

### Product implementation

One JPEG representation family extends the existing assembler:

* Eligible whole-page tonal residuals try optimized Q85 4:2:0, with approximately
  200-DPI Lanczos3 reduction when that saves at least 5% versus native Q85.
  Physical page extent is unchanged. No upsampling is performed.
* Eligible tonal native exceptions retain source resolution and 4:4:4 Q90.
  They require at least 16×16 samples, 64 luminance levels, a 512-byte lossless
  stream and at least 5% encoded saving. Binary/tiny patches remain lossless.
* Whole-page eligibility retains the 512-pixel minimum and 16-MP resource bound.
  Verified source-JPEG passthrough, explicit protection and faithful remain separate.
* Encoding failures/non-beneficial candidates retain existing alternatives;
  actual complete serialized PDF length chooses the compact document.
* The pure-Rust MIT/Apache `jpeg-encoder` 0.7.1 adds no transitive dependency or
  external executable. No public switch, ownership rule, font or OCR change.

An optimized sequential RGB encoder exposed an existing decoder compatibility
problem: white decoded green in the project's image decoder despite correct
Poppler/PDFium rendering. That trial was rejected. Progressive RGB scans fix the
round-trip; odd dimensions, colour and partial MCU regression tests cover it.
All final results bind to the corrected progressive build, not the rejected run.

### Hypotheses B and C

Independent raster/font ablations support **unconverted printed ink**, rather
than retained full cores under emitted fonts, as the principal expensive residual
on selected financial pages. No safe, dominant cleanup defect was established.
No additional source pixels were erased and no cleanup saving is claimed.

ACR-03 already showed the limited value of expensive native-colour masked tiles.
The source-native crop experiment above improves existing objects' encoding
without new masks, classification or paper estimation. It outperformed adding
another selective-composition architecture in engineering cost for this mission;
no new crop/mask geometry was integrated or claimed as a tested win.

## Visual and functional evidence

Independent review inspected all 32 final pages in both renderers (64 overview
sheets), plus native 300-DPI fixed-coordinate detail on historical, receipt,
financial, Linn and NARA pages. It found no material new content loss, seal-colour
damage, seam, halo or decoder corruption. Minor thermal/historical softness and
paper-texture reduction remain. Inherited rough reconstructed receipt typography
is not newly repaired. The review is sampled evidence, not certification of every
faint mark or unseen input. See [the final visual review](qualification/acr04/final-product-visual-review.md)
and [implementation review](qualification/acr04/implementation-review.md).

All 32 decompressed page operator streams, font programs, ToUnicode streams,
MediaBoxes, glyph/owner decisions and suppression counts match ACR-01 exactly.
PDFium native text and Poppler raw extraction match on every page. Receipt numeric
search remains **17/49**, with the same per-query outcomes. Source-representation
changes cannot be inferred safe from invisible text alone: six pages were also
rerendered and recognized independently by fixed Tesseract PSM3. OCR token changes
are recorded in `rerender-ocr.json`, not hidden; these are distinct from native
search and require visual interpretation rather than exact OCR-string equality.

The maintained matched CID counter yields Linn 784 and forms 504 before **and**
after. Earlier 748/500 figures use older evidence; this is not increased font
coverage. Page operators and outlines are identical, not merely similar counts.

### Regression and operational cost

* Unfiltered locked workspace tests: 136 pass; donor repair passes. Denied-warning
  Clippy, workspace build and all 15 existing Python CI scripts pass.
* E0–E7 pass. Historical P01–P08 visual limitations remain disclosed; their failing
  checks are not represented as passing or silently excluded.
* All five PDFs pass qpdf syntax checks and OTS font validation.
* Repeated receipt and synthetic300 conversions are byte-identical.
* Matched faithful forms are byte-identical: 855,127 bytes, SHA-256
  `5f17cd97caa7caa79f931edc63692fe2551235f4aa658072cf24482f0f78188c`.
* Synthetic300: 185,119 → 173,746 bytes; synthetic600: 258,720 → 189,052.
  Visible owners remain 531/552 and 517/552. On the same 552 non-space exact-size
  instances, PDFium IoU changes 0.95668751 → 0.95667259 at300 and
  0.96826778 → 0.96828461 at600; Poppler 0.94972894 → 0.94973258 and
  0.96244957 → 0.96246942. No material fidelity loss or font improvement is claimed.
  The evaluator's pristine reference remains separate from conversion.

Financial wall time was 477.11s versus archived ACR-01 452.73s. These are not
controlled isolated encoder benchmarks (concurrent workload differed), so no
causal speedup/slowdown percentage is asserted. Peak financial RSS was 1.31GiB.
The assembler still constructs competing PDF candidates; added encoding has real
CPU/memory cost. Per-stage times and measured RSS are retained in results.

## Remaining gap and next intervention

The result is 18.68% smaller than frozen OCRmyPDF -O3 but 8,276,579 bytes larger
than Adobe. Financial native exceptions still cost 3,461,535 bytes, reduced paper
1,479,568, and font programs 1,065,434; whole-page residuals cost only334,370.
Thus more whole-page JPEG tuning is not the main financial opportunity.

**Highest-value next intervention:** a bounded representation experiment on
financial retained printed ink, separating compact high-resolution luminance
from low-frequency paper/colour while preserving thin digits and rules. It must
beat the new Q90 native crops in actual PDFs and reject visible character loss,
halos and seams. This is a proposal, not a new implementation or authorization
for generic MRC or OCR/font redesign. Better font coverage remains relevant but
was not solved here. Adobe's savings cannot be copied without checking what
source detail its much smaller backgrounds omit.

No automatic merge. Publication CI, server-side Sonar and review disposition are
recorded in the implementation PR; local success alone is not a green server gate.

### Rerendered OCR caveat

On financial page6 Tesseract changed `75` to `15`. Independent inspection at
source pixels `[1150,1330,1450,1530]` found source, baseline and final all visibly
read `33 75` in both renderers: the final7 retains its top bar and diagonal.
This is a real optical-recognition regression, not proof of a visible substituted
digit. Receipt2 changed mistaken `36,000` to visible `-16,000`; receipt5's sparse
`70`/`0`/`017` tokens were not reliable truth. Native PDF text was not changed.
The selected candidate is accepted with this limitation, not an OCR-invariance
claim. Exact strings and independent supplemental sheets remain reproducible.
