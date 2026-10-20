# GitHub consolidation checkpoint

## History and publication

Fetched GitHub before editing. `origin` is `git@github.com:mitchins/scanweave.git`; default branch `main` remains `3f0a7086068796d0ddbeee5e942ffa0da414a99f`. Initial local `main` was `4c24312e7503bc2407a38c2bc97b9779ed6c5ec0`, exactly 35 commits ahead, with the same merge base and no divergent remote changes. No PR was open. Previous main CI runs were successful; they did not exercise this unpublished history.

Published those 35 existing commits without rewriting or force-pushing on `review/clearscan-consolidation`, targeting `main`: **https://github.com/mitchins/scanweave/pull/1**. One catch-up boundary preserves the existing interdependent linear provenance rather than reconstructing three artificial histories. Typography (`4bff482`), contours (`ac977ff`), paper (`b2ec997`), packaging (`80b2a42`, `b4387d4`) and convergence (`5998611`, `13288a8`, `4c24312`) are all ancestors. This document and CI-contract fixes are follow-up commits on the same review branch.

The checkout initially had no tracked changes, but 6,160 untracked/ignored-discovery status lines from existing research/evidence. Those remain in place; the status snapshot is local `/tmp/scanweave-publication-status.txt`. No holdout was opened. Existing history contains about 1,020,485,044 bytes of tracked working-tree objects and `.git` occupies about 944 MiB; largest tracked file is a 24,756,907-byte measurement JSON. The push includes existing committed history, not newly staged ignored bulk collections. Removing already committed evidence would not shrink historical transfers and rewriting history was not authorized. No new bulk evidence was added for publication.

## CI credibility

`.github/workflows/ci.yml` still runs **unfiltered `cargo test --workspace`**, Clippy with denied library warnings, publication hygiene and Python qualification gates. No exclusion or weakened reconstruction threshold was added.

- The auto-accounting test incorrectly assumed a 1.0 source-preservation requirement forces raster-baseline selection. Low-fidelity units already fall back before ranking, so reconstruction can meet 1.0 and be smaller. The corrected regression checks the actually selected candidate's serialized bytes, font/image/content/raster accounting and page fidelity, plus cheapest-qualified selection. Baseline bytes/fidelity are also checked when selected. The original selected-accounting requirement is retained.
- The M1-D damaged-crossbar `e` remains a **genuine inherited donor-repair capability gap**. It has intact witnesses but current candidate discovery reports `no_supported_donor`. It is not reclassified as success, skipped, or retired. Its test remains failing. This PR stays draft with that merge blocker.
- Current-toolchain Clippy findings are corrected with equivalent standard integer/chunk operations and bounded DPI clamp. No contour or acceptance thresholds changed.
- Local equivalent checks and logs: `qualification/github_consolidation/`. Real-document P01–P08 inherited visual/native failures remain in `qualification/real_convergence/e0-e7-p01-p08.json`. They are not represented as passing.

Independent review confirmed the obsolete forcing assumption and independently identified the unrepaired `e` as a real gap. The existing CodeRabbit installation was explicitly requested to review draft PR #1 (`@coderabbitai review`). No PR is automatically merged. README describes the normal PDF-to-PDF command, measured real limitations and this draft status.

GitHub Actions links and the latest head/check state can be retrieved with `gh pr checks 1`, `gh pr view 1 --json headRefOid,statusCheckRollup,reviews`. A draft is intentional until actual blockers are resolved; successful publication is not release qualification.

## Separate shaded-paper work

The accumulated implementation is now pushed and reviewable, satisfying the publication gate. Bounded shaded-paper ownership work starts from this published branch on a separate branch, with a separate stacked PR targeting this catch-up branch. It must not change the catch-up PR's glyph reconstruction behavior or conceal its donor-repair blocker.
