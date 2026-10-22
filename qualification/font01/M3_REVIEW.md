# M3 review, reproducibility and disposition

Based on merged product+M1+M2 main9a187132f5ff9d3cf8c1d9e927f8450acfdee57e.
No Rust or ordinary converter changes. Failed models stay research-only.

Independent code review examined source/evaluator boundaries, train/validation
selection, pre-test freezes, baseline binding, context and target-excluded recovery.
It identified a missing comparison between the frozen baseline's fixture hash and
current corpus hash. Corrected and regression-tested; today's hashes already
matched, so measured embeddings/results did not change. Final review follows in
PR discussion. CPU research dependencies are separate, official and hash-pinned;
no training dependency is added to Rust or ordinary conversion.

Independent visual review inspected source/Adobe/ACR-05 physical-coordinate
comparisons in both engines and synthetic candidates before unblinding identities.
It found one credible numeral medoid repair but healthy punctuation regressions,
cross-face T damage and unsafe different-style matches. Full-stop fragments were
correctly reinterpreted after labels were revealed; this does not establish fusion.
No model, canonical group or typography change is approved for normal conversion.

The reviewer also caught an overstated unused-font shadow equivalence claim:
Poppler7/8/9 differ despite PDFium equality. The user was corrected immediately,
changed pixels measured, and a head.flags control failed to remove the discrepancy.
The font packing shadow is unqualified and no production code is promoted.

Parent qualification:27 focused FONT tests, ~97% local measured source coverage;
strict baseline tensors/targets and all three CNN embedding arrays reproduced
exactly. The full research run is51.68s wall, peak773268KiB RSS. Test pairs share
masters/faces, so population confidence and general font-cohort success are not
claimed. Python/Rust inference parity is conditional and not attempted after
failed model gates. Sealed holdout remains unopened.

Final independent code/evidence check found no remaining blocker and reconciled
pair counts, failed gates and shadow limitations against results.json. The reviewer
did not rerun tests; execution evidence is from the parent.
