# S2a partial work receipt

Status: **incomplete; not ready for blind grading**. The owner-authorized round is development on spent data; P2′ remains FAIL. No S2a outcome or comparative defect claim has been established.

The source-only exploratory program can be run from the repository root:

```
qualification/.venv/bin/python -m qualification.font04.s2a_prototype qualification/font04/local/S1/instrumented-0 --limit 2
```

It reads existing P2 source fields and frozen cover groups, applies the research registration routine, chooses the median source-to-source MSE medoid (deterministic index tie break), and computes a per-pixel median for groups of at least three members, otherwise falling back to the witness. `k=3` was fixed before the smoke run. This is preliminary: the local-disagreement guard is not implemented; groups in `plan.json` precede ownership preflight and must be reconciled with actual admissions; fields are not traced; transforms and placements have not been validated against native output. Two two-member groups ran successfully and both used the fallback. The scores are diagnostics, not evidence of visual improvement. The existing P2 export uses the earlier cover-2.0 base, not the ceiling, and cannot alone establish the requested evaluation.

A new worktree branch `exp/canonical-witness` was created at `3370de3`; it contains no implementation yet. P2′ has no retained planner/observation export; an isolated ceiling checkout and hash-preserving research hook are still required. No baseline PDF hashes have been reproduced in this round.

Remaining work: finish and validate both prototypes, implement both native flags with unchanged grouping, placement and vetoes, establish baseline and off byte identity, run all requested datasets and functional, quality, economy and performance checks, join all defect fixtures, and assemble and seal the randomized blind review package. None of those results is available. The independent contract is a draft; its numerical margins have not been calibrated and must not be inferred from development results.

Do not generate or open P2″. Do not alter either existing `OPENED` lock. Do not commit local data, fonts or generated pages.
