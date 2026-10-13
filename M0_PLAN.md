# M0 Implementation Plan — ScanWeave feasibility and contracts

Status: DRAFT — submitted for independent review (deepseek-reviewer). No implementation before approval.
Authority: `reference/scanweave-spec-v0.1/{SPEC,QUALIFICATION,AGENT_BRIEF}.md`, `defaults.toml`, schemas; operator conditions of 13 Oct 2026.
Scope: M0 only. Stop at the M0 gate. No M1 infrastructure.

## 1. Outcome expectation (honest ceiling)

The benign corpus is **not mounted**. Per AGENT_BRIEF and operator condition 5, real-document
evaluation is recorded as blocked, never substituted by synthetic results. Therefore the best
achievable M0 outcome is **PROVISIONAL** ("feasibility demonstrated, corpus/independent
qualification blocked"). PASS is reserved for a rerun with the corpus mounted or an explicit
operator decision that synthetic-only evidence suffices — the agent cannot grant that.
FAIL is declared on any fidelity violation, invalid font/PDF output, or architectural
contradiction found by probes or review.

## 2. Environment facts (recorded 13 Oct 2026, this machine)

| Item | State | Consequence |
|---|---|---|
| OS/CPU/RAM | Ubuntu 24.04 x86_64, 24 cores, 78 GiB | Record in all reports; pinned environment |
| Rust toolchain | **absent** | Install via rustup in setup phase; pin exact version in `rust-toolchain.toml`; commit `Cargo.lock` |
| Network (setup) | rustup 200, sparse index 200, static.crates.io 200, github 200, apt 200 | Approved dependency installation allowed in setup phase only |
| Network (runtime) | probes run offline after setup | matches `execution.network = false` |
| Poppler | 24.02.0 (`pdftotext`, `pdftoppm`, `pdfinfo`) | independent extraction + render engine #1 ✓ |
| fontTools | 4.46.0 | independent font parser ✓ |
| qpdf | **absent**, apt candidate 11.9.0 | install in setup phase |
| tesseract | **absent**, apt candidate 5.3.4 | optional-OCR-subprocess; install but M0 probes use supplied synthetic OCR only |
| ots-sanitize | **absent**, not in apt | build from source (best effort); if not feasible → `NOT_RUN`, never a pass |
| 2nd independent PDF engine | **absent** | REQUIRED route: PDFium (Apache-2.0) via a pinned `pdfium-binaries` release behind `pdfium-render` ( licence-noted fallback: PyMuPDF, AGPL, qualification-only black box — still an engine independent of Poppler). If no second engine can be provisioned, the affected semantic-transport proofs are recorded `NOT_RUN` (never partial pass) and listed as an explicit PROVISIONAL cause in `M0_REPORT.md` |
| System fonts for synthetic scans | DejaVu, Liberation, IPA Gothic, fonts-japanese-gothic, WQY | qualification-harness-only sources; font files are NOT committed to the repo |
| git | present | repo init in WP-A |

Validator discipline: an unavailable validator is `NOT_RUN` in every table it was required for.
No check may be reported as passed by an absent tool.

## 3. Repository layout (created in WP-A)

```
/data/coding/scanweave/            repo root (git init; spec.md + zip committed as received)
  reference/scanweave-spec-v0.1/   extracted packet, SHA256SUMS-verified
  M0_PLAN.md  LEDGER.md  TOOLCHAIN.md  UPSTREAMS.lock.toml  rust-toolchain.toml
  Cargo.toml                       workspace, three production crates
  crates/scanweave-core/           types, validation, hashing, planning interfaces (no fs/net/proc)
  crates/scanweave-io/             image/OCR import, hOCR reader, font/PDF serialization adapters
  crates/scanweave-cli/            stub only (binary prints version; no commands — M1 scope)
  qualification/                   dev-only harness: fixture generation (Python), probe driver,
                                   fixtures/negative/, fixtures/positive/, measurement scripts
  probes/m0-font-pdf/              the vertical probe binary (workspace member, dev scope)
  M0_REPORT.md                     written in WP-G
```

## 4. Work packages

### WP-A — Repository, toolchain, validator inventory
- git init; commit packet + this plan; `.gitignore` for target/ and generated art.
- Install rustup; pin exact toolchain in `rust-toolchain.toml`; record `rustc/cargo` versions.
- `apt-get install qpdf tesseract-ocr` (setup phase); record versions.
- Best-effort OTS build from pinned source; else `NOT_RUN` with the concrete blocker.
- Provision engine #2 (PDFium preferred; PyMuPDF fallback with licence note).
- `TOOLCHAIN.md`: full inventory (items of §2 with final versions and statuses).
- Done when: `cargo --version` pinned; every §2 row has a final status.

### WP-B — UPSTREAMS.lock.toml
- Resolve and pin exact versions/revisions for:
  - runtime: `vtracer`, `kurbo`, `write-fonts`, `read-fonts`, `pdf-writer`, `image`,
    `imageproc`, `serde`, `serde_json`, `thiserror`; plus transitive-licence audit of these.
  - qualification-only: qpdf, Poppler, PDFium (or PyMuPDF), fontTools, ots-sanitize, Python,
    fixture-generation font set (system-installed, never committed).
  - optional OCR subprocess: tesseract (version + executable hash).
- For each crate: registry identity, exact version, `.crate` sha256, licence(s) + notice hash,
  selected features, usage scope, platform status (linux-x86_64 verified by build).
- No other upstream version is used in qualification; upgrades require a new lock entry.
- Done when: lock file complete; `cargo build --locked` succeeds against it.

### WP-C — Normalized types, binding, validator, negative fixtures (tests first)
- Commit authoritative schemas under `reference/` (done in WP-A) — they are the contract;
  core types mirror schema 1.0 field-for-field via serde, with `deny_unknown_fields`.
- Implement in `scanweave-core` / `scanweave-io`:
  - pixel-hash v1: `SWRASTER1` preimage exactly per SPEC Appendix A (format header, packed
    samples, mono1_msb bit order, 16-bit BE, straight alpha); `file_sha256` separately.
  - binding check: page binds to file hash AND pixel hash; mismatch → `BindingMismatch`.
  - hOCR reader: char-box granularity when present (`hocr_char_boxes`), honest word-level
    otherwise; UTF-8 byte ranges computed on scalar boundaries; no fake equal-width chars.
  - coordinate policy: pixel-edge continuous coordinates, half-open rects; affine
    `raster_to_page_pt` validation (finite, invertible, extent-consistent).
  - semantic validator: unique IDs; reading-order completeness/no duplicates; symbol ranges on
    Unicode boundaries, non-overlapping; polygon size/containment bounds; path containment
    (no traversal/URI/symlink escape); budget limits; NaN/Inf rejection; duplicate JSON key
    rejection (custom parser hook).
- Tests written BEFORE implementation (must fail first), stable IDs:
  - IN-01 matching image+hOCR imports, no OCR invoked.
  - IN-02 same dimensions, different image hash → rejected, nothing published.
  - IN-03 stale crop/rotation binding → unsupported mapping rejected, never shifted silently.
  - IN-05 absent DPI and no physical extent → `MissingPhysicalGeometry`.
  - IN-06 malformed XML / path escape / oversized input → bounded typed rejection, no network,
    no entity expansion.
  - wrong page pairing: bundle page ↔ ocr-page hash mismatch → rejected.
  - bad UTF-8 ranges (mid-scalar split) → rejected; extended-grapheme split → rejected.
  - six negative schema fixtures (operator condition 2) validated at TWO layers: (i) an actual
    Draft 2020-12 JSON-Schema validator (Python `jsonschema`, qualification harness) — serde
    semantics alone diverge from JSON Schema (patterns, uniqueItems, enums); (ii) the Rust
    typed layer with `deny_unknown_fields`. Each fixture is a committed JSON plus a test
    asserting rejection with a typed error: NF-01 unknown property; NF-02 malformed sha256;
    NF-03 zero physical width; NF-04 undersized polygon; NF-05 duplicate reading-order
    reference; NF-06 unsupported direction.
  - positive control: the packet example passes schema validation — STRUCTURAL ONLY (its hashes
    are zero placeholders and its asset is absent); it is explicitly not an IN-01 binding pass.
  - word-granularity honesty (IN-04, partial): a word-only fixture imports with word-level
    units, no equal-width invented symbol boxes, no fake per-character geometry.
- Done when: all WP-C tests red→green and merged in small commits.

### WP-D — Vertical probe (raster mask → font → searchable PDF → independent checks)
Synthetic scan generation (qualification harness, Python+PIL, system fonts, never committed
fonts): ~300-dpi-equivalent rasters containing:
  1. Latin `8` and `6` (two shapes, both with true counters);
  2. `ガ` — multi-component kana with detached dakuten marks;
  3. touching `fi` — one visual unit, multi-codepoint string; plus one supplementary-plane
     scalar (e.g. `𝐀`) for UTF-16 ToUnicode evidence;
  4. `8` on coloured paper (counter holes must stay transparent);
  5. degraded/anti-aliased variant of `8` (visual-variant retention evidence).
Each raster ships with a normalized OCR JSON (some labels deliberately wrong — see WP-E).

Geometric error budget (SPEC §5.5) — operationalized as versioned policy
`qualification/policy/m0-probe-1.toml` (recorded before implementation, referenced by all
probe measurements):
  - ONE total budget `B = 1.0` source pixel (consistent with `max_edge_max_px` in
    `defaults.toml`), defined in source pixels and converted per unit to font units as
    `B_font = B_px × (units_per_em / em_px_of_unit)` at upem 2048 using the unit's own
    placement scale; the derivation is recorded, never assumed.
  - stage allocation: VTracer simplification ≤ 0.50 px; cubic→quadratic conversion ≤ 0.25 px;
    font quantization + placement ≤ 0.25 px. The tracer's tolerance parameter is derived from
    its allocation, not set independently; the converter and writer receive the remaining
    budget explicitly.
  - guard: per-glyph MEASURED combined symmetric edge error against the source crop must
    satisfy p95 ≤ 0.5 px and max ≤ 1.0 px; a per-glyph stage-wise error decomposition
    (mask→traced path, traced path→converted path, converted path→quantized rendered font)
    is recorded for EVERY traced glyph — accepted, near-budget and rejected alike, so the
    guard cannot be satisfied by survivor cherry-picking — making independent budget
    consumption detectable.
  - known probe risk (SPEC §11.1 class): if VTracer's simplification tolerance cannot be
    parameterized from the budget allocation, that is a concrete recorded blocker, not a
    reason to silently decouple the stages.

Rust probe pipeline (`probes/m0-font-pdf`, logic destined for core/io split in M1):
  decode → foreground mask (threshold) → connected components (`imageproc`) → group into visual
  units per OCR symbol observations (marks attached) → `vtracer` trace per unit under its
  budget allocation → contour orientation/winding normalization → `kurbo` cubic→quadratic
  conversion under its allocation → `write-fonts` TrueType build (glyf/loca/head/hhea/hmtx/
  maxp/cmap-minimal/name/OS2/post; unhinted; `.notdef`) → `pdf-writer` assembly:
  Type 0 / CIDFontType2 with FontDescriptor/FontFile2, explicit CIDToGIDMap stream, /W and /DW
  widths, deterministic subset naming, ToUnicode CMap with UTF-16BE, per-unit `Tj` placement
  transforms taken from source geometry (no re-typesetting), background handling for the
  coloured-paper page (no white-out rectangles).
Independent verification of every emitted PDF:
  - `qpdf --check` structural pass;
  - fontTools parse: glyph count, contour counts, winding of outer/inner contours
    (hole = opposite winding, not white fill);
  - ots-sanitize if built (`NOT_RUN` otherwise);
  - extraction via Poppler `pdftotext` AND engine #2: strings must match supplied OCR exactly;
  - render via `pdftoppm` AND engine #2 at native + 2× DPI; per accepted unit the FULL
    `dev-initial-1` policy metric set is measured against the source crop: ink IoU ≥ 0.98;
    symmetric edge p95 ≤ 0.5 px, max ≤ 1.0 px; normalized local MAE ≤ 0.02; component/hole
    topology stable at threshold offsets −0.05/0/+0.05; no unowned source mark in the probe
    page (ownership map check);
  - coloured-paper counter check: pixels inside counters equal background colour, not white.
- Done when: every probe artifact passes available independent checks; failures recorded.

### WP-E — GID/CID/Unicode separation proofs (reviewer focus area)
CID allocation contract (SPEC §6.1): the encoding allocation key is
`(visual_glyph_id, semantic_string, writing_mode, required_metrics)` — carried verbatim in the
probe data model. `writing_mode` and `required_metrics` are explicit fields fixed to
horizontal / one metric value for M0; CID allocation is implemented and asserted as a pure
function of all four parts, and additional writing-mode/metric variants are representable
(deferred) without schema change. Unicode scalar value, CID and GID are never equated.
Committed probe fixtures + extracted evidence:
  - E1 same outline, two CIDs: shape `8` referenced by CID-A (ToUnicode `8`) and CID-B
    (ToUnicode `6`). Proven from the FONT/PDF GRAPH, not inferred from pixels:
    (i) CIDToGIDMap inspection shows N CIDs → ONE GID (glyph reuse, not outline duplication);
    (ii) content-stream inspection shows both CIDs actually painted at their placements;
    (iii) renderings pixel-identical; (iv) extraction yields both distinct strings.
  - E2 different outlines, same string: two CIDs → two DISTINCT GIDs → one ToUnicode string
    (`8` regular + degraded variants); CIDToGIDMap + glyph-table inspection proves the two
    GIDs; extraction yields `8` twice. Converse of E1 per SPEC §3.
  - E0 (test-first, WP-E entry condition): the four-part key's pure-function property is an
    executable unit test — each of the four components is mutated in turn and the test
    asserts CID separation vs. dedup behaviour accordingly, before the probe relies on it.
  - E3 VS-01 page: observed `8` labelled `6` by OCR stays visibly `8` — measured with the
    `dev-initial-1` policy metrics (IoU ≥ 0.98, edge p95 ≤ 0.5 px / max ≤ 1.0 px, MAE ≤ 0.02,
    stable topology, no unowned mark) — while extracted text is `6` with unreviewed provenance
    recorded. This is THE demonstration that OCR mistakes do not become visual mistakes.
  - E4 ligature/multi-codepoint: `fi` unit → ToUnicode `fi`; supplementary scalar → correct
    surrogate-pair CMap entry.
  - E5 kana: `ガ` traced as one multi-component unit → extracts `ガ` with no normalization,
    no transliteration, no generic-font substitution.
  - E6 span/unit cardinality and semantic ownership (SPEC §3, §6.2): one semantic span covers
    MULTIPLE visual units; a second span is owned by an invisible text representation over a
    retained raster region — reusing the B0 glyphless-font path from WP-F, not a new fallback
    subsystem. Every span's owner is recorded from the §6.2 enum
    (`visible_tounicode` / `actualtext` / `invisible` / `unmapped`), and each admitted span
    extracts EXACTLY ONCE (no duplicate layers) — also asserted on the repeated-text B2
    document in WP-F (TX-03 partial).
  - E7 subset determinism: glyph/CID allocation order is stable across two runs (byte-equal
    font + PDF on pinned toolchain).
- Done when: E0–E7 evidence files (render PNGs, extraction dumps from BOTH engines, font/CIDToGIDMap
  dumps, content-stream excerpts, owner table) exist and match expectations; any mismatch is a
  FAIL input to WP-G.

### WP-F — Searchable raster control and measured baselines
- B0 searchable raster control, built by our own path: full-page canonical raster +
  glyphless-font invisible text layer using the same supplied OCR (SPEC §6.2 fallback font).
- B2 reconstructed probe output (WP-D artifacts over a small 2–3 page synthetic document with
  repeated text).
- B1 MRC via Internet Archive `archive-pdf-tools`: bounded install attempt (pinned commit,
  venv, leptonica build). If not feasible within the bound → blocked with exact reason;
  this is an expected PROVISIONAL contributor, not a failure of M0 feasibility.
- Measurements (recorded, no advantage claimed):
  - byte breakdown per output (writer instrumentation + independent bytecounts): font tables,
    CID/ToUnicode maps, content streams, images, xref/object overhead;
  - `source_ratio = O/S`, `baseline_ratio = O/B` per output; PDF-only vs package sizes;
  - render comparison at native + 2× DPI; extraction transport comparison vs supplied OCR;
  - runtime verification cost measurement (QUALIFICATION §9 requirement for M0).
- Done when: measurement tables exist for every candidate that built; blocked items documented.

### WP-G — Ledger, report, hypothesis, exit decision
- `LEDGER.md`: per-WP entries (revision, tests/commands, failures, reviewer findings).
- `M0_REPORT.md` per AGENT_BRIEF checklist: exact revision + dirty-state disclosure; files and
  architectural boundaries; commands + exit codes + artifact hashes; raster/reconstructed
  samples and extraction output; wrong-label side-by-side evidence (E3); pilot baselines or
  precise blockers; resource/timing separated from OCR and setup; reviewer findings + response;
  explicit **PASS / PROVISIONAL / FAIL**.
- Product-value hypothesis preregistered (one of QUALIFICATION §7's two options, with the
  stated subset and thresholds), plus M1/M2 plan sketch and explicit unresolved list
  (SPEC §11.1 items still open after probes).
- Exit-state vocabulary: the operator's PASS/PROVISIONAL/FAIL table governs the M0 decision;
  the ledger additionally records the QUALIFICATION §1 vocabulary equivalent (PROVISIONAL ≈
  `HOLD`) so evidence stays machine-consistent. A missing second engine or blocked MRC makes
  the affected proofs `NOT_RUN` and is listed as a PROVISIONAL cause — never partial pass.
- Final independent review (deepseek-reviewer) of implementation + artifacts BEFORE the M0
  decision is recorded. Reviewer has blocking authority; unresolved blockers → HOLD.

## 5. M0 behavior-test subset (stable IDs; full suites come at M1+)

| ID | M0 scope |
|---|---|
| IN-01/02/03/05/06 | WP-C import/binding/geometry tests (tests-first) |
| IN-04 (partial) | word-only fixture: word-level units, no fake per-character geometry (full word-path planning is M2) |
| NF-01…NF-06 | six negative schema fixtures, executable at JSON-Schema AND typed layers |
| VS-01 | E3 wrong-label preservation evidence, measured with dev-initial-1 metrics |
| VS-06 | coloured-paper counter-hole evidence (E-page 4 + winding check) |
| TX-01 | E1/E2 CID↔Unicode separation evidence, proven from font/PDF graph |
| TX-02 (partial) | ligature + supplementary-plane transport (E4); combining marks deferred to M1 |
| TX-03 (partial) | each span extracts exactly once; mixed visible/invisible owners (E6, B2) |
| TX-04 (partial) | kana extraction without normalization (E5); full-width set deferred |
| OP-04 (partial) | byte-deterministic repeat run (E7); multi-worker determinism deferred to M3 |

## 6. Non-goals for M0 (anti-scope)

No CLI commands beyond the stub; no dictionary/matching/medoids; no internal MRC; no PDF input
adapter; no protection heuristics; no corrections file; no deskew/cleanup; no resume/job store;
no report schema beyond minimal JSON; no vertical-writing mode; no ActualText path; no font
subsetting/splitting logic; no performance optimization. Each is first addressed in its
designated milestone (M1–M4).

## 7. Review protocol for this plan

This plan goes to `deepseek-reviewer` before any code. Revision 2 addresses the reviewer's
four blocking findings from the first plan review (operationalized error budget, four-part
encoding key, font-graph-based E1/E2 evidence, mandatory second engine) and adopts the
non-blocking recommendations (dev-initial-1 metrics in E3/WP-D, span-cardinality/owner proof
E6, IN-04/TX-03 partials, dual-layer schema validation, positive-control clarification,
state-vocabulary mapping, FontDescriptor//W//DW emission). Reviewer is asked to verify these
resolutions and to challenge especially: (a) the operationalized shared geometric error
budget (`m0-probe-1` policy); (b) whether the E1–E7 proofs demonstrate SPEC §3's three
identities and §6.1's four-part encoding key `(visual_glyph_id, semantic_string,
writing_mode, required_metrics)`, including glyph REUSE proven from the CIDToGIDMap rather
than inferred from pixels; (c) tests-first coverage of the operator's six conditions;
(d) scope leaks toward M1; (e) honesty of the PROVISIONAL ceiling and validator NOT_RUN
policy. Blocking findings must be resolved and re-reviewed before implementation starts.
