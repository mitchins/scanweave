# M1-G — Document-Wide Canonical Font Reconstruction

**Result: experiment completed; qualification gates failed.** The opt-in
`canonical-experimental` profile is not eligible for default promotion. It
demonstrates document-supplied witnesses and vector replacement in an assembled
searchable PDF, but it does not demonstrate the required combination of
source-faithful restoration, safe fallback, and meaningful compression.

## Starting state and isolation

- Starting `HEAD`: `c6c4790fadabe5599acd225b030891257cfc20b2` (M1-F1).
- The five-file implementation diff from that base is SHA-256
  `85fdfa727a217e32f5c3a974f28a1a1ab08a2aa43f4280aaa78e1b922d8607c8`;
  fixture, oracle, result, and PDF hashes are in
  `qualification/experiments/m1g/fixture/m1g_hashes.json`.
- The profile remains opt-in. CLI default remains `faithful`; existing
  `faithful` and `clearscan` paths retain their previous donor selection and
  raster ownership behavior. The experimental residual and bounded
  page-stratified donor sample are restricted to `canonical-experimental`.
- Pre-existing untracked Adobe XI, M1-C research, and M1-F evidence directories
  were preserved. Only the ScanWeave files listed in this commit and the new
  `qualification/experiments/m1g/` artifacts were added.
- Converter input was the `input/` bundle. Pristine page renders and per-glyph
  geometry are under the evaluator-only `oracle/` directory and are not
  referenced by the converter manifest. The source font files were not copied
  into converter inputs.

## Implementation

The experimental profile collects page observations, passes a deterministic,
page-stratified sample of up to 32 sibling observations per OCR label into each
page reconstruction, and chooses a high-coverage observed donor for the
candidate outline. Each page still constructs its own prototype table before
the existing document font assembly; this is not yet a first-class global
`GlyphObservation` / `CanonicalGlyph` / `GlyphOccurrence` store. No consensus
reconstruction or missing-stroke fusion was implemented. The report records
observation, prototype, and occurrence details for auditing.

The exact-mask identity now includes width and height. The experimental
acceptance path can replace compatible healthy as well as damaged occurrences;
it preserves each occurrence's source Unicode. Its residual page representation
copies the source page and alters thresholded mask samples only for emitted
vectors, using a local ring median. That simple repair is intentionally
experimental: the ring has no guard against adjacent ink or protected detail,
and it does not implement a validated antialias fringe or explicit uncertainty
ownership model.

## Fixture and procedure

`qualification/experiments/m1g/generate_fixture.py` creates eight independently
rendered pages at 300 and 600 DPI using licensed DejaVu Serif, Liberation Serif
Italic, and IPA Gothic. The eight pages contain 600 OCR-symbol occurrences
(552 non-space characters, including 8 kana symbols), independently rendered
repeated Latin glyphs, an OCR `e`→`c` confusable, kana, and line art. Per-page
seeds and degradation code are fixed in the generator. The pristine render and
glyph boxes are separate from converter inputs.

Font provenance on the generation host: DejaVu Serif Book fontVersion 155320
(`8f2c103b…9c3cc7ab`), Liberation Serif Italic fontVersion 137625
(`eaeaf7f2…20249242`), and IPA P Gothic Regular fontVersion 198574
(`a63f6153…f5b8068`). Their license texts are included beside the fixture.

This is a useful positive-control fixture, not the full scientific design in
the mission: it does not establish the N=1/2/4/8/16 witness curve, a controlled
no-perfect-donor complementary-damage cohort, all listed hard negatives, or a
sealed statistical holdout. The fixture does not constitute real-document
validation.

300-DPI conversion command:

```sh
target/debug/scanweave-cli build \
  --bundle qualification/experiments/m1g/fixture/dpi300/input/document.json \
  --mode reconstruct --profile canonical-experimental --glyph-dictionary visual \
  --output qualification/experiments/m1g/fixture/dpi300/output/canonical-experimental.pdf \
  --report qualification/experiments/m1g/fixture/dpi300/output/report.json
```

The matching 600-DPI command substitutes `dpi600` for `dpi300`. Run
`qualification/.venv/bin/python qualification/experiments/m1g/evaluate.py 300`
or `600` to regenerate Poppler/PDFium renders and compare the current PDF to the
separate oracle. `hash_artifacts.py` records source, oracle, report, and output
SHA-256 values. Conversion is deterministic only by the repository's existing
E7 fixture; this profile was not converted a second time for a byte-equality
claim.

## 300-DPI result

The final PDF is 4,184,507 bytes, SHA-256
`9da8be9d2b147ea111d791efc9fb6b569e87c63288ece55643be8387d88b6e3d`. The
searchable-raster candidate emitted by the same run is 4,212,985 bytes. The
28,478-byte reduction is **0.68%**. The reconstructed PDF contains one
embedded 38,292-byte TrueType font, 65 glyph programs, eight full-page 1800×900
DeviceGray image XObjects, 4,079,502 encoded raster bytes, and 59,705 content
stream bytes, plus 7,008 bytes of document overhead. The
reconstructed candidate has 8 image references; it does not merge the distinct
page backgrounds. Raster payload remains about 97.5% of the file.

Of 552 non-space occurrences, 289 were accepted and emitted as vectors
(52.4%; 48.2% when whitespace symbols are included): 266 reuse decisions and 23
repair decisions. The report has 281 page-local prototype entries and 44
distinct prototype IDs across pages. **The G3 reuse demonstration passes:**
one `a` prototype ID (`prototype:40f6…4b95`) is referenced by 60 accepted
occurrences on pages p00 through p05. Eleven are classified as repairs and 49
as reuse. Their observed source-mask similarity spans 0.889–0.985. The same
document font reports GID 2 for that outline on each of the six pages, and the
assembled PDF has one embedded font. For comparison, `g` has 64 accepted
occurrences but seven prototype IDs and `a` has 92 accepted occurrences
across five IDs. The single 60-occurrence `a` outline demonstrates reuse, but
its accepted rendered group still regresses against pristine appearance
(0.942→0.900). The additional IDs are not yet qualified as legitimate variants
rather than fragmentation. The complete occurrence and per-page GID evidence is
in `qualification/experiments/m1g/fixture/dpi300/output/reuse-proof.json`,
generated by `qualification/experiments/m1g/prove_reuse.py`.

The diagnostic counts below use scan-mask hashes as exact masks and the
reported prototype IDs as compatible groups. `eligible` excludes spaces; OCR
label `c` is the deliberate `e` confusable. The 50% coverage mark (276 of 552
non-space occurrences) was chosen after fixture construction, not preregistered
before the final run, so the achieved 289/552 is descriptive rather than a
pre-registered pass.

| OCR label | Observations | Exact masks | Prototype groups | Eligible | Accepted | Accepted outline IDs |
|---|---:|---:|---:|---:|---:|---:|
| e | 95 | 95 | 3 | 95 | 22 | 2 |
| a | 96 | 96 | 5 | 96 | 92 | 5 |
| g | 64 | 64 | 7 | 64 | 64 | 7 |
| 0 | 64 | 64 | 4 | 64 | 14 | 2 |
| 8 | 64 | 64 | 6 | 64 | 15 | 3 |
| 6 | 64 | 64 | 5 | 64 | 14 | 2 |
| , | 32 | 32 | 4 | 32 | 31 | 4 |
| ; | 32 | 30 | 4 | 32 | 8 | 2 |
| ! | 16 | 16 | 2 | 16 | 14 | 2 |
| ? | 16 | 16 | 4 | 16 | 15 | 4 |
| c (confusable) | 1 | 1 | 0 | 1 | 0 | 0 |
| か / な / カ / ナ | 8 | 8 | 0 | 8 | 0 | 0 |
| **Total** | **552** | **550** | **44** | **552** | **289** | — |

At the fixed pristine glyph boxes and threshold used by the evaluator, mean
source→output IoU is lower for most accepted groups. Replaced `e` is 0.932→0.887,
`8` 0.937→0.907, `a` 0.942→0.900, `g` 0.948→0.914, `6` 0.943→0.916,
semicolon 0.950→0.914, and `0` **0.939→0.583**. The emitted zero visibly has
broken, square-edged geometry compared with the pristine outline. `!` is a
small positive control (0.941→0.945), but one small gain does not offset the
identity and fidelity regressions. Poppler and PDFium agree on the direction
of the main failures; individual renderer IoUs differ.

The supplied OCR text matches both Poppler and PDFium extraction after
whitespace normalization. The intentional OCR confusable is the one difference
between supplied OCR and pristine source Unicode. This validates text transport
for this fixture, not recognition accuracy. The kana remain raster fallback,
but their measured output-to-pristine IoU is only 0.55–0.65 versus source
0.89–0.91. High-zoom inspection shows their visible shapes retained, with a
renderer/raster-placement discrepancy sufficient to fail the fixed-box metric;
the named 300-DPI fallback-placement issue remains unresolved. Fallback and
uncertain-content fidelity therefore do not pass.

The output PDF passes qpdf structural validation and OTS 9.3.0 font
sanitization. Poppler reports one embedded CID TrueType font and eight 300-DPI
grayscale images. PDFium and Poppler render the PDF and extract searchable text.
The conversion took 355.34 seconds and peaked at 241,248 KiB RSS; page
conversion accounted for 337.19 seconds. The small size reduction comes from
changed residual raster samples and glyph reuse, not removal/downsampling of
the page backgrounds. It is not a meaningful compression win.

The old M1-F1 Adobe XI outputs cover different three-page documents, so they are
not a matched Adobe arm for this fixture. No new Adobe conversion was used as a
quality oracle. The existing 12-page repeated-content fixture was not run: the
300-DPI positive control already fails glyph and fallback fidelity gates, so
the mission's condition to extend a working synthetic mechanism was not met.

## 600-DPI result

The final PDF is 16,294,363 bytes, SHA-256
`0553ff8dd6581aba43aaee573a4c580a0530af64f57444aa26168fde8a39cc08`. The
same-run searchable-raster candidate is 16,301,964 bytes, a 7,601-byte
reduction (**0.047%**). Its eight 3600×1800 DeviceGray images account for
16,196,931 bytes (99.4% of the output); the font is 34,604 bytes, content
streams 56,080 bytes, and document overhead 6,748 bytes. All eight pages retain
their own image resource.

The profile accepted 497 of 552 non-space occurrences (90.0%). That higher
coverage worsened the quality result: document-weighted pristine IoU goes from
0.9781 in the scan to 0.9178 in the PDF; for accepted occurrences it goes from
0.9786 to 0.9214. Every major accepted family regresses. The unreplaced kana
fallback is also below the source scan (Poppler 0.79–0.86 vs 0.96–0.98).
Poppler and PDFium both extract the supplied OCR text correctly after
whitespace normalization, but their glyph IoU measurements diverge by several
points for some characters.

Wall time is 685.02 seconds (11.4 minutes), peak RSS 889,212 KiB. Page
conversion uses 608.9 seconds; PDF serialization/encoding uses about 33.9
seconds. Higher raster resolution increased the output by almost 4× over 300
DPI while reducing the already negligible size win. The 600-DPI run therefore
reinforces the no-promotion decision.

## Test and review record

- `cargo test -p scanweave-io`: passed, including the new exact-mask geometry
  test.
- `cargo test --workspace --no-fail-fast`: all remaining packages completed,
  but the existing `m1b_behavior::regress_auto_reports_the_selected_candidate`
  test failed (`reconstruct` selected; expected `raster_baseline`). The changed
  code path is experimental-profile-only for donor sampling and raster
  suppression; this test uses the default policy and is treated as an inherited
  failure, not as evidence of a canonical-profile regression.
- `qualification/checks.py --out /tmp/m1g-e0-e7.json`: E0–E7 all pass. The
  inherited visual/transport suite has failures at P01–P06 and P08; P07 passes.
  Details are preserved in `qualification/experiments/m1g/e0-e7-results.json`
  (SHA-256 `8638806cf0fa891858b8a1e980126f367cefafb4387d9d3a4ec506b2ef92dec8`).
- `cargo test -p m0-font-pdf --test m1d_document -- --nocapture` and
  `cargo test -p m0-font-pdf --test m1d_reconstruction -- --nocapture`: passed.
- Current 300-DPI PDF: qpdf `--check` passed; OTS font sanitization passed;
  `pdfinfo`, `pdffonts`, `pdfimages -list`, Poppler text extraction, and PDFium
  render/extraction were inspected.
- An independent reviewer confirmed the final 300-DPI byte accounting and
  search result, and identified the zero fidelity regression, fallback
  placement failure, and residual ring risks. The reviewer did not edit files.

## Decision and next step

The experiment demonstrates that document witnesses can support more than the
previous 2–8% replacement rate and that accepted occurrences can be replaced
inside an assembled searchable PDF. It does **not** satisfy M1-G's product
objective: most accepted glyph classes regress against pristine truth, the
zero is seriously wrong, fallback geometry is not qualified, and the PDF is
only 0.68% smaller after a six-minute 300-DPI run. The 60-occurrence single
outline reuse gate passed, but that outline itself regressed on pristine
appearance.

The single limiting subsystem is **occurrence-to-outline geometry and raster
ownership/compositing**. The next bounded action should isolate the existing
fallback page-placement discrepancy and the emitted-zero transform/contour
failure, then add per-occurrence pristine-independent acceptance diagnostics
and the specified hard negatives before changing reconstruction strategy.
Do not increase cohort breadth, add consensus fusion, or promote the residual
layer until those two concrete render failures pass. Real-domain validation is
**BLOCKED** because no stratified real receipts or historical book sample was
available for this run.
