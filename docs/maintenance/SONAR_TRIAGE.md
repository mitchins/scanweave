# Consolidation and Sonar triage checkpoint

This is an explicitly incomplete historical-debt cleanup, not a claim of zero priority findings. The keyed CSV is the correctly scoped **main5b4ad8b** snapshot before PR7/9 merge. It records every open BLOCKER/HIGH/MEDIUM finding's rule, location, maximum impact severity, all impacts, status and disposition, deduplicated by key. Final main analysis and CI are linked in the PR closure receipt. No issue was bulk Accepted, no rule disabled, no NOSONAR added, and no Quality Gate threshold changed.

## Scope and actual measurements

| State | Source files | Noncomment source lines | BLOCKER | HIGH | MEDIUM | LOW | Ratings S/R/M | Measured coverage | Server gate |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| Before1597671 |745|4,498,538|15|182|126|157|E/C/A|not configured|NONE|
| Corrected main5b4ad8b checkpoint |240|24,321|1|211|114|168|E/C/A|40.1%|PASS (new code)|

The original dashboard omitted Rust entirely and counted4,486,069 JSON lines. The first scoped analysis added production Rust, exposing previously unreported debt; its543 unique issues cannot be compared as a code-quality regression against the original480. Eight frozen rejected/baseline Rust copies (not Cargo targets) were then excluded by exact path/hash:4,290 source lines and23 findings. All active Rust/Python utilities, tests, workflows and C reference utility remain in scope. Other generated/third-party exclusions are explained in SONAR_SCOPE.md. Scope removals are not code fixes.

## Genuine corrections and reviewed false positives

PR5 pins actions to verified immutable official Node24 releases, uses minimal permissions and nonpersistent checkout credentials, and enables CI analysis/real Rust coverage. PR8 hash-locks Python direct/transitive dependencies, enforces wheel-only artifact hashes and pins OTS9.3.0 source. Fresh main analysis confirms S7637/S8541/S8544 closed; S8549 remains on Cargo build, now corrected with --locked in PR9, pending main verification.

PR7 addresses BLOCKER S2755 with explicit resolve_entities=False while retaining no-network/no-DTD behavior. Five tests include actual script execution with only Tesseract mocked, private synthetic input/output, preserved text/title processing and unexpanded entities. Measured utility coverage91%; four existing hOCR controls remained serialized-byte identical. Current lxml6 already rejects the demonstrated external-file entity, so this is version-independent explicit hardening plus prevention of custom internal expansion, not a claim of a demonstrated current remote file leak. Independent review found no bypass; nonzero crop-offset arithmetic is outside the added unit case.

PR9 addresses thirteen HIGH S5443 findings: historical comparison executables require explicit caller selections; no implicit shared /tmp PATH/library injection; scratch PNG/font/N1 lifetimes are private. Six resource tests include real missing-override entry points and real empty-corpus packaging modules. Existing synthetic300/600 render hashes remain unchanged. The main converter is not modified. Fresh independent boundary and bypass reviews found no blocker. Local PR9 server analysis after actual coverage import passed with81.6% new-code coverage and no new open issues; hosted/final-base CI remains required.

The JSON records25 separately reviewed false-positive issue keys, including24 historical-main keys and one repeated PR9 font-body/path report. Fourteen original BLOCKER S2083 reports confused bytes written with their destination; exact receiver/provenance reasons and independent review are recorded for each. Ten S2245 reports use PRNGs exclusively for synthetic noise/barcode/degradation samples, not credentials or cryptographic material. The additional PR9 S2083 receiver is private TemporaryDirectory()/font.ttf; PDF bytes are only its body. Each key has its own server comment/reason and FALSE-POSITIVE disposition. Genuine shared-temp findings remained open until fixed separately. Historical hash-based seed reproducibility is a separate concern, not dismissed by the randomness disposition.

Contextual CLI/argument findings remain OPEN where final authority/symlink/tag reasoning is not being promoted to a blanket false-positive class. Ratings remain visible. No successful test is used as proof that a reported defect cannot exist.

## Coverage and gate limitations

Official GitHub coverage/scanner runs pass the existing server gate after processing, not merely upload. PR7 initially failed0% new Python coverage; that failure was retained and corrected with a test executing the real parser. Python coverage XML includes all in-scope Python production files, so uninstrumented utilities remain in the denominator. No Python coverage percentage is inferred from test success. Rust LCOV artifact is retained seven days for reproducibility.

Five importer warnings are diagnosed using actual downloaded LCOV and a credential-safe local verbose scan: five positive DA hit counts in scanweave-io/src/convert.rs exceed the analyzer's integer range (about10.1billion). Paths, source line numbers and BRDA/FN ranges are valid. The analyzer omits those five entries. The displayed40.1% is the real imported aggregate and may slightly understate coverage; counts were not falsified or zeroed to remove warnings. Raw coverage remains available in CI. C AutoConfig analyzes the27-line Win32 reference source, but C taint analysis is unavailable in this mode; no complete C-taint assurance is claimed.

## Explicit stop for behavior-sensitive refactoring

Independent review confirms these are genuine live production complexity findings:

| Sonar key | Function | Complexity |
|---|---|---:|
|AaFbqrwrDf3ZA7hnTDuL|convert_parts, convert.rs:726|294|
|AaFbqrwrDf3ZA7hnTDuM|clean_replaced_text, convert.rs:2000|174|
|AaFbqrwVDf3ZA7hnTDuH|reconstruct, visual_dict.rs:345|106|
|AaFbqrvpDf3ZA7hnTDt6|emit_text_runs, page_pdf.rs:434|100|
|AaFbqrvcDf3ZA7hnTDt5|convert_document_with_sources, document.rs:229|96|

Reducing them below30 requires substantial helper/state decomposition of coupled ownership, accepted-only pixel suppression, donor thresholds, CID/ActualText placement and document candidate assembly. Independent review found no safe tiny correction that resolves these metrics. The user's explicit prohibition on broad converter/font/ownership/assembler refactoring solely for style therefore blocks complete historical-debt closure. These findings are left open, not relabeled false positive or suppressed. A follow-up needs operator-reviewed scope and function-at-a-time decoded-PDF/render/extraction/ownership/determinism equivalence gates. Other unresolved medium/high findings remain visible in the CSV and require case-specific work; this checkpoint does not claim they are all fixed.

## Product stability and review

No crates/probes production Rust changes are made in this consolidation. Faithful, ordinary PDF input, canonical reconstruction/donor repair, source-image trust, Unicode ownership and serialization are unchanged. Unfiltered workspace Rust tests, denied-warning Clippy, Python qualification, font/PDF/search and hygiene run on actual PR heads. No full32-page regeneration is justified by documentation/workflow/qualification-resource changes. Existing P01–P08 visual limitations are retained; green CI is not a claim those disappeared. An extra local cargo fmt --check found inherited formatting drift; no mass formatting was applied.

PR5/6/8 merged after green hosted CI and independent review. CodeRabbit was rate limited on some revisions; that is not approval. PR7's refreshed small diff received a completed CodeRabbit review. PR9's stacked-base CodeRabbit skip requires review after retargeting to main. No merge is authorized by a skipped status alone. Repository settings permit squash merges only; normal configured squash merges preserve the published branch histories without force pushes or history rewriting.

README explanatory prose185 words, approximately56 seconds at200wpm. Prior technical content lives in docs/DEVELOPER_GUIDE.md. Linux package names and official Homebrew formulae were verified; macOS commands were not executed on a Mac. Action release SHAs and source exclusions are separately recorded. The deferred OCR reconciliation paragraph is in LEDGER.md only.
