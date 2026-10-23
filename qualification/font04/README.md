# FONT-04 discovery — Checkpoint B2′

Contract: `9c2e9963aebce439495a409ac9588a5b38321fc3`.
Product/main baseline: `c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1`.
Default PDF SHA-256: `74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f`.

B2′ stops for independent review. No operating point is selected or promoted;
P2 is unopened, PR #24 remains draft, and no merge or product PR is authorized.
Earlier checkpoints remain historical evidence in `FONT_04_RESULTS.md`.

The B2′ compositor is an explicit offline research tool. It takes the complete
ordinary default PDF and the frozen source-only B2 trace/fit ledger and emits
complete financial PDFs. It does not hook or modify default conversion. Each
occurrence retains its CID, Tm, W and ActualText; TrueType composites reference
shared outlines, with metric-identical CID-map resources resolving repeated-CID
instance conflicts. Primitive outlines, composite stubs and total required slots
are counted separately.

## Reproduction

Use `qualification/.venv/bin/python -m` for the modules below. Dependencies are
NumPy, SciPy, Pillow, fontTools, pikepdf, pypdfium2, Poppler, qpdf and OTS.
Large inputs/outputs remain ignored in `local/`, hashed in the artifact manifests.
The prior `b2-artifact-manifest.json` freezes the cached B2 source observations,
traces and fits; these are prerequisites, not freshly inferred pristine data.
The pinned commit's README describes the earlier B1/B2 preparation workflow.

1. Build with `cargo build --release -p scanweave-cli --bin scanweave -p scanweave-io --example font04_trace`.
2. Run the normal default financial conversion and compare it to independently
   generated main. B2′ records the fresh run in `B2prime-default-profile.json`.
3. `qualification.font04.b2prime transport` re-emits frozen P-initial membership,
   scores all four references and requires exact text/search/structural contracts.
4. `qualification.font04.measurement_equivalence` checks serial/parallel coverage;
   `qualification.font04.canonical_hygiene` screens offers and runs all 16
   candidate-side material regressions before any soft-criterion change.
5. `qualification.font04.soft_support` calculates source-only LOO fallback floors
   for every member. Witness count is diagnostic; hard member vetoes stay fixed.
6. `qualification.font04.run_b2prime` emits star/cover × 1.0/1.5/2.0, the outline
   retirement control, and the literal all-slot retirement control. It scores,
   validates, repeats, audits actual raw owned ink, separates fidelity-only groups,
   and seals the review. `--resume` reuses exact completed outputs and validations.
7. `qualification.font04.finalize_b2prime` verifies all deliverables, writes
   `checkpoint-B2prime.json` and the hashed manifest, and updates the results.

`support-initial` outputs retain the complete first sweep, whose missing fallback
floors indirectly gated 378 members. They are explicitly superseded diagnostics.
The final sweep has no missing floors. Sparse CID maps and matched generated
object streams remove serializer overhead; the save-only control is separate.

The four references retain B2's physical coordinate grids: supersampled analytic
primary, independent direct winding coverage, native PDFium and native Poppler.
Workers reopen PDFium input files independently after fork; 16 serial replays
match the corrected parallel arrays exactly. Native differences below measured
renderer floors do not rank arms. Cached OCR/trace/fit emission timings are not
an end-to-end conversion benchmark.

## Independent review

Open only `local/B2prime-blind-review/` for grading. It contains a lossless PDF,
opaque-ID Source/U/V assets, blank judgments and an integrity receipt. The key
and private selection/context data are outside that directory. No filename
encodes the arm, stratum or current/candidate mapping. Every glyph comparison
uses identical full default page context with only the target draw replaced.

Save every U/V judgment first. Only then may the independent reviewer run:

```sh
qualification/.venv/bin/python -m qualification.font04.seal_b2prime_review reveal qualification/font04/local/B2prime-blind-review qualification/font04/local/B2prime-review-keys/key.json saved-judgments.json
```

The command refuses missing, duplicate or incomplete judgments and checks the
sealed key hash before decoding. Materiality/false-rejection fields remain null
until that review. The authoring run does not reveal the key.

`geometry.py` and `pdf_helpers.py` retain FONT-03 `7ebc09e` attribution. All hard
structural checks, ownership rules and existing security analysis remain active.
