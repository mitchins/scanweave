# M2 independent review and reproduction

Base: merged M1 `e8739e0e7d6a3169b5e2b93061cff81c60d2919a`.
Independent read-only reviewer checked preprocessing, bounded registration,
metric validation, AUC/tie handling, complete-link grouping, corpus containment,
inference/evaluator separation and runner sequencing.

Three confirmed review findings were corrected before publication:

1. Reject every current evaluator-only field, including layout/master metrics.
2. Require exact public-source/evaluator ID sets and character agreement, including
   source observations that may subsequently abstain.
3. Bind runner inputs to the frozen fixture and freeze model/validation hashes
   before test; reject changed inputs before creating an output directory.

Focused regressions cover each. Final independent review found no remaining
blocker; the reviewer did not claim to have run tests. Parent ran all 20 FONT-01
unit tests and source coverage (98% rounded). Package extraction reproduced all
9344/5701/5744 train/validation/test feature and target values byte-for-byte against
prepublication prototypes. A strict manifest-bound rerun is recorded locally.

Healthy validation recall at 0.5% different-face FPR: deterministic27.97%,
linear28.52%; neither reaches the frozen50% shortlist gate. Healthy unseen-font
FPR:3.83% and3.33%, respectively, above1%. No product activation. Pair observations
share source masters and fonts; these counts are not independent population trials.

No Rust, PDF/font programs, Unicode, faithful or ACR-05 output behavior changes.
Large corpora, tensors and model files remain ignored. CNN challenger results and
canonical recovery are subsequent research evidence, not claims of this API PR.
