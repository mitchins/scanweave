# Adobe XI ClearScan behavioural anatomy — ACR-02

22 October2026. **Observed PDF output, not Adobe internals.** Product baseline
ACR-01 `8f14cd3`; research helpers PR14 `ffa604e`. No Adobe executable inspection,
font-program transplantation or incompatible implementation code was used.

## Evidence and reproducibility

`qualification/acr02/fixtures.py` generates **36 unique image-only scans**:
six content families × white/texture/yellow/illumination/annotation/stamp.
Each variant changes one feature relative to its family's white baseline.
Pages are1500×1800 at300DPI (360×432pt); typography/layout remain fixed.
Families: monochrome logo, flat-colour logo, photographic logo, faded receipt,
financial statement and ornament. Drawn annotations are controlled line/scribble
marks, **not genuine handwriting**. The photographic crop comes from the existing
licensed CORD development material. Genuine NARA signatures and historical marks
are checked separately using unchanged frozen comparator PDFs.

Acrobat XI11.0.20 under Wine9.0 emitted a36-page **738,212 B** ClearScan PDF.
ClearScan was explicitly selected using the existing runner. The sticky UI
resampling selector was not reasserted; this report measures emitted DPI rather
than asserting an unverified UI value. A stale initial UI state caused one failed
open; after Escape/close, the unchanged runner succeeded. Both logs are retained.

The exact-object inventory covers **all36 pages**. All36 have font/non-font/
image/path atlases and individually painted image contributions. Ordered replay
is pixel-identical in **PDFium and Poppler on every page**. Full PDF objects,
CTMs, clips, colours, transparency and paint order are recorded locally under
`qualification/acr02/local/adobe-layers/`. See the versioned run manifest and
README for exact helper acquisition and reproduction. Original PDFs are untouched.

## What Adobe actually emits

| Content | Direct observation in the controlled output |
|---|---|
| Printed body text | Visible Type0/CID CFF font paint, with raster text absent from the isolated background in inspected body regions. 175 referenced font dictionaries; **19,375 B encoded font programs**, not175 independently identified typefaces. |
| Monochrome logo symbol | Page0 image **500 0**,328×216 at300DPI,8,420 B. The surrounding full-page image **501 0** is752×901 at150DPI,631 B. Logo lettering may be font-painted separately. |
| Flat-colour logo | Page6 symbol image **305 0**,328×216 at300DPI,9,880 B. Logo lettering uses visible font **350 0** and non-neutral `rg [0.078,0.329,0.58]`. Adobe does not simply turn all recognized coloured ink black. |
| Photographic logo | Page12 image **306 0**,352×296 at300DPI,10,812 B, over a150DPI paper image. It remains an image, not reconstructed paths or glyphs. |
| Annotation crossing text | Page4 images **301 0** (912×184,27,245 B) and **302 0** (1056×80,4,810 B),300DPI. Font-only views have gaps where overlapping printed material remains inside the annotation raster. The compound content survives together. |
| Red stamp | Page5 image **304 0**,400×296 at300DPI,11,307 B. It is a cropped RGB image, not a binary mask. |
| Thin table rules | Page24 contains **10 non-font path paints**, including a stroked horizontal path at CTM translation(20.4,297.36). Some rules also remain in the300DPI crops188/189; not every rule becomes a path. |
| Yellow/shaded statement | Pages26/27 retain **one1500×1800 image at300DPI** (34,152/39,827 B), despite visible font/path paint. Reduced paper plus small crops is not universal. |
| Historical-style ornament | Page30 image **307 0**,1248×168 at300DPI,27,599 B, over750×900 paper at150DPI. It remains raster. |

Across this36-page output there are **65 unique image XObjects**, **560,548 B**
of encoded image streams. All are8-bit RGB JPEG:34 direct `/DCTDecode`,31
`[/FlateDecode /DCTDecode]`. The Flate wrapper must not be mistaken for lossless
image preservation. There are **no image masks, SMask images or inline stencils in
these controlled outputs**. Repeated resources are reused: e.g. the same white
paper, logo and annotation image IDs occur on multiple pages. Page0 has99 text
paint operations, **not99 proven character occurrences**.

### Paper and illumination

The fixed blank strip x100–1400,y430–460 contains no generated text/artwork.
Decoded first-image measurements (`local/paper-measurements.json`) show:

- White and textured mono-logo pages both output RGB250 with channel SD0 in this
  strip; the input texture has independently sampled SD≈2. High-frequency grain
  is removed in the emitted result.
- Yellow input RGB239/224/184 becomes239/225/186: colour is retained approximately.
- The shaded mono-logo strip retains an illumination gradient (mean219.21,
  SD17.93). Adobe does **not** universally whiten or flatten shading.

These are output observations. Whether smoothing precedes JPEG, follows a paper
estimate or results partly from compression cannot be inferred from PDF structure.

### Masks on genuine pages: an important counterexample

The frozen historical collection contains an inline1-bit `/ImageMask true`
stencil3×58 on page3 at≈300DPI. The frozen mixed collection contains16 inline
stencils; page0 examples are8×14 and10×20 at≈300DPI. Thus “Adobe never uses masks”
is **refuted**, even though the new controlled set uses none. The real forms
inventory has19 image XObjects and no inline stencil. Parent clipping/paint colour
is essential when rendering a stencil; raw mask bits are not a visible colour layer.

`local/real-adobe-{history,forms,mixed}/` inventories full frozen documents and
ablates selected historical, form/signature, Linn and illustrated pages. Inline
images are isolated collectively in paint order; addressed image XObjects are
isolated individually. External/soft masks retain their actual parent contribution;
a mask is selection, not a separately additive RGB picture.

## Transferable design and limits

**Supported:** clean/reduced paper, source-resolution crops for compound visual
objects, visible fonts with colour state, occasional rules/inline stencils, and
resource reuse. Overlapping annotations may legitimately carry unreconstructed
printed text in the same image. Fine detail need not be stored as full-page RGB.

**Refuted:** one universal three-layer MRC format; universal150DPI backgrounds;
all rules reconstructed; all coloured content converted to glyphs; all paper
illumination removed; no masks anywhere.

**Unresolved:** Adobe's internal object classifier, exact paper estimator and
how it chooses crop boundaries. Output rectangles do not prove semantic detection.
The controlled photo is a small real receipt crop, not a broad photographic corpus.
Hand-drawn controlled marks do not establish safety on arbitrary real signatures.

The useful next operation is **object/background separation that keeps broad flat
colour and crossing ink intact**, not a global darkness mask. ACR-02's attempted
local paper/coverage representation fails that distinction; see ACR_02_REPORT.md.
