# FONT-04 product integration: closeout

The owner approved a squash merge of PR #26, which merged on 2026-11-04 as `79b30e54907baedc76d0649ad17a7b2ebc749fda` on `main`.

- PR head before merging: `a460fe9bfae1fd8f4f39c43e7720e3e70deb7208`. The merge was pinned with `--match-head-commit`, and all seven required checks were green. No protections or reviews were bypassed.
- The merged tree on `main` is identical to the PR head.
- Post-merge CI on `79b30e5` passed: Rust tests, Python qualification gates, publication hygiene, analyze and SonarCloud. The SonarCloud quality gate on `main` is OK.
- `--glyph-sharing off` is still the default. `cover-2.0-ceiling-q3` is the only opt-in. No release was tagged and nothing was promoted to default.
- Accepted follow-up debt is tracked in issue #27: the seven Sonar cognitive-complexity warnings, conservative owned-ink behaviour at 600 DPI and the late PDFium dependency check.

FONT-04 product integration is complete. Any further FONT research milestone needs separate owner authorization.
