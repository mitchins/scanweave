# Wave 3 — shared qualification auditor and stable product samples

## Gate and scope

Base: `825eb12b8eadd06cf7e8286800b34e949f6378b0`, after PR12 merged under
operator authorization, fresh main CI/Sonar passed, all nine original keys were
queried individually, and zero open PRs was confirmed. The exact closure is
**eight verified fixes, zero reidentifications, one unresolved CLI finding**.
Main has113 OPEN HIGH findings. The remaining CLI function has complexity32;
this qualification-only wave does not change it.

This PR targets five exact existing keys:

| Key | Existing finding | Change |
|---|---|---|
| `AaFbZj1A2TNSduKvuGug` | competitive auditor, complexity164 | Shared implementation |
| `AaFbZj1d2TNSduKvuGu4` | background auditor, complexity164 | Shared implementation |
| `AaFbZj3T2TNSduKvuGyL` | contours auditor, complexity164 | Shared implementation |
| `AaFbZj4h2TNSduKvuGzW` | typography auditor, complexity164 | Shared implementation |
| `AaFbZj482TNSduKvuGz-` | product measurement `main()`, complexity16 | Extract first-replaced sample selection |

The operator explicitly added the last key from Wave1. One analytical
implementation family is consolidated; no comparator or stage-analyzer changes.
The other12 originally assigned candidates stay open and deferred rather than
expanding this PR beyond its proven semantic/numerical equivalence budget.
No Sonar scope, rules, severities, exclusions or Quality Gate settings change.

## Why sharing is appropriate

All four original `audit.py` files are byte-identical, SHA-256
`330731520febfbd20f122d9aade4c8dff6ce64948ea19fd51af1630702da4de8`.
Their history shows maintained tools carried forward through competitive,
typography, contour and background engineering, rather than intentionally
independent frozen implementations. Reports, hashes, PDFs and historical
measurements remain unchanged. The previous implementations remain in Git.

The new `qualification/clearscan_audit.py` separates font loading, per-page text
state, occurrence inspection, TrueType/CFF geometry, witness assignment,
image-resource accounting and reporting. The four original paths are thin
backwards-compatible entry points. Their `audit(dpi, arm, path, report_path=None)`
interface remains; each passes its own originating ROOT and output B explicitly.
The shared module's `__file__` never determines corpus or report locations.

Preserved details include per-page text-state reset, ActualText cursor order,
CID/GID differences, CFF `.notdef` fallback, `repr(RecordingPen.value)` hashing,
counting shown codes before empty-outline filtering, counter insertion order,
outline-hash-before-bbox JSON ordering, exact bbox arithmetic, witness lookup
and its error order, numeric image-name sorting, patch/resource zipping and
first-object-reference accounting. Images are still classified only when a
matching report exists; no report-free classification is invented. The
existing limitations of mixed-content byte attribution and unrotated geometry
remain disclosed rather than repaired inside consolidation.

Product sampling now names the original first-replaced-per-character loop.
It preserves object identity, first occurrence and dictionary insertion order;
there is no sorting or changed replacement ownership.

## Executed exact equivalence

The original CLI entry points were executed before and after, not just their
helper functions. Each of four paths ran at300 and600 DPI against both the
same ScanWeave eight-page PDF/report and the frozen Adobe PDF: **16 runs**.
Every output JSON byte and stdout hash matches. This exercises the actual
TrueType/CFF font programs, occurrence/witness accounting and raster resources.
The auditor's historically supported absolute arm/output-directory behavior
redirected these trials into scratch; no published audit was overwritten.

The actual full product measurement ran before/after on the preserved300 DPI
fixture/PDF/report. All **27 files match byte-for-byte**, including metrics JSON,
16 full-page Poppler/PDFium renders and ten labeled800% comparison crops.
Numerical values and render geometry are exactly equal; no tolerance was used.

[Machine-readable hashes and reproduction commands](sonar-high-wave3-validation.json)
record original script hashes, exact source PDF/report identities, all16 audit
commands/results and the27 product artifacts. Large existing inputs and derived
runs remain outside Git. To reproduce on an existing fixture:

```sh
qualification/.venv/bin/python qualification/clearscan_competitive/audit.py \
  300 /tmp/wave3-audit /path/to/frozen.pdf --report /path/to/matched-report.json
qualification/.venv/bin/python qualification/clearscan_product/measure.py \
  --dpi 300 --input-dir qualification/experiments/m1g/fixture/dpi300/input \
  --oracle-dir qualification/experiments/m1g/fixture/dpi300/oracle \
  --pdf qualification/clearscan_product/300/clearscan.pdf \
  --report qualification/clearscan_product/300/report.json --out /tmp/wave3-product
qualification/.venv/bin/python qualification/test_high_wave3.py
```

The first command preserves the historical audit CLI and writes
`/tmp/wave3-audit/audit.json`. Repeat for the other entry points and600 DPI.
The baseline source is available at `825eb12`; main's reconstruction and faithful
production code is unchanged in this PR, so no full real-corpus regeneration is
necessary. Existing E0–E7 results and P01–P08 visual/transport limitations are not
reclassified by green maintenance CI.

## Tests, coverage and review

Seven fast PDF-backed controls exercise TrueType/CFF accounting, empty outlines,
Tj/TJ, invisible text, Unicode-owner ordering, native/shared image classification,
wrong witnesses, absent reports, nonembedded fonts, all four real entry points,
legacy keyword `arm` calls,
and product sample identity/order. These minimal containers test accounting;
they are **not** a claim of independent renderer validity. The unchanged actual
product renders provide the Poppler/PDFium evidence.

The new tests execute in ordinary Python qualification CI and measured Sonar
coverage. A local instrumented run measures99% statement coverage for the shared
auditor; this is not a substituted project coverage percentage or Quality Gate
result. Independent read-only source/test/evidence review found no blocker and
verified the exact equality claims. Fresh final-head CI/Sonar and CodeRabbit
results are recorded on the PR before requesting merge approval.

Main's five original keys remain OPEN until an approved merge and fresh main
analysis verify closure and check for reidentification. Moving code alone is not
reported as five verified fixes. No production interfaces, OCR, reconstructed
fonts, Unicode ownership, faithful behavior or serialized PDF bytes change.


### First server result and small cleanup

At `0124487`, CI and Sonar passed (97.1% new-code coverage, zero duplication).
Sonar also reported two new LOW unused matrix bindings and one MEDIUM unused
parameter in the new shared implementation. Those are not HIGH target closures.
The backend now takes only the inputs it uses; the legacy `arm` parameter stays
in every historical wrapper's exact signature, including keyword calls. Its
pre-existing unused-parameter findings remain old compatibility debt, not claimed
fixes. Matrix unpacking explicitly ignores the same two unused components and
preserves all numerical operations. Seven controls and all16 historical CLI
comparisons pass again with exact output bytes. Independent review cleared the
small delta. Fresh final-head CI/server results are recorded on the PR.
