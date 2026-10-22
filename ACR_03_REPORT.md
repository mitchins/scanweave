# ACR-03 — Object-first clean recomposition

## Outcome

**The demonstrated ACR-02 object error is corrected in completed prototypes.**
The blue triangle has a uniform interior, its S is blue rather than black, crossing
annotations remain visible, and the historical seal remains red. Native object
crops match the evaluator-only object arm in the inspected views.

**No production implementation is adopted.** Candidate A passes the selected
visual checks but grows the mixed-content documents. Candidate B saves **576,417 B
(6.39%)** on the complete thirteen-page financial document, with no material new
readability/layout defect found in independent two-renderer review. This is a real,
limited positive result, not a failure against an invented numerical threshold.
However, B fails shaded-paper composition and provides no size advantage on the
logo, annotation or coloured-seal interventions. Both independent reviews advise
against adding a general object/paper/mask product path on this evidence.

The bounded experiment ends here. ACR-01 JPEG85, the ordinary CLI, reconstructed
fonts and faithful are unchanged. No full 32-page regeneration or Rust integration
is claimed. No production PR or merge is warranted by this result. The committed research
branch preserves these bounded findings for review.

## Revision and evidence boundary

- Product base: ACR-01 **`8f14cd329493ad0cc226e480d152d7a464fb4731`**, PR15, still open.
- Verified remote main: **`0ca94aecd74c35ea1b28bcebe7e11e863aae7f08`**.
- ACR-02: PR16 remains draft at **`38cc218f8f1e50e56679fd12d5d72c1d4a44a697`**.
  It is not merge-ready: final verification/Sonar findings remain; its four security
  findings are not resolved or suppressed by this mission. It was not merged.
- Read-only PR14 inspector/renderer: **`ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e`**.
- This branch starts directly at ACR-01, importing only explicit read-only helpers
  into ignored local exports. No PR16 production behavior was cherry-picked.
- All **35 frozen collection hashes match**. Source PDFs and competitor outputs
  remain byte-for-byte unchanged; sealed holdout and unrelated work were untouched.

Reproduction: [qualification/acr03/README.md](qualification/acr03/README.md).
Exact source, script and PDF hashes: [run-manifest.json](qualification/acr03/run-manifest.json).
Python 3.12.3, pikepdf 10.17.0, NumPy 2.5.4, SciPy 1.18.1, Pillow 13.0.0,
pypdfium2 5.14.0, fontTools 4.67.0, Poppler 24.02.0. Frozen Acrobat remains
11.0.20 ClearScan; no new Acrobat conversion is substituted for archived results.

## 1. Causal defect ledger

Coordinates are original MediaBox physical positions, sampled at 300 DPI, without
registration or glyph normalization. Controlled pages are 360×432 pt; their PDFium
raster is 1500×1801. Historical/financial region bounds are specified in
`compare.py`, with exact pixel bounds in `region-results.json`.

| Case / source-selected region | Demonstrated cause | ACR-03 result |
|---|---|---|
| Flat blue logo, pixel **(1230,270)**; inspection `[1040,140,1420,440]` | ACR-02 assigned zero foreground coverage while its paper plate retained blue RGB `[20,85,149]`. Resampled/palette colour then created nested interior contours. | Source pixel `[20,85,150]` is chromatic object; new estimated paper there is `[250,250,250]`. Both representations retain solid blue interior, without invented bands. |
| Blue S below logo, same region | **Inherited ACR-01 colour-ownership defect:** a black visible font painted a genuinely blue source glyph. This was separate from ACR-02 paper failure. | Retain the whole source compound object, suppress only the intersecting visible font show using `Tr 3`; keep its CID, placement, ActualText and Unicode. This is not new coloured-font reconstruction. |
| Crossing annotation, `[90,800,1060,1030]` | Global coverage/colour sampling mixes printed and coloured strokes; independent font paint can duplicate ink inside an object. | Source-derived coherent crop includes crossing ink; intersecting complete glyph transferred to raster visibility, semantic show retained. Amounts, punctuation and rules remain readable. |
| history-04 red seal, normalized `[.12,.70,.88,.92]` | ACR-02 indexed16 foreground materially changed red to brown; sparse edge coverage did not describe a coherent coloured object. | Full-colour native object samples retain red seal wording/outline in A and B. They cost more; no accepted historical compaction result. |
| Financial page 10, right figures `[.78,.64,.97,.91]` | ACR-02 locally estimated paper/coverage transitions created circular halos near underline/204. | A/B remove that representation; independent comparison finds no corresponding circles. Original font outlines are unchanged. |
| history-02 corner `[0,0,.28,.25]` | Paper evidence is unsupported in shaded/book-edge cells. B fills a low-resolution plate across uncertainty, then makes abrupt transitions to protected samples. | **B rejected:** broad tan seam/flecks visible in both engines. A keeps a continuous native crop but grows. Explicit fallback retains ACR-01 byte-for-byte. |

[Logo comparison](qualification/acr03/representative/logo.png) ·
[Financial figures](qualification/acr03/representative/financial.png).
Full-resolution seal/shade/annotation sheets remain local; their paths/hashes are
recorded. These are distinct colour, ownership and paper-transition defects, not
one generic segmentation label.

## 2. One source-derived object method, two representations

The detector uses the original source raster, without OCR or authoring truth.
Estimate paper chromaticity from brighter source samples; distinguish real colour
from the paper-to-neutral-ink chroma segment. Close small gaps and recover enclosed
interiors before grouping coherent coloured objects. A 64-pixel paper grid uses
non-chromatic observations and explicitly records cells lacking paper evidence.
Smooth interpolation estimates economical illumination, not restored pristine paper.

A first diagnostic model incorrectly treated neutral antialiased type on yellow
paper as coloured artwork (292 financial objects and 259 glyph transfers). It was
corrected using the paper-to-neutral chroma model **before** the final A/B comparison.
No threshold sweep or third composition method was introduced. The failed model
and its script remain in local/v0.

Ordinary retained ink is derived from source-supported contrast **and the already
cleaned ACR-01 non-font residual**. It never repaints raw source glyph cores under
emitted fonts. Coloured compound objects instead use original RGB, with every
intersecting vector glyph wholly transferred to raster visibility. No font identity,
font program or Unicode map is rewritten. Unknown content is not silently paper.

- **A — native object crops:** approximately 150-DPI paper; opaque native-resolution
  object and retained-ink crops. Per image choose smaller predictor-Flate or
  full-colour JPEG95 (paper JPEG85). No 16-colour palette assumption.
- **B — masked native-colour tiles:** exactly the same frozen object/protection
  maps; native 512-pixel sparse tiles, 1-bit DeviceGray soft masks and native-colour
  samples, choosing Flate/JPEG95 by encoded size. Hidden off-mask samples are
  filled with estimated paper for encoding only. No resampled foreground colour,
  no global darkness-derived alpha, no symbol substitution. Full colour/mask bytes
  are counted regardless of how much is visible.

A/B protection and object hashes match on all five cases. The blue logo oracle arm
uses authoring differences only for evaluation; source-derived object-mask IoU to
that arm is **0.98806** (annotation **0.90802**). These are mask diagnostics, not
claims about every preserved mark. Both oracle and inferred native-crop arms paint
the inspected blue logo/annotation correctly: the representation itself can work.

Native placement uses exactly **72/300 pt per pixel**, including the renderer's
extra clipped last row. Normalizing the 1801 rows into 432 pt would introduce a
sampling/phase error. No candidate-dependent crop alignment is used.

The paper model remains limited: neutral broad objects, stains and textured shaded
paper are not generally separable by this one chroma/illumination method. Raising
object counts is not evidence that the resulting classification is reliable.

## 3. Actual completed PDF sizes

Each selected-page row is a **whole-document intervention**, retaining the original
four-page controlled, five-page historical or thirteen-page financial context.
Do not sum these rows or call them standalone page sizes.

| Intervention | ACR-01 B | A crops B | B masked B | Decision |
|---|---:|---:|---:|---|
| Blue logo in four-page controlled doc | 431,287 | 536,703 | 523,099 | Cleaner colour/shape; both grow |
| Annotation in same four-page doc | 431,287 | 725,937 | 556,096 | Readable crossings; both grow |
| Seal in five-page historical doc | 5,114,421 | 6,045,921 | 6,113,664 | Red preserved; grows, B paper unsupported |
| Financial page 10 in thirteen-page doc | 9,018,954 | 8,960,135 | 8,890,476 | Limited savings, no old circular halos |
| Shade in five-page historical doc | 5,114,421 | 6,078,494 | 5,562,872 | A grows; B visually rejected |
| **Full thirteen-page financial** | **9,018,954** | Not run | **8,442,537** | **576,417 B / 6.39% saved**, visual subset passes |

The unsafe seal/shade B PDFs remain under `local/rejected/`. The explicit qualified
fallback documents equal the original historical hash
`50fdf5b980fb804315300b7fe6eeef0d489ef6088b7011ee5acf080a95fd6407`.
Standalone and shared-document fallback paths were both exercised. Unsupported
paper outside coherent retained objects is rejected, not tuned away.

### Financial byte accounting

| Encoded resource / cost | ACR-01 B | ACR-03 B |
|---|---:|---:|
| Raster including masks | 7,350,457 | 7,094,398 |
| Reduced paper | Not separately reclassified | 502,145 |
| Native foreground colour | Not separately reclassified | 6,012,918 |
| Native masks | — | 579,335 |
| Font programs | 1,065,434 | 1,065,434 |
| Page content streams | 149,888 | 151,027 |
| Remaining PDF resources/overhead | 453,175 | 131,678 |
| **Complete PDF** | **9,018,954** | **8,442,537** |

The complete saving is not entirely raster saving: **256,059 B** is raster,
**321,497 B** is other serialization/resource overhead, partly offset by **1,139 B**
more content. A matched **save-only control** is **8,971,229 B**: pikepdf reserialization
accounts for **47,725 B**, while the candidate remains **528,692 B (5.89%)** smaller
than that control. There are **1,892 original image objects / 1,928 total objects**,
versus **563 images/masks / 599 total objects** in B. Fewer native resources therefore
explain an important part of the remaining overhead gain; it is not all codec or
serializer efficiency. The Rust writer has not been changed or measured with this
representation, so its exact integrated saving remains unproven.

The trial contains **563 image/mask objects**. All thirteen pages have zero coherent
coloured objects and zero visible-font ownership transfers. Its positive result is
paper/retained-ink packing, not proof of economical coloured-object lifting or
improved font coverage. Native foreground colour dominates despite the compact
paper; the historical support covers 92.6% (seal) / 70.5% (shade) after fringe
support dilation. A broad native crop/mask is not free merely because it is clipped.

Frozen financial comparators: Adobe **718,276 B**, OCRmyPDF-O3 **5,166,004 B**,
rejected ACR-02 **6,912,445 B**. ACR-03 remains **11.75× Adobe** and **1.63× OCRmyPDF**.
Its unchanged fonts alone exceed Adobe's entire PDF; neither paper smoothing nor
mask packing can close that gap alone. No additive attribution of competitor
image bytes to semantic content is invented.

## 4. Visual, semantic and mechanical verification

Independent selected-case review inspected both engines; A passes all five views.
B passes eligible logo, annotation and financial views but **fails shade**. A second
review covered **all thirteen financial pages in both PDFium and Poppler at 300 DPI**,
plus upper-body and lower/numeric fixed windows on every page. No material new wrong
number, lost rule, duplicate text or layout defect was identified. Small warm/soft
edge-tone/background variations remain. This is sampled human-readable inspection,
not a transcription of every number, pixel equality or a new font-clarity claim.

- Four focused algorithm tests pass: solid blue interior, neutral type on coloured
  paper, whole-glyph compound ownership and sparse-tile support coverage.
- Thirteen candidate/fallback PDFs have matching baseline font-program hashes,
  ToUnicode hashes, CID/show/text-matrix/ActualText operator signatures, page boxes,
  PDFium native text and Poppler extraction. Hiding a conflicting visible glyph
  changes its paint mode only; it does not discard its semantics.
- qpdf structural checks passed for completed prototype/fallback PDFs. Unchanged
  font-program hashes establish reuse of baseline font validation, not new fonts.
- Full-financial repeat output SHA is stable:
  `1d70720bbe12b46fd45137db926fe8b56ccdcadba371fa4bd4754f702832a0fb`.
- Full-financial prototype measured **37.03 s, 512,652 KiB peak RSS** on a repeat run;
  this includes source/residual renders and PDF encoding, not original OCR/font
  reconstruction. Per-page timings and final repeat measurements remain local.
- No Rust/product/faithful code changed. No new normal-CLI integration, full-corpus
  result, production Sonar pass or disappearance of inherited limitations is claimed.

[Independent code review](qualification/acr03/reviews/code.md) ·
[Selected visual review](qualification/acr03/reviews/selected-visual.md) ·
[Full financial visual review](qualification/acr03/reviews/financial-visual.md).
The code review's fallback/manifest findings were corrected and the records rerun.
The save-only control preserves text/font contracts and page-10 render hashes in
both engines. Source-selected PNGs are full-resolution; browser previews are not
used as quantitative inputs.

## 5. Gate decision and exact remaining limitation

- **A — object separation:** passes the specific blue-interior/red-seal checks;
  no general object classifier qualification is implied.
- **B — clean composition:** A passes selected views. B fails shaded paper;
  explicit fallback works, while financial/controlled eligible subsets pass.
- **C — product value:** limited positive financial shadow result, but no economical
  mixed-colour-object result. The measured raster reduction is 256 KB;
  the complete saving also includes fewer resource objects and 47.7 KB from the
  save-only serializer control.
- **D — product integration:** **not justified** for either general candidate on this
  evidence. Preserve working ACR-01; do not add mask/paper complexity merely to
  reproduce this modest, narrowly qualified financial gain. No third candidate,
  new codec, font project or broader segmentation round is started.

The precise blocker is **economical foreground representation with credible paper
boundaries**: preserving native colour under hundreds of masks still costs 6 MB,
while paper estimation across unknown shading makes visible seams. Object-first
separation fixes the demonstrated representation error, but does not by itself
supply a competitive, general-purpose encoding. That is the demonstrated limit,
not a demand to preserve scanner noise or exact pixels.
