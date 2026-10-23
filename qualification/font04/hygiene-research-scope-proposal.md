# Proposed separate PR: isolate research measurement coverage

Proposed title: **Scope experimental research coverage without disabling analysis**.
This is a reviewable proposal, not an applied gate change or an opened PR.

Move maintained experimental Python into `qualification/research/` in a separate
small infrastructure PR, preserving per-study modules (`font01`, `font02`,
`font03`, `font04`) and keeping immutable evidence and ignored large local
artifacts at their existing paths. Keep stable product qualification gates such
as search, XML boundaries, scratch/tool selection and corpus adapters at their
current paths and fully covered. Do not move or delete untracked research data.

Add these properties while preserving all existing analysis sources:

```properties
sonar.coverage.exclusions=qualification/research/**
sonar.cpd.exclusions=qualification/research/**
```

Do not add this path to `sonar.exclusions`, exclude Python wholesale, alter the
project quality gate, or suppress Security or Reliability rules. Experimental
coverage and copy/paste metrics concern alternative trial implementations;
Security and Reliability remain applicable to researcher tools and their inputs.
Shipped Rust crates retain every existing gate. Existing Python contract tests
continue to run and report results even when research coverage is not a gate.

Stage the PR narrowly: migrate the maintained FONT-03 package and its experiment
entrypoints first, update explicit imports and reproduction commands, and retain
historical evidence paths and hashes. List additional study migrations as later
work rather than combining a broad cleanup. Never move local ignored outputs in
an import refactor. Verify affected import/CLI contracts, the frozen evidence-path
mapping, unchanged Rust/product qualification scope, and a fresh Sonar report
showing research Security and Reliability analysis still active. Report both
pre/post issue inventories and keep each false-positive disposition individual.

A separate repository would require duplicating version pins and reproducing
private source inputs across repositories. The package boundary keeps research
and product revisions auditable together, while the two metric-specific
exclusions express the intended scope directly. Research code that becomes a
shipped dependency must leave this excluded package and gain production coverage
before shipping.

PR #24 decision remains pending. After independent review of the 15 distinct
Security dispositions, resolution of any remaining gate failures, and the scope
PR's fresh Sonar evidence, reviewers can choose to merge #24 as infrastructure.
If they choose closure, retain `research/font03-consensus` at its recorded SHA and
its local evidence; no FONT-04 result depends on merging it. This launch performs
neither merge nor closure.
