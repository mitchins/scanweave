# Independent M1 review receipt

Read-only reviewer: `/root/independent_review`, 23 October 2026. Reviewed generator,
tests, inference/oracle boundary, split/fixture manifests, specification and CI
dependencies. The reviewer did not run the generator/tests; the implementation
agent ran the recorded local tests and complete strict reproduction independently.

Findings and disposition before any model fitting:

- Global severity coverage did not prove each face-character had clean and damaged
  observations. Fixed with preassigned per-identity bands and an enforced coverage
  assertion.
- Merely recording hashes did not enforce frozen reproduction. Added strict asset,
  notice, tool, PDF, label and input-record verification, with mismatch tests.
- Encounter-order severity correlated rare punctuation with DPI. Fixed with
  independently seeded, shuffled per-identity damage plans; rare-`!` regression.
- Shared geometry/degradation RNG allowed draw-count coupling. Separated streams;
  regression injects extra degradation draws and verifies unchanged geometry.
- Parent review found authoring baseline/nominal height in public records. Moved
  them to oracle labels, added absence tests, and disclosed controlled labels/bounds.

Final independent conclusion: **no remaining infrastructure/versioning blocker**.
This is not review or approval of an algorithm, model or production font merge.
Oracle separation is procedural; published seeds allow label regeneration.

Ten local tests pass; benchmark module statement coverage is99%. A complete strict
second generation matches the committed fixture manifest. No production Rust code
or accepted ACR-05 PDF has changed. GitHub CI, Sonar and automated review remain
separate server gates; a CodeRabbit rate-limit check is not review approval.
