# ScanWeave — implementation specification v0.1

**Date:** 13 October 2026  
**Status:** Proposed engineering contract; no implementation or performance qualification is claimed.  
**Working name:** ScanWeave (`scanweave`); check package/name availability before publication.  
**Deliverable:** An offline scanned-document reconstruction library and CLI, not a PDF editor or a new OCR engine.  
**Licence target:** MIT OR Apache-2.0 for original project code; audit every shipped dependency, model and resource separately.

## 1. Product contract

Given original page pixels and OCR with geometry, produce a compact PDF that preserves the document's visible appearance, exposes the supplied text for search/copy, and replaces suitable scanned text with reusable vector glyphs embedded as document-specific fonts. Retain original raster regions whenever reconstruction is unsafe, unsupported or uneconomic.

The result should still look like the source, whether its typography is a conventional bank-statement font, Comic Sans, a historical typeface, or Japanese kana. The system does not need the original font file and must not replace the source with a merely similar installed font. It reconstructs **observed shapes**, not the author's original digital font or details that the scan never captured.

The priority order is: (1) do not corrupt visible content; (2) do not introduce text-layer corruption beyond the supplied OCR; (3) preserve layout, typography and non-text material; (4) choose a small representation; (5) improve scalable vector coverage. No size target overrides the preceding priorities.

OCR can already be wrong. The utility preserves OCR provenance; it cannot certify an account number, amount or historical transcription merely because it can encode it in a font. Visual fidelity, semantic accuracy, PDF validity and compression are four separate qualification results.

A scanned source and a searchable output are not byte-equivalent products. Searchability can add overhead, and there is no promise that every output is smaller than its input. A one-page receipt can be better represented by compressed raster text than by a new font. `auto` chooses the smallest **qualified candidate evaluated**, not a claimed global optimum.

### 1.1 Required use cases

| ID | Use case | Required behaviour |
|---|---|---|
| UC-01 | Scan + existing Tesseract hOCR | Build without invoking another recogniser. Use real symbol geometry when present; retain word-level granularity when it is not. |
| UC-02 | Existing OCR from another engine | Accept the engine-neutral bundle. Engine/model choice does not enter the visual reconstruction core. |
| UC-03 | Thermal receipt | Preserve faded ink, decimal points, currency, barcodes, logos and handwriting. No default whitening or despeckling. |
| UC-04 | Bank statement / utility bill | Preserve all amounts, identifiers, tables, footnotes, colour coding and non-text marks. Protect selected financial regions with original raster samples. |
| UC-05 | Old document / book | Reuse shapes across a bounded page window; preserve old glyph forms, ligatures, page texture, illustrations and marginalia. No automatic modernisation or dehyphenation. |
| UC-06 | Decorative / unfamiliar font | Trace source shapes. No font-identification service, font download or substitution is required. |
| UC-07 | Japanese kana and mixed Japanese/Latin | Support multi-component glyphs, dakuten/handakuten, small kana, punctuation and logical text. Horizontal and vertical layouts have separate qualification gates. |
| UC-08 | Low-quality / unsupported script | Preserve source appearance with raster fallback and whatever OCR geometry/text was actually provided. Report unrecognised content. |
| UC-09 | Scan-only PDF | Preserve physical page geometry. Rebuild to a distinct output; do not append old scan data as an incremental revision. |
| UC-10 | Already-digital / mixed PDF | Pass through native pages. Do not turn good digital text into scans or reconstruct it unnecessarily. Unsupported document-level features cause an explicit hold, not silent loss. |
| UC-11 | Embedded consumer such as PdfCraft | Host supplies pixels/OCR; core returns host-neutral reconstruction plans. No CLI process or OCR runtime is required to use the library. |
| UC-12 | Long offline batch | Bounded resources, cancellation, deterministic output on a pinned environment, content-bound resume, atomic PDF publication and machine-readable reporting. |

### 1.2 Non-goals for v1

No GUI, scanner driver, mailbox integration, cloud service, account system, OCR training, LLM correction, generative super-resolution, reflowed ebook export, general PDF editor, automatic financial reconciliation, handwriting-to-font generation, full PDF/UA certification, or recovery of the original source typeface. No in-house PDF parser, OCR engine, image codec or general-purpose vector tracer.

Do not make universal handwriting or script-recognition claims. All scripts can be visually retained through fallback; searchable recognition depends on the supplied OCR. Passing a Latin corpus does not qualify Japanese, and passing horizontal Japanese does not qualify vertical Japanese.

## 2. Architecture and reuse

Use a Rust workspace with **three production crates**, plus a development-only qualification harness. Keep internal modules together until an actual consumer needs another crate.

| Crate | Owns | Must not own |
|---|---|---|
| `scanweave-core` | Validated geometry/types, coverage, visual units, matching, tracing adapter, candidate planning, glyph assets, policy decisions, cancellation/progress interfaces | Filesystem discovery, subprocesses, network, PDF object graph, an OCR engine, UI framework |
| `scanweave-io` | Image and OCR import, bundle validation, optional PDF source adapter, font serialization, PDF assembly, structural validation adapters | OCR-dependent visual substitution, a second reconstruction algorithm |
| `scanweave-cli` | CLI/config, optional local OCR invocation, jobs/cache/resource limits, reports, atomic publication | Business logic duplicated from core |
| `qualification/` | Corpus adapters, oracle fixtures, independent render/extraction checks, benchmarks, mutation tests | Runtime dependency of the library |

The core takes immutable page rasters and normalized OCR, yielding `PageAnalysis`, document/window `GlyphDictionary`, and `PagePlan` values. A `PagePlan` references content-addressed assets supplied through an asset-store interface rather than retaining the whole document in RAM. The PDF adapter consumes these plans. An embedding host may consume the same plans directly.

A synchronous library API with callbacks and a cancellation token is sufficient. Do not require Tokio, a web server, a database daemon or a GPU. A consumer can put work on its own thread pool.

### 2.1 Intended reusable components

These are evidence-backed candidates, not a fabricated lockfile. At M0 resolve exact versions/commits, source hashes, licences, transitive licences, platform availability and required APIs in `UPSTREAMS.lock.toml`. Pin the Rust toolchain then. Do not silently use newer upstream versions in qualification.

| Responsibility | Preferred building block | Decision |
|---|---|---|
| OCR | Existing hOCR / normalized JSON; optional Tesseract executable | Reuse OCR. Tesseract exposes symbol iteration and character-box hOCR. [S03, S04] |
| Image primitives | Rust `image`/`imageproc`; Leptonica only behind an optional adapter if measured necessary | Use existing decode, thresholding, connected-component and morphology primitives. Audit chosen codecs. [S14] |
| Vector tracing | VTracer / visioncortex library | MIT upstream. Prove compound contours/holes and curve export before committing to its adapter. [S05] |
| Curves and font writing | `kurbo`; Fontations `write-fonts` / `read-fonts` | Reuse curve conversion and OpenType table writing. No hand-written TrueType serializer. [S06] |
| PDF generation | `pdf-writer` | Low-level PDF emission, not a renderer or a validator. [S07] |
| PDF import / object copy | `lopdf` | Optional native-PDF adapter; avoid imposing it on core-only consumers. [S09] |
| Default Rust PDF rasterization | `hayro`, after corpus qualification | Work-in-progress upstream; never use it as its own sole validation oracle. [S10] |
| Independent validation | qpdf; Poppler and PDFium; FontTools and OpenType Sanitizer | Development/qualification tools. Separate executables and dependency policies from shipped core. [S12, S13, S15] |
| Existing output baselines | OCRmyPDF; Internet Archive PDF Tools; optionally Scribe and TrulyFreeOCR | Run as black-box baselines. No need to copy copyleft code into the permissive engine. [S02, S08, S11, S16] |

Smoothscan already demonstrates scanned-symbol vectorization into embedded TrueType, but its documented prototype assigns arbitrary character codes. It is a technique reference and optional baseline, not the selected production foundation. [S01]

No claim here grants rights to redistribute third-party fonts or model weights. Distribute only permitted synthetic fixture sources/assets. Use operator-provided Comic Sans scans as private tests; do not package a Comic Sans font. Reading an algorithm description is not permission to copy its implementation.

### 2.2 PdfCraft boundary

The inspected PdfCraft OCR module describes invisible text over retained pixels and exposes word rectangles. Its currently inspected recogniser is Latin-oriented. Therefore, integration must accept a better external OCR result rather than inheriting that alphabet restriction. [S17]

Implement integration as an **optimized export / reconstruction mode**. The host may show a preview and obtain approval, but the reusable library does not depend on that UI. A fresh compact output is required to reclaim old image storage; merely appending new glyphs while retaining the original image bytes is not a compression implementation.

`PagePlan` includes a disposition (`reconstructed`, `hybrid`, `raster`, `passthrough`), ordered paint operations, font/bitmap asset references, semantic spans, source-to-output mappings and reasons. The host owns its source PDF graph, document history and save policy. A host may reserialize the plan in its own PDF engine.

## 3. The three independent identities

Do not model a glyph as a Unicode character with a bitmap attached.

**Visual unit:** an observed shape or shape cluster extracted from source pixels. It can contain disconnected components, a ligature, an entire word, or unknown text.

**Semantic span:** the exact OCR-supplied Unicode string, provenance, geometry, logical reading position and confidence information. A span can cover one visual unit, multiple units, or a retained raster region.

**PDF encoding entry:** a document-local association used for rendering and extraction. Several CIDs may point to the same glyph outline but expose different Unicode strings. Conversely, several differently printed shapes can all expose the same Unicode.

Consequences:

- Never merge visual units just because OCR labels match. Never choose a template because it has the expected character name.
- A source `8` labelled `6` must retain the observed `8` appearance. Its search text remains the supplied `6` unless an explicit correction is supplied.
- Sharing a visual outline must not overwrite occurrence-specific OCR text by cluster majority vote.
- Glyphs are strings/clusters, not single-byte characters, not necessarily one code point, and not necessarily one connected component.
- Unknown text does not become an invented Unicode character. Preserve its appearance; mark its search coverage as unknown.

OCR boxes are candidate geometry, not a licence to erase all pixels in the box. OCR-free ink remains part of the page.

## 4. Input contract and normalized OCR

### 4.1 Supported entry paths

1. Raster image or ordered multi-page TIFF plus explicitly mapped hOCR.
2. A versioned manifest of images and per-page normalized OCR JSON.
3. Scan-only PDF plus externally bound OCR; direct PDF rendering is an adapter.
4. Optional convenience OCR invocation on prepared page images, never implicit on an already-bound OCR input.

PNG/JPEG/TIFF are the initial image formats. Additional formats require codec/resource-limit tests. A plain text file or Markdown transcript without page geometry is not sufficient for reconstruction. An existing searchable PDF is not guaranteed to contain character boxes; preserve its actual granularity.

hOCR with real character boxes is the first OCR adapter. Ordinary word-level hOCR remains useful: use whole-word shape units if justified, or a retained raster word with text. Do not split words into equal-width fake characters. TSV is word-level import, not a source of invented symbol boxes. ALTO is a later adapter behind the same contract; reject unsupported measurement units or transforms rather than guessing.

### 4.2 Binding and coordinates

See `schemas/ocr-page.schema.json` and `examples/ocr-page.example.json`. The example illustrates structure only and does not refer to a bundled scan.

Every page binds to both original raster **file hash** and a **decoded pixel hash**. Canonical pixel hashing includes a format/dimensions header and packed, top-to-bottom, padding-free sample bytes. The production decoder's colour/orientation policy is pinned in the binding. Hashes prevent stale OCR from being used after rotation, image replacement, cropping or deskewing.

Core coordinates are continuous **pixel-edge coordinates**, origin at the top-left of the canonical raster, +x right, +y down. A 10-pixel-wide image occupies x in [0,10]; pixel centres are at half-integers. Rectangles are half-open. Polygons and baseline points use the same coordinate space. The core never receives mixed coordinate systems.

The page manifest also stores physical dimensions and an invertible affine `raster_to_page_pt` transform. For an unrotated 300-dpi image of height H: `[72/300, 0, 0, -72/300, 0, H*72/300]`, using `x'=a*x+c*y+e`, `y'=b*x+d*y+f`. Output page points are physical 1/72-inch units; the PDF adapter accounts for source CropBox, MediaBox, rotation and UserUnit separately. Retain the source geometry record. No double application of PDF rotation or EXIF orientation.

Image DPI must come from reliable metadata or an explicit override. If neither DPI nor physical size is available, return `MissingPhysicalGeometry`; do not silently assume a 300-dpi receipt. Very large dimensions and malformed/invertible-looking but numerically unstable transforms are rejected with bounded work.

Any external deskew/dewarp must provide the exact OCR reference raster and its mapping. Affine transforms are supported initially. For a nonlinear dewarp, accept the dewarped raster as an explicitly chosen new visual source, or reject the mapping; do not apply an affine approximation silently. Original-page geometry is the default output target. Optional deskew/cleanup is a separate, logged transformation, not a free compression step.

### 4.3 Normalized page information

The schema includes page identity, raster binding, physical extent, producer name/version and model hashes, declared languages, granularity, logical reading order, and a list of semantic spans. Each span includes an ID, text, trailing separator, source polygon, direction, role, raw confidence and scale, and optional symbol observations with byte ranges into the UTF-8 string.

A symbol's byte range must be on Unicode scalar boundaries; a visual cluster must not accidentally split an extended grapheme sequence. Preserve supplied strings exactly. No NFKC, punctuation rewriting, spelling correction, automatic dehyphenation, implicit joining of lines, or conversion between full-width and ASCII characters.

Confidence is `null` when unavailable. A score of 95 from an OCR engine is not automatically a 95% calibrated probability. Retain its original scale and meaning. v1 does not use a global confidence threshold to delete visual ink or silently drop search text.

The importer validates unique IDs, geometry within a small documented boundary tolerance, legal UTF-8, page binding, text ranges and reading-order references. A word with no valid glyph geometry stays a word. Reject conflicting or duplicate text coverage rather than selecting one arbitrarily.

`reading_order_status` is `supplied`, `inferred` or `unknown`. Preserve explicit order. When only layout heuristics supply order, mark it inferred. An inferred order is not evidence of accessible reading order or a correctly recovered table structure.

### 4.4 Corrections and protected regions

An optional corrections file is bound to source and OCR hashes, references span IDs and specifies exact replacement text plus provenance. Corrections never change visual geometry unless a separate, explicit geometry override is supplied. Preserve the original OCR in the report/work record; do not silently rerun a recogniser and replace it.

Caller-provided protection polygons have priority. Receipt/statement presets also conservatively protect numeric-bearing tokens, their adjacent signs/currency/decimal separators, identifier-like tokens and known table data regions. These heuristics add protection; they are not proof that every financial field has been detected. All unprotected content still passes the full visual checks.

Once derived, the protection mask is a distinct input to the visual planner. A label-only OCR mutation with fixed geometry and a fixed protection mask must leave the visual plan unchanged.

## 5. Reconstruction pipeline

### 5.1 Preflight and preserved baseline

Inventory source pages and their existing native text, images and unsupported features. Establish a searchable raster baseline using the exact supplied OCR. Preserve source image streams when safe and possible; otherwise losslessly encode their canonical decoded samples. Keep this candidate available throughout planning.

For an existing digital page, choose passthrough rather than rasterization. Initially, mixed native/raster pages also pass through intact. Targeted image-XObject replacement within an otherwise digital page is a later integration capability, not a requirement to make the core useful.

Baseline validity includes physical geometry and semantic coverage. The unchanged source file is a size comparator, but is a viable output candidate only when it already satisfies the requested searchability, geometry and feature-preservation contract.

### 5.2 Segmentation and coverage

Use a conservative foreground/background analysis to propose text regions, with OCR polygons as hints. Preserve colour source samples. Analysis may create multiple temporary binarizations; those are not automatically the output image.

Create an explicit coverage/ownership map for reconstructed regions, retained rasters, protected material and background. Overlapping candidate regions must be resolved into a disjoint ownership plan or merged/fallbacked. No pixels or connected marks disappear merely because OCR did not label them. Disconnected accents and punctuation must remain attached or separately owned.

Start with monochrome or near-monochrome text on locally simple backgrounds. Text touching a photograph, stamp, underline, table rule or patterned paper falls back unless the adapter can separate it without altering those elements. The first implementation must not build a document-layout neural network.

White rectangles over word boxes are forbidden. Remove only the accepted ink footprint and its validated antialiasing fringe. Even that replacement is provisional until recomposition validation passes. Filling the old ink position with a deterministically estimated local paper colour is allowed only for a locally simple background, with the estimate and changed region recorded. Unknown paper texture behind opaque ink cannot be recovered exactly; textured or inseparable regions default to raster.

When removing source text, also remove its retained full-resolution copy from the encoded visual background. Keeping the whole original page plus drawing vectors on top does not satisfy reconstruction or size gates. Only a documented whole-page fallback may retain a full-page scan.

### 5.3 Visual units and observation extraction

Use source masks, contours, ink colour, bounding geometry and baseline-relative placement. Preserve dot/diacritic/radical components. Connected-component count is not character count: `i`, `é`, `ガ` and many kanji can have several components; touching `rn` can resemble one component.

With symbol geometry, collect the entire observation including marks. With word-only geometry, a complete word can be one visual unit mapped to a Unicode string. Split into smaller units only when an independent geometric association is defensible; otherwise keep the complete unit or fall back.

Unknown or ambiguous ink may remain raster. Tracing a shape does not oblige assigning a text label. A vector shape without semantic identity can be emitted as non-text artwork without fake private-use characters.

### 5.4 Dictionary and matching

The v1 dictionary is document-local and bounded by an explicit page window, initially 64 pages. No persistent cross-document glyph cache by default. This avoids privacy leakage, incorrect type-style transfer and unbounded font growth.

Matching stages are: exact normalized-mask lookup; geometric descriptor buckets; bounded comparisons against actual representatives. Start with translation-aligned, scale-compatible observations. Broad scale normalization, slant correction, morphological repair and learned averaging are out of scope for the first proof.

Use an actual observed **medoid**, not a synthetic average, as the first representative. Keep multiple visual variants when ink weight, style, damage or shape differs. Every occurrence must pass against the final representative rendered at its own placement. Do not use transitive union-find merging where A≈B and B≈C are taken to imply A≈C.

OCR labels are not matching authority. They may be recorded as discrepancy diagnostics; they must not drive visual substitutions or majority-vote text replacement. Distinct source observations labelled the same character need not share an outline. Identical observations with different labels may share shape storage while retaining distinct PDF semantic encodings.

Limit bucket occupancy, candidates tested, contours, points and CPU work. Exhausted budgets cause a recorded raster fallback, not dropped text or an unbounded quadratic comparison.

### 5.5 Outline construction

Trace accepted masks with the selected upstream vectorizer. Convert its output into true compound font contours. **An SVG using white paint to cover a black shape is not automatically a valid glyph outline.** Holes in `O`, `8`, `B`, kana and historical lettering must become correctly oriented contours, not white glyph fills. Test counters and nested contours on non-white paper.

Perform cubic-to-quadratic conversion through a verified curve library or an established conversion implementation; keep an explicit geometric error budget in source-pixel units. Quantization, simplification and font-coordinate conversion all spend that same budget. Never allow the tracer, converter and font writer each to consume the full tolerance independently.

Use ordinary unhinted TrueType outlines initially; do not synthesize hinting instructions. Validate winding, closure, bounds, integer limits and point counts. Extremely complex outlines become raster candidates rather than exceptionally large or malformed fonts.

Do not invent serif detail or missing strokes. Vectorization removes raster pixelation; it does not recreate information absent from the scan.

### 5.6 Placement

Record each occurrence's original placement transform, geometry and colour. Preserve irregular kerning, baselines, superscripts and alignment by explicit placement. Do not typeset recognized strings again with conventional font metrics or HarfBuzz; the scan already contains the shaped visual forms.

Baseline/font metrics help compact representation and selection but must not override source placements. Begin with per-unit positions for correctness. Only combine adjacent units into compact PDF text runs after render/extraction equivalence tests prove the optimization.

Protect bidi and vertical logical order independently from paint order. Distinct paint and semantic orders are allowed; their mapping must remain explicit.

### 5.7 Candidate validation and fallback

For every occurrence, compare the candidate after final tracing, font quantization and placement with its own source crop, including nearby context. Validate final assembled pages as well, since locally correct glyphs can still be misplaced or erase neighbouring content.

Initial tunable thresholds are in `defaults.toml`; their definitions and freeze protocol are in `QUALIFICATION.md`. Thresholds are engineering starting points, not evidence of human equivalence. Use multiple signals: edge displacement, ink overlap, threshold-stable topology, local colour/coverage error and missing/added small components. Page-wide SSIM alone is never an acceptance gate.

Fallback order is: accepted shared glyph; accepted unique glyph; unchanged raster region; unchanged raster page; explicit failure when the source/baseline itself cannot be faithfully processed. Complexity/size failures may skip directly to raster. Failure of a PDF validator is not permission to publish an unvalidated file.

Protected regions retain canonical source raster samples without lossy foreground coding or default tracing. This protection includes their punctuation and neighbouring uncertainty margin. A digit regex is not the only safety mechanism.

Reconstruction preserves source appearance within a measured policy, not a mathematical guarantee that humans can never perceive a change. `exact` is a distinct raster-preservation mode; do not call ordinary vector reconstruction lossless.

### 5.8 Compression planning

Evaluate at least: searchable source-raster baseline, conservative MRC where valid, and hybrid font reconstruction. The first proof can implement baseline + hybrid; MRC comparison exists from M0 and an internal MRC candidate is added before a production auto mode is qualified.

For each dictionary/window candidate account for: font tables/outlines; CID maps and ToUnicode; placement streams; background and foreground images; masks; fallback crops; object/xref overhead; and shared resource amortization. A large glyph dictionary can lose on kana-heavy pages with many rare forms or on a very short receipt.

Use bounded greedy or beam-style candidate selection, not an exhaustive combinatorial optimizer. Measure actual serialized whole-document bytes before choosing the final winner. A local estimate cannot establish a document-level saving. Keep the fallback baseline with the same supplied text available, and select it when smaller.

Compression effort changes candidate search/codec effort, not safety. A target size is advisory unless `--require-target` is set; it never permits lowering text resolution, dropping pages, changing symbols or erasing non-text content without an explicitly different policy.

MRC is a representation, not a blanket losslessness guarantee: foreground/background separation can itself alter appearances even when its final mask codec is lossless. Qualify it against original samples, not just its own mask. [S08]

## 6. PDF and font output contract

### 6.1 Font encoding

Production visible reconstructed text uses an embedded subset TrueType font inside a Type 0 / CIDFontType2 PDF font. Keep the visual glyph index (GID) separate from the PDF character identifier (CID). Use an explicit CIDToGIDMap and ToUnicode CMap. The nominal OpenType `cmap` is not the source of truth for occurrence-specific PDF text extraction.

The encoding allocation key includes `(visual_glyph_id, semantic_string, writing_mode, required_metrics)`. Two CIDs may reference one GID with different semantic strings. Two GIDs may map to the same semantic string. Never equate Unicode scalar value, CID and GID.

Use complete Unicode strings, encoded correctly for PDF Unicode mappings, including surrogate pairs where needed. A ligature can expose multiple characters. Preserve OCR's exact string rather than forcing either a compatibility ligature or its expansion. Use bounded-size ToUnicode mappings; exceptionally long visual clusters use a separately qualified span-level ActualText strategy or raster-plus-text fallback.

Use valid required font tables, deterministic subset naming, `.notdef`, correct bounds, advances and metrics. Cap each font resource at a conservative **60,000 glyphs and 60,000 CIDs** and split before limits are reached. These are project caps, not an assertion that OpenType's exact format limits equal 60,000. Also cap point counts, contour counts and font bytes. Prefer additional small subsets or raster fallback to a giant font.

No Type 3 prototype may silently become the production font path. A Type 3 diagnostic is allowed only if explicitly labelled experimental and excluded from production qualification. It does not satisfy the TrueType interoperability gate.

### 6.2 Semantic ownership and invisible fallback

Each admitted semantic span appears exactly once in extracted content. For a simple visible glyph/ligature, ToUnicode owns its text. For a more complex many-to-many span, a qualified ActualText marked-content span may own replacement text. For retained raster regions, one invisible text representation owns the semantic span.

Do not put a full invisible OCR layer under already searchable reconstructed text. Merely marking a second copy as an artifact is not an acceptable substitute for testing extraction; some extraction APIs do not obey accessibility tags as expected.

Fallback can use a tiny generated glyphless font with explicit Unicode mappings and geometrically placed invisible text, rather than embedding an entire CJK typeface only to hide it. Qualify this independently in the selected readers; it is not accepted just because a PDF viewer opens the file. Word-only geometry produces word-level selection claims, not fictional accurate per-character selection.

Unknown visual regions have no invented text. Optional text-confidence filtering changes only semantic admission and must report omissions. Default admission preserves all supplied, valid OCR text, with unreviewed provenance; it does not suppress low-confidence searchable text silently.

Track every span's owner (`visible_tounicode`, `actualtext`, `invisible`, `unmapped`) in the report. Whitespace, line breaks, tables and reading order require explicit tests. Preserve numeric punctuation and original line-end hyphens. Optional normalized search text can exist in a sidecar, but must not be injected as duplicate PDF text.

### 6.3 Vertical and complex-script handling

Horizontal kana is an early end-to-end gate, not deferred until after an ASCII release. Vertical Japanese is a separate v1 gate covering column order, punctuation orientation, ruby, small kana and mixed inline Latin/numbers. Use qualified horizontal/vertical font wrappers and metrics as appropriate; share underlying font bytes where possible. The traced source determines each visual form. Do not rotate all punctuation according to a generic rule after it has already been traced in the correct appearance.

Combining sequences, ligatures, RTL and contextual scripts must be representable in the normalized schema from day one. Full script-specific reconstruction is qualified only as demonstrated. An unsupported segmentation or shaping situation falls back visually without transliteration. ActualText/reading-order support is verified in independent extraction engines, not assumed from specification validity.

### 6.4 Images, masks and codecs

Use existing PDF-compatible codecs. Initial required codecs are Flate and pass-through JPEG where appropriate; a qualified CCITT Group 4 encoder is preferred for bi-level masks. Do not ship a new CCITT implementation merely to close a milestone. MRC can use Flate masks until a reusable encoder is qualified.

JBIG2 is optional, disabled by default in v1 and never required for reconstruction. If subsequently added, accept only a mode whose decoded mask is checked byte-for-byte against the input mask. Prohibit lossy symbol substitution in all production presets; a configuration string saying `lossless` is not sufficient evidence. Foreground mask exactness does not excuse lossy segmentation upstream.

Keep original bit depth/colour in protected and fallback patches unless an explicit output policy authorizes a measured change. Do not turn anti-aliased gray receipt ink into 1-bit black simply because a monochrome codec is smaller. Avoid seams, halos, doubled ink and incorrect alpha compositing at patch edges. Merge overlapping fallback patches to prevent double painting.

### 6.5 Document features and publication

Initial output is ordinary PDF 1.7. PDF/A is deferred behind a separately validated profile; do not advertise PDF/A just because fonts are embedded. Searchable output is not a PDF/UA claim.

For supported PDF inputs preserve page count, ordering, physical sizes, crop/rotation behaviour, safe metadata and bookmarks. Existing native pages and their required resources pass through without visual change. A mixed PDF with unsupported forms, annotations, attachments, layers or document-level structures must be rejected or passed through as an entire document; never silently drop those features while reporting success. Host-based integration may preserve more features than the standalone initial PDF adapter, and reports must distinguish that support.

Signed PDFs are rejected for reconstruction unless explicitly authorized as a new derivative; never claim a rewritten document retains a valid original signature. Encrypted inputs require explicit local credentials through a protected input channel, not command-line password text. Unsupported encryption returns a clear error. Never write passwords, OCR text or private page crops to default logs.

Always write a distinct output. Reject source/output aliasing, including hard links and symlinks. Build and verify a same-filesystem temporary PDF before atomic publication. Normal operation never overwrites an existing output without explicit permission. Atomic replacement preserves an existing output until the new candidate is fully validated.

Report/PDF publication involves two files unless `--result-dir` is used. Do not claim two independent renames are an atomic transaction. A result-directory mode atomically publishes a completed directory. For individual output files, the report records expected PDF hash and publication state; incomplete or orphaned sidecars cannot imply successful output. Report any publication failure, including whether the PDF was already committed.

The compact PDF must not secretly embed the original scan/document as an attachment, a hidden full-resolution page, unreferenced font baggage or historical incremental revisions. Source originals remain external and untouched. This utility is not a redaction/sanitization product.

## 7. Public library contract

The API names below are normative design names; exact Rust lifetimes and generic parameters are implementation details to settle at M0. Public types must have documented units, ownership and error behaviour.

| Operation | Input | Output / guarantee |
|---|---|---|
| `validate_page` | Raster binding, normalized OCR, physical geometry, policy | Typed validated input or explicit validation errors; no rendering changes |
| `analyze_page` | Validated page, cancellation/progress context | Segmentation, protection and source observations; no PDF mutation |
| `build_dictionary` | Bounded observation window, policy, asset store | Stable representatives and membership evidence; no semantic relabelling |
| `plan_page` | Page analysis, dictionary, codec/cost capabilities | Candidate page plans, coverage and fallback reasons |
| `verify_plan` | Original page and final plan, renderer adapter | Per-occurrence and composited-page measurements; no self-declared human verification |
| `encode_document` | Ordered chosen plans, font/PDF writer, output sink | Temporary PDF plus resource accounting; not yet a published output |
| `build_document` | Page source, OCR source, options, asset store, execution context | Bounded orchestration, final report and publishable verified artifact |

A host-neutral `PagePlan` provides ordered paint operations (`RasterPatch`, `GlyphRun`, `VectorArtwork`, `Background`) and semantic spans. A glyph asset is exposed as compound outlines plus metrics and an optional serialized font produced by the IO adapter. Font serialization is not needed by the abstract visual planner.

An embedding host must be able to provide page tiles rather than give the library access to arbitrary source paths. The core has no network dependency and no process spawning capability. The CLI provides file-backed implementations. GPU memory and OCR model initialization are not part of `scanweave-core`.

Errors are typed and include page/span context without default document text: `InvalidInput`, `BindingMismatch`, `MissingPhysicalGeometry`, `UnsupportedGeometry`, `UnsupportedDocumentFeature`, `DependencyUnavailable`, `ResourceLimit`, `Cancelled`, `ValidationFailed`, `PolicyUnsatisfied`, `IoFailure`, `PublicationPartial`. Warnings/fallback reasons are structured enums, not parsed free text.

Cancellation is observed between bounded work units, aborts child processes through the CLI adapter and leaves the original/output intact. No callback is invoked after the operation completes. A progress callback receives stage/page/work counts, never page text by default.

## 8. CLI contract

The following commands describe the **planned** interface, not an already installed program. The Tesseract invocation uses its documented character-box hOCR setting. [S03, S04]

### 8.1 Main workflow

```bash
# Existing OCR: no second recogniser and no font downloads.
tesseract scan.tif scan -l eng+jpn -c hocr_char_boxes=1 hocr
scanweave build scan.tif --ocr scan.hocr --ocr-format hocr --dpi 300 \
  --preset faithful --output scan.searchable.pdf --report scan.report.json

# Explicit page/OCR manifest, including documents with different page sizes.
scanweave build --bundle document.bundle.json --preset book \
  --output book.compact.pdf --work-dir .scanweave-work --resume

# Optional convenience wrapper; only this route invokes local OCR.
scanweave build receipt.png --ocr-engine tesseract --languages eng \
  --dpi 300 --preset receipt --output receipt.searchable.pdf

# Prepared scans plus normalized OCR from any provider.
scanweave build --bundle provider-output.bundle.json --output output.pdf

# Explicit exact-sample preservation rather than vector reconstruction.
scanweave build scan.tif --ocr scan.hocr --dpi 300 --preset exact \
  --output scan.exact.pdf
```

Languages are used only for an explicitly invoked OCR engine. No language setting can transform the visual source or substitute a font. Example DPI 300 is explicit operator input, not the default for unknown images.

`build` requires exactly one positional source or `--bundle`. `--ocr` and `--ocr-engine` are mutually exclusive. An image stack's page-to-OCR map must be explicit; equal file counts alone do not establish correspondence. A document without usable OCR requires explicit `--allow-unsearchable`, and its report must say it is not fully searchable.

### 8.2 Commands

| Command | Contract |
|---|---|
| `build` | Produce a new verified PDF using source images/PDF and bound OCR. |
| `prepare` | Create a canonical raster/OCR bundle from supported sources; preserve source provenance. Optional OCR invocation only by explicit flag. |
| `inspect` | Inventory input or output: page types, geometry, fonts/images, semantic owners, coverage, resource bytes and unsupported features. |
| `verify` | Compare output with the source bundle/report; run selected installed validators and return a measured status. Missing requested validators are not a pass. |
| `doctor` | Report compiled features, executable/model versions, hashes and supported adapters without network access. |
| `bench` | Development/qualification command for an explicit corpus manifest; no hidden network or corpus download. |

### 8.3 Presets and controls

| Preset | Intended policy |
|---|---|
| `faithful` (default) | Hybrid reconstruction; conservative shape checks; preserve paper appearance and source colour; no cleanup; no lossy fallback/foreground coding. |
| `receipt` | Faithful plus original-sample protection for amounts/identifiers and uncertainty margins; preserve faint/low-resolution ink and barcodes. |
| `statement` | Faithful plus conservative financial/table data protection; no punctuation normalization or data inference. |
| `book` | Faithful plus bounded cross-page dictionary reuse; preserve historical forms, margins, paper and page structure. |
| `compact` | Same foreground/content protections; explicitly permits qualified background/photo downsampling and lossy coding. No text-resolution reduction. |
| `exact` | Raster preservation of canonical decoded source samples, plus supplied OCR; no tracing, lossy recoding, cleanup, deskew or approximate decomposition. |

Primary controls: `--mode auto|reconstruct|mrc|raster`, `--preset`, `--effort fast|balanced|max`, `--dpi`, `--pages`, `--jobs`, `--memory-mib`, `--work-dir`, `--resume`, `--report`, `--protected-regions`, `--corrections`, `--target-kib`, `--require-target`, `--require-vector-coverage`, `--require-savings`, `--result-dir` and explicit metadata/derivative authorization policies.

`auto` minimizes actual bytes over qualified candidates. `reconstruct` prefers qualified vector coverage and may be larger; it still permits safe raster fallback. There is no production `force-everything-to-vector` escape hatch. `--require-vector-coverage` rejects a result below the requested measured fraction; it never disables fallback. `--require-savings` is measured relative to the explicitly reported searchable baseline by default; the source-file ratio is a different metric.

Advanced TOML controls include dictionary window, candidate-count/curve limits, validation policy, photo quality and background resolution. Ship named presets rather than dozens of required flags. Unknown config keys, unsupported options and contradictory combinations are errors. Command-line values override the selected preset, and the resolved complete policy is validated and hashed. `exact` plus any lossy/vector/cleanup setting is a conflict, not a silently weakened exact mode.

Production numeric thresholds are versioned policy, not unlogged command-line magic. Lowering validated foreground safety thresholds marks a run `custom_unqualified`; it cannot keep a qualified preset label. The agent must not expose a shortcut that converts a safety check failure into success.

### 8.4 Exit codes and streams

| Code | Meaning |
|---|---|
| 0 | Complete output satisfies requested predicates. Legitimate raster fallback may be present and is reported. |
| 2 | Usage, schema, binding or unsupported-input error. |
| 3 | Required local dependency/model unavailable. |
| 4 | Resource, processing, IO or publication failure; report commit state. |
| 5 | Quality validation or an explicit savings/coverage/size predicate failed; do not publish the rejected candidate. |
| 130 | Cancelled/interrupted. |

Human progress goes to stderr. `--json` selects machine-readable structured events/results, without progress interleaved into JSON. Default logs contain IDs/counts, not OCR text or pixel crops. Refusing a lower-quality candidate and selecting a valid baseline is a successful build; it is not a reconstruction success claim.

## 9. Resources, jobs and reproducibility

Default limits are in `defaults.toml`. Start with two workers, a 1,024-MiB managed memory budget, a 64-page dictionary window, explicit page-pixel and scratch limits, and deterministic bounded candidate counts. These are limits/design targets, not measured throughput claims. A memory budget must account for decode buffers, candidate rasters, final validation and font/PDF buffers, not just source page bytes. Report OCR subprocess memory separately and combined where supported.

A 300-page book must not require all page rasters or fonts in memory. Spool immutable page analyses and dictionaries to a job-local content-addressed store. Avoid unlimited per-page JSON copies of pixel arrays. Resource exhaustion degrades a region to a valid baseline where possible; otherwise it stops with a precise resource error. It never silently downscales text to fit RAM.

The job key includes source content, normalized OCR, corrections/protection, resolved policy, toolchain/build ID, dependency/model versions, canonicalization rules and relevant renderer versions. Resume cannot reuse a previous result when any of these change. Stage manifests record exact input/output hashes. Completed artifacts are immutable; partial writes are distinguishable and ignored on resume.

Dictionary representatives, font IDs, object order, resource order, timestamps and compression settings must be deterministic for the pinned platform/toolchain. Parallel completion order must not choose the winning medoid. Reproducibility across different platforms is measured separately and not claimed automatically. Fixed timestamps apply to deterministic output; wall-clock timing stays in the separate report.

Do not build a generic workflow engine. A small fixed stage machine (`validated → analyzed → planned → encoded → verified → committed`) with per-page/window hashes is sufficient. Crash/cancellation tests cover each transition.

No network at processing time, including model auto-downloads, HTML external entities, remote image references or font discovery. An explicitly separate setup step may install approved dependencies; runtime `doctor` reports what exists and fails usefully when something is missing.

Scratch directories are private and scoped to one job. Avoid symlink traversal, path escape, XML entity expansion, decompression bombs and unbounded font/path recursion. Spawn executables with argument arrays, not shell command strings containing document data. An OCR document is data, never an instruction source. Default cleanup removes intermediates after success; debug retention is opt-in and warned as sensitive. Do not promise forensic secure erase on SSDs.

## 10. Reporting contract

Every requested report includes schema/version, run/build/config IDs, source/output hashes and sizes, source geometry, OCR provenance, pages completed/preserved, semantic coverage, vector/raster coverage, protected-region counts, fallback reasons, byte breakdown, resource/elapsed measures, validation results and publication state.

Report two vector coverage denominators: (1) all detected text ink, including protected and rejected units; (2) independently predeclared eligible text ink. Also report occurrence counts. Never create an impressive percentage by excluding all failed glyphs from eligibility after reconstruction.

Per-page and per-region reasons include: `protected`, `low_contrast`, `uncertain_segmentation`, `textured_background`, `overlap_nontext`, `trace_error`, `topology_change`, `placement_error`, `dictionary_budget`, `outline_budget`, `font_overhead`, `raster_smaller`, `unsupported_geometry`, `unmapped_ocr`, `validation_failure` and `native_passthrough`.

Use independent fields: `structure_status`, `visual_status`, `semantic_transport_status`, `ocr_accuracy_status`, `compression_status`, `reconstruction_status` and `publication_status`. Examples of honest states are `PASS`, `FAIL`, `NOT_RUN`, `UNQUALIFIED`, `UPSTREAM_UNREVIEWED` and `NO_GAIN`. A structural pass cannot be promoted to visual or OCR accuracy pass. A report template is not an executed report.

Text/crop-level audit output is opt-in. Summary reports should avoid exposing financial text, private filesystem paths or source metadata unnecessarily. Font dictionaries and diagnostic crops derived from private documents are private data too.

## 11. Delivery and acceptance

Use `QUALIFICATION.md` for test definitions, metric formulas, corpus splits, performance measurements and release gates. Use `AGENT_BRIEF.md` for the implementation/review loop and the first authorized work package.

The first public artifact is a tested CLI/library slice, not a GUI. A v1 release requires real original-shape font reconstruction, searchable transport, safe fallback, horizontal and vertical Japanese gates, representative receipt/statement/book results, independent readers and bounded long-document operation. A safe all-raster utility can be useful but must not be advertised as the ClearScan-style engine.

Maintain a concise ledger with milestone state, exact revision, tests/commands, failed attempts, reviewer findings, unresolved coverage and accepted decisions. Freeze corpus, thresholds and upstreams before holdout evaluation. No model/agent may self-promote its evidence to independent human verification.

### 11.1 Decisions deliberately left to bounded M0 probes

Only these implementation details are unresolved: exact upstream versions/toolchain; VTracer compound-contour adapter route; the selected reusable CCITT encoder (Flate is an acceptable initial fallback); precise embedded-font/vertical/glyphless interoperability demonstrated against the chosen reader versions; and calibrated operating thresholds on development data.

The coding agent must resolve these through small executable probes, record evidence and stop at the M0 gate. These are not permission to redesign the product, postpone kana indefinitely, import an unreviewed copyleft implementation, or build months of infrastructure before demonstrating a reconstructed searchable glyph.

## Appendix A. Exact interchange validation details

`schemas/bundle.schema.json` is the document manifest: ordered page entries reference normalized OCR-page files by hash and original source IDs/page indices. Each normalized page references its canonical single-page raster asset by file/pixel hash. An importer of multi-page TIFF creates per-frame canonical assets while preserving the original TIFF/source-frame association. Validate all references before reconstruction; filenames or array positions are not the only identity check.

Pixel-hash v1 preimage is ASCII header `SWRASTER1\n{format}\n{width}\n{height}\n{colour_tag}\n{icc_hash_or_dash}\n` followed by packed sample bytes. Width/height are unsigned base-10 integers without leading zeros. ICC hash is lowercase SHA-256 or `-`. Samples are row-major top-to-bottom, without row padding except the last partial byte of each `mono1_msb` row. Mono uses 0=black, 1=white, high bits first, with unused low bits set to zero; 16-bit channels are big-endian; RGB(A) channels are interleaved in name order, alpha is straight/unpremultiplied. SHA-256 covers header and sample bytes. `file_sha256` covers the exact asset bytes. Hash the entire referenced ICC profile separately when `colour_tag=icc`; null ICC with that tag is invalid. No newline/prefix ambiguity is permitted.

A schema can describe pixel formats that a particular adapter has not qualified. The runtime must report unsupported formats instead of converting a 16-bit/alpha source silently into 8-bit opaque data. The initial adapter may support only opaque gray8/rgb8; exact mode must reject other inputs until a preserving path is qualified. Preserve colour metadata and transformations explicitly.

JSON Schema is only the first validation layer. The semantic validator must additionally enforce: invertible finite affine matrices; transformed raster extent matching declared physical extent; consistent source geometry; total pixel and byte budgets; per-string UTF-8 byte limits (schema string lengths alone are insufficient); polygon shape/containment and boundary tolerances; unique IDs; complete and nonduplicated reading-order references; valid symbol byte ranges at Unicode boundaries; no illegal overlapping symbol ranges; consistent parent/ruby references with no cycles; confidence-value ranges when a defined scale is supplied; existing referenced assets with matching hashes; and root-contained paths without symlink escape.

Reject NaN/infinity, duplicate JSON object keys and unknown fields. Reject unrecognized major schema versions. Before changing a public field or meaning, add migration/version tests; do not silently reinterpret a v1 file. Optional fields cannot be used to smuggle remote references or processing instructions.
