# M1-B: searchable multi-page documents, economical fallback, honest measurement

**Commit:** implementation frozen at `5462593`; review fixes at `358bada`,
`7855601`, `170236e`; deliverables at `85e1564`; operator-review corrections in
the following commits. **Status:** M1-B approved at `170236e`; the operator's
review of the pushed revision then found six implementation defects, all fixed
in this revision (see §0b).

## 0. N1 — root cause and fix (the M1-A open defect)

**M1-A's diagnosis was incomplete.** The M1-A report attributed the failure to
"PDFium hoisting invisible runs". Two bodies of evidence, both kept in-tree:

1. **Real-page A/B (the discriminator).** The M1-A build (binary from the
   accepted `650dafa` code) fails: PDFium extraction ends
   `...Page of 4.\r\nPlease pay within 30 days.\r\n1` — the fallback `1`
   appended after the page's last line, so `search("Page 1 of 4")` fails. The
   M1-B build passes with a **pixel-identical render** (0 differing pixels vs
   the M1-A build at 300 dpi) — same pixels, different text-layer geometry.
   Both facts are asserted permanently by `test_m1b_paint_fidelity.py`
   (native search + "owner label not hoisted to the end" + 0 px paint).
2. **Mechanism illustration** (`qualification/n1_experiments.py`, 5 variants).
   Stated scope: it isolates PDF-level mechanisms (mark granularity, rendering
   mode, inline-vs-last, baseline placement) on a synthetic one-line page with
   a Type1 font. It does **not** reproduce the real failure (the real page's
   owner CID references the empty placeholder glyph at the span-box height in
   a CID font), so the real-page A/B above is the discriminating evidence.

The mechanism consistent with both: **PDFium merges runs into a line by
baseline and sorts the line's characters by x.** The M1-A owner run was placed
on the OCR *polygon-box* bottom — ~1pt off the visible line's glyph-ink
baseline — so the label formed its own line, emitted after the rest, and
appeared out of order.

**Fix** (no visual change, verified pixel-identical): owner runs stay INVISIBLE
(`3 Tr`, they paint nothing) and are placed on the span's traced **ink
baseline** (`place_px` = the first unit's ink bbox), emitted INLINE in reading
order inside the text object, each with its own per-span `/ActualText`.

Intermediate approaches tried, measured, and rejected (provenance in the
commit history):
- *line-level `/ActualText` enclosing the whole line's runs* (the experiment's
  V1): passes both engines on the synthetic, but on the real page Poppler
  split the per-glyph runs inside the line mark into separate segments
  ("T\nota l a") — rejected.
- *visible owner runs on the paper-coloured placeholder*: the placeholder is a
  real filled box (the qualification harness rejects degenerate contours), so
  this painted an ink rectangle — caught by the p06 render diff and the winding
  gate — rejected.
- *collinear (degenerate) placeholder*: the harness flags degenerate contours
  by design — rejected.

**Verified:** `test_text_search.py` 49/49 pass (p10 page1 `Page 1 of 4` native
search now passes); M1-A vs M1-B renders of p10 page1 are **pixel-identical
(0 differing pixels)** — the owner run provably paints nothing.

## 0b. Operator review of the pushed revision: six defects found and fixed

An independent inspection of the pushed (approved) revision found correctness
gaps the M1-B tests did not cover. All six are fixed here, each with a
regression test (`regress_*` in `probes/m0-font-pdf/tests/m1b_behavior.rs`):

| # | Defect | Fix | Regression |
|---|---|---|---|
| P0 | Protected regions were discarded: `input_from_ocr_page` kept spans but dropped `protected_regions` (the internal OCR page hardcoded `vec![]`), so caller-specified financial protection was never honoured | `Input` carries `protected_regions`; `plan_regions` treats a protection polygon as having priority (SPEC §4.4): any unit within the contact margin of a protected box forces the region to raster with reason `Protected`, and the region box grows to cover the protected pixels so the patch reproduces them exactly | `regress_protected_amount_stays_raster` |
| P0 | The pixel binding was computed for reporting but never compared: `OcrPage::verify_binding` existed and was never called | The CLI (both OCR input forms) and the bundle path call `verify_binding` against the decoded canonical pixels before converting; `convert_parts` re-checks the declared hash itself (defence in depth) | `regress_pixel_binding_mismatch_is_refused` |
| P1 | Page geometry came from `policy.dpi` instead of the page's affine, so a 600 dpi scan was laid out at the bundle's 300 dpi default | `PageTransform` is derived from the normalized page's `raster_to_page_pt` and drives every placement (MediaBox, patches, glyph runs, owner baselines); skew is refused as unsupported geometry. Verified pixel-identical on the 300 dpi fixtures | `regress_geometry_uses_the_page_affine` |
| P1 | `min_ink_iou` (0.98) was never read: auto selected by bytes without any fidelity check | Per-occurrence analytical ink IoU (outline rasterized over the unit's crop vs the source ink mask — SPEC §4.2's mask definition on the candidate); **units below the threshold are not vectorized** — their region degrades to raster (`FidelityBelowPolicy`), so every emitted vector unit satisfies the policy; the report describes the *emitted* content (post-degradation min/mean, degraded count) and auto ranks the degraded reconstruction against the raster baseline by real bytes; `--min-ink-iou` is an explicit operator decision recorded in `qualification/policy/m1b-operating.toml` | `regress_min_ink_iou_is_enforced` |
| P1 | Shared CID deduplication was incomplete: `enc_index` was queried but never populated, so repeated (glyph, string) pairs minted new CIDs | The union now inserts into `enc_index` on first sight; doc4_repeat dropped 41,781 → 39,354 B | `regress_repeated_spans_keep_owners_and_cids_dedup` |
| P1 | Owner dedup compared OCR *text* instead of span id, so a repeated word whose second occurrence lacked visual components lost its owner | Dedup by `span_id` everywhere (the text-based lookup `owner_span` was removed) | same test (two identical-text spans keep both owners) |
| P2 | Auto reports could describe the wrong candidate: top-level image/content statistics came from the reconstruction even when the raster baseline was emitted | The document report's accounting follows the emitted candidate | `regress_auto_reports_the_selected_candidate` |

Also fixed while re-running everything: `report.font_bytes` was left at 0 by the
`convert`/`convert_parts` refactor (the PDF always embedded the font), and the
probe's `b0_raster.pdf` path re-enforces the pixel binding.

**Consequence of enforcing the fidelity policy (measured, not hidden):**
these antialiased fixtures' vector traces measure 0.80–0.996 per occurrence, so
at the SPEC's default 0.98 the below-threshold units are NOT vectorized — p16's
45 small-text units all degrade to raster (the report says so), and a
document-level run at 0.98 therefore selects the raster baseline by bytes.
Byte costs are honest in both policies — see §4.

## 1. Economical raster fallback

- `coalesce_patches` merges overlapping/adjacent patches transitively; each
  merged patch re-copies the full source rect of its union, so every emitted
  pixel stays byte-identical to the source (`m1b02`, sha per patch).
- **p14_noisy: 143,143B → 45,941B (204 image XObjects → 1)** via
  `scanweave build … --dpi 300` (CLI numbers; the committed deliverable
  `work/m1b-deliverables/noisy_auto.pdf` is 45,725B), zero new gate flips,
  p06's inherited visual metrics *improved* (pdfium IoU 0.9465→0.9564,
  MAE-ink 0.0453→0.0315).
- `--mode auto` ranks **both** candidates by actually-serialized bytes
  (`reconstruct` 45,941 vs whole-page searchable raster baseline 45,725) and
  picks the smaller; the report records both candidates with their bytes
  (`work/m1b-deliverables/noisy_auto.json`), so the evaluation is auditable.
  The tiny margin is expected: this page rasterizes fully either way; the
  ranking matters where pages are vector-dense (doc4_invoice: 54,592 vs
  192,737).
- No lossy background processing was added.

## 2. Multi-page CLI and document assembler

`scanweave build --bundle document.json [--mode reconstruct|auto] --output … --report …`

- Uses the existing normalized bundle contract (`verify_pairing` — hash-verified
  source+OCR binding per page) and the existing one-page path (`convert_parts`).
- `assemble_document` emits ONE PDF with N pages: **one shared font program**
  (document-wide `(shape, label)` encoding union in first-appearance order, so
  identical content across pages shares CIDs — measured: doc4_repeat is smaller
  than the same four pages built separately, by at least the duplicated fonts,
  `m1b04b`), deterministic object numbering, 16-bit CID bound, atomic publication.
- Per-page MediaBox (dimensions/rotation are the source page's), page order =
  bundle order, per-page and document-level report with coverage, search plan,
  bindings, and honest byte accounting (`image_xobjects`, `raster_encoded_bytes`,
  `content_bytes`, `font_bytes` — actual serialized sizes from an assembly
  side-channel, not estimates).
- Fixtures (hash-verified bundles): `doc2_min`, `doc4_invoice`, `doc4_repeat`,
  `doc4_mixed`, `doc10_mixed` — 2/4/10 pages composing the already-qualified
  single-page fixtures (invoice, repeated statement, noisy, decorative,
  horizontal kana).

## 3. Test evidence (all run in this tree)

| Suite | Result |
|---|---|
| `cargo test` | **53 passed, 0 failed** (46 inherited + 7 M1B) |
| `checks.py` E0–E7 e-proofs | **8/8 PASS**, zero gate flips vs accepted M1-A |
| `test_text_search.py` | **49/49 pass** (was 48/49; the N1 gate now passes) |
| `test_m1b_paint_fidelity.py` | all pass (owner runs paint nothing — 0 px outside patches in both engines; patch reproduces source above measured M1-A baselines; **explicit M1A-05 rule/stamp/barcode regression**: every contacted-region label stays searchable in both engines, exactly as the OCR has it) |
| `test_m1b_document_search.py` | **86/86 pass** (page count/order/dims, per-page native PDFium search incl. `Page N of 4`, kana intact, no duplicates, qpdf --check, report honesty) |
| `test_m1b_baselines.py` | all gates pass (see §4) |
| `test_corpus_adapter.py`, `test_subpixel_metric.py`, `validate_fixtures.py` | pass |
| Determinism | all 5 documents byte-identical (PDF **and** report) across repeat builds, both modes; single-page p10/p14/p16 identical (PDF+report); qpdf --check clean; OTS-sanitize clean |

## 4. External baselines (document level, actual bytes, policy-scoped)

Exact numbers committed at `work/m1b-deliverables/baseline_report.json`
(`qualification/test_m1b_baselines.py`, fails closed). Two scanweave policies
are shown because the fidelity gate is now real:

- **reconstruct@0.75** — the development measurement floor
  (`qualification/policy/m1b-operating.toml`): the vectorized pipeline the
  M1-B work is about.
- **auto@0.98** — the SPEC's default policy, enforced: the same documents with
  the fidelity gate active (this is what `scanweave build --mode auto` emits by
  default for these fixtures).

| Document | reconstruct@0.75 | auto@0.98 (enforced) | OCRmyPDF | IA MRC (per-page sum) |
|---|---:|---:|---:|---:|
| doc4_invoice | **48,836 B** | 168,727 B | 174,55x B | 154,867 B |
| doc4_repeat | **39,354 B** | 92,184 B | 93,30x B | 95,295 B |
| doc4_mixed | **78,242 B** | 117,089 B | 117,25x B | 115,042 B |
| doc10_mixed | **170,242 B** | 300,920 B | 306,80x B | 302,085 B |
| doc2_min | **61,967 B** | 74,957 B | 80,76x B | 72,472 B |

Reading this honestly (the earlier "1.2–3.2× smaller" framing was withdrawn):

- At the development floor, scanweave's vectorized output is **1.2–2.4×
  smaller than OCRmyPDF and IA MRC** at equal content, with ink IoU 0.79–1.00
  per page (OCRmyPDF reaches 1.0 by embedding the source losslessly).
- At the enforced SPEC default (0.98), scanweave's auto output is **lossless
  raster**, so it is smaller than OCRmyPDF everywhere (also lossless at
  `--optimize 0`) but **within ±9% of IA MRC's lossy MRC coding** — for
  doc4_invoice IA MRC is 8.9% smaller. That is expected: IA MRC is lossy on the
  noise-heavy pages, this pipeline is not ("no lossy background processing" is
  M1-B scope discipline).
- OCRmyPDF carries **English tessdata only** in this environment, so its kana
  page is not semantically comparable; byte sizes for it still count.
- OCRmyPDF embeds a creation timestamp, so its bytes vary ±10 between runs
  (shown as ranges); scanweave's and IA MRC's are deterministic.

Per-page ink IoU for scanweave's reconstruction ranges 0.7868–1.0 on these
fixtures — the same figures the M1-B report already published, now measured
against a policy that actually gates them.

## 5. Required demonstrations## 5. Required demonstrations

1. **Native PDFium search for `Page 1 of 4` on the mixed line** — PASS (single
   page and inside doc4_invoice page 1, both engines).
2. **Statement rows / financial tokens searchable in correct groupings** —
   PASS (`Total amount due: 1,234.56 EUR`, `INV-2026-0042`, `Amount`; native
   search per page on all documents).
3. **All architectural E-proofs green** — 8/8 (E0 four-part key, E1 outline/CID,
   E2 two GIDs one string, E3 wrong-label preservation, E4 UTF-16 transport,
   E5 kana, E6 span owners, E7 determinism).
4. **No unowned or multiply-owned ink** — 0/0 on every page and document (real
   pixel census in `convert.rs`).
5. **Noisy example auto-selects the economical candidate** — auto picks the
   raster baseline by real bytes (45,725B < 45,941B); both candidates recorded
   in the committed report.
6. **Four-page repeated text → one independently valid, searchable PDF** —
   doc4_repeat: 4 pages, one font, every page native-searchable, deterministic.
7. **Byte-identical output on repeated runs** — verified for all 5 documents
   (PDF + report), both modes, and for the three deliverables.
8. **Font validity / Poppler / PDFium+native search / qpdf** — OTS-sanitize
   clean, Poppler extraction correct and ordered on every page, PDFium native
   search per page, qpdf --check clean (all three deliverables).
9. **Existing visual FAILs recorded, not relaxed** — the inherited visual-gate
   failures and the p08 transport cardinality failure are unchanged (zero
   flips vs 392d42d/f5e5cb5/650dafa); thresholds untouched.
10. **Corpus holdout sealed** — not mounted, not accessed; the M1-B fixtures
    compose existing qualified single-page fixtures only.

## 6. Defects found and fixed during M1-B (by the regression run, before review)

- N1 root cause corrected as above (baseline, not rendering mode).
- The union CID remap remapped CIDs but not glyph indices → the document drew
  local indices into the global shape table (wrong glyph outlines; caught by
  an ink-IoU anomaly on a mixed-size document).
- The single-page B0 candidate was emptied by the `convert`/`convert_parts`
  refactor → all B0 search gates failed; restored (B0 keeps every span's text
  invisibly over the whole-page source patch).
- The owner-runs-before-patches experiment painted an ink box (placeholder is
  a filled contour) — rejected, not shipped.

## 7. Remaining limitations

- **L1 (engine-specific, measured):** a line whose spans are ALL raster
  fallback (no visible glyph on the line) still appends its owner labels at the
  end of PDFium's extraction order (the synthetic experiment's V0/V4 rows show
  the same effect on a Type1 font; the real all-fallback pages p06/p14 extract
  correctly in Poppler and as searchable text in PDFium). The M1-A failure —
  a MIXED line (visible spans + a fallback numeral) — is fixed. Recorded,
  not concealed.
- **L2:** single-image sources only in the bundle path (PDF/multipage TIFF
  sources return a clear error); multi-page stitching from one asset is not
  implemented.
- **L3:** auto selection is whole-document (reconstruct vs raster baseline);
  per-page hybrid selection is not implemented (the candidates are measured
  and recorded, so this is a policy extension, not a missing measurement).
- **L4:** document-level IA MRC is a per-page sum (the tool is per-page);
  OCRmyPDF is document-level.
- **L5:** the fixtures are synthetic (no benign corpus mounted — BLOCKED);
  all documents compose already-qualified single-page fixtures.
- **L6:** `work/m1b-deliverables/` was force-added past `.gitignore`; a
  regeneration is not auto-tracked (manifest must be re-committed).
- **L7 (new, from enforcing the fidelity policy):** at the SPEC's default
  `min_ink_iou = 0.98`, the vector traces of small antialiased text measure
  0.80–0.996 per occurrence, so `--mode auto` emits the lossless raster
  baseline for such pages (≈2–3× the bytes of the vectorized output). The
  policy is enforced rather than relaxed; `--min-ink-iou` is the explicit
  calibration knob and the calibration evidence/thresholds are recorded in
  `qualification/policy/m1b-operating.toml`. Vectorizing antialiased text
  inherently bolds the mask boundary (SPEC §4.2's note), which caps the
  achievable ink IoU below 0.98 for small glyphs.

## 8. Instruction

Submitted for the independent completion-gate review. The reviewer should
verify the §0 mechanism claim by running `qualification/n1_experiments.py`,
re-run every suite, confirm zero gate flips vs `650dafa`, and attempt to break
the document assembler (mixed page sizes, CID bound, determinism, search
duplication).
