# ACR-06 C2b: 600-DPI sharing funnel (research only)

Original recommendation was to revise; after the follow-up below, the recommendation is to **close #27 item 2 as no useful safe gain for the tested bounded halo correction**. No bounded, physically justified change with demonstrated meaningful gain was identified, and no relaxed candidate was implemented. This does not establish that no useful safe gain is possible. In particular, the 1.5-source-pixel halo remains an unresolved scale-dependent question, not a demonstrated safe correction. The q3 and default decisions are unchanged. No holdout was opened and no Phase 3 candidate qualification is claimed.

## Design and limits
Development fixture: 18 identical text lines, same layout in points, five DejaVu faces and multiple sizes, seed 270602, rendered separately at 300 and 600 DPI. Generator, font and input hashes and the Bitstream Vera/DejaVu licence location are in `development-manifest.json`; PNGs and PDFs are in `local/c2b/development`. PIL integer font-size rounding and rasterization change the samples, as expected. These are clean repeated-font pages with little independent design variation and are not representative holdouts. OCR produces 273 emitted occurrences in both pages but different eligible cohorts. Spent sheets are P2/P2prime/P2pp 6–8 and FONT-01 train/validation/test 2, 600 DPI. This worktree is based on main 9655fcc; numbers need not reproduce the older 79b30e5 study exactly.

`SCANWEAVE_RESEARCH_C2B_TRACE=<path>` writes occurrences, eligible rows, all tested fits, cover groups, and final pre-economy decisions to that path; ownership outcomes are in `<path>.ownership.json`. Null ownership outcomes mean invalid geometry and remain vetoes. The ordinary q3 sidecar supplies economy and final decisions. Trace artifacts are large and live in `local/c2b/trace`. `run.py` pins PDFium and thread limits. `summarize.py` replays the deterministic cover, checks the replay against actual groups, and computes member-existence counts. The existence columns are successive filters over a member’s tested non-self pairs; they are not a disjoint accounting of causal failure, and no claim is made about untested pairs beyond the 24 nearest candidates. Cover columns partition eligible members, with selected groups listed before ownership. Cross-stage differences can include canonical selection and greedy cover interactions.

## Funnel

| document | occurrences | cohort ≥10 | frame / trace | any structural fit | + hygiene / band | + relative ≤2 | + absolute ≤0.08 | self-admissible | cover below quorum | no self candidate left | planned |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development-300 | 273 | 170 | 170 / 170 | 151 | 139 | 131 | 131 | 137 | 141 | 26 | 3 |
| development-600 | 273 | 167 | 167 / 167 | 160 | 153 | 151 | 145 | 149 | 147 | 11 | 9 |
| font01-test-2 | 389 | 257 | 257 / 257 | 127 | 102 | 101 | 64 | 184 | 169 | 70 | 18 |
| font01-train-2 | 434 | 294 | 294 / 294 | 131 | 112 | 110 | 63 | 209 | 195 | 84 | 15 |
| font01-validation-2 | 322 | 159 | 159 / 158 | 69 | 52 | 51 | 36 | 114 | 110 | 43 | 6 |
| p2-6 | 425 | 289 | 289 / 289 | 112 | 91 | 91 | 38 | 198 | 200 | 89 | 0 |
| p2-7 | 502 | 372 | 372 / 372 | 134 | 90 | 85 | 45 | 221 | 215 | 151 | 6 |
| p2-8 | 527 | 412 | 412 / 412 | 217 | 164 | 160 | 96 | 260 | 242 | 148 | 22 |
| p2pp-6 | 469 | 330 | 330 / 330 | 134 | 103 | 100 | 61 | 227 | 216 | 102 | 12 |
| p2pp-7 | 547 | 450 | 450 / 450 | 216 | 171 | 167 | 88 | 314 | 292 | 136 | 22 |
| p2pp-8 | 544 | 396 | 396 / 396 | 174 | 135 | 133 | 87 | 269 | 252 | 121 | 23 |
| p2prime-6 | 522 | 403 | 403 / 403 | 185 | 138 | 134 | 62 | 250 | 240 | 151 | 12 |
| p2prime-7 | 574 | 441 | 441 / 441 | 209 | 139 | 136 | 73 | 301 | 294 | 139 | 8 |
| p2prime-8 | 548 | 430 | 430 / 430 | 200 | 153 | 150 | 81 | 301 | 289 | 124 | 17 |

| document | planned | legacy invalid | legacy true | corrected true | corrected invalid | combined veto | survive final quorum before economy | emitted | fallback |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| development-300 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | — |
| development-600 | 9 | 6 | 0 | 0 | 0 | 6 | 0 | 0 | no surviving cover groups |
| font01-test-2 | 18 | 6 | 0 | 6 | 0 | 10 | 3 | 3 | — |
| font01-train-2 | 15 | 3 | 0 | 5 | 0 | 6 | 6 | 0 | aggregate economy: negative net outline retirement or encoded font growth |
| font01-validation-2 | 6 | 2 | 0 | 2 | 0 | 4 | 0 | 0 | no surviving cover groups |
| p2-6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no surviving cover groups |
| p2-7 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | no surviving cover groups |
| p2-8 | 22 | 8 | 0 | 3 | 0 | 10 | 6 | 6 | — |
| p2pp-6 | 12 | 3 | 0 | 2 | 0 | 4 | 3 | 3 | — |
| p2pp-7 | 22 | 11 | 0 | 10 | 0 | 16 | 3 | 3 | — |
| p2pp-8 | 23 | 15 | 0 | 3 | 0 | 16 | 6 | 6 | — |
| p2prime-6 | 12 | 4 | 0 | 4 | 0 | 7 | 0 | 0 | no surviving cover groups |
| p2prime-7 | 8 | 5 | 0 | 2 | 0 | 6 | 0 | 0 | no surviving cover groups |
| p2prime-8 | 17 | 6 | 0 | 1 | 0 | 7 | 6 | 6 | — |

The 12 spent 600-DPI sheets have 4,233 eligible members, 1,908 with at least one structurally passing non-self fit, 1,450 after hygiene/band, 1,418 after the relative ceiling, and 794 after the absolute ceiling. Greedy cover consumes 2,714 members in groups below its distinct-design quorum; 1,358 remain with no self-admissible canonical, and 161 enter planned groups. These cover categories partition the eligible members and are not interchangeable with the pair-existence counts. Of the 161 planned members, 88 encounter the combined ownership veto, leaving 33 members after final group checks; six members in FONT-01 train then fall back for document economy. Legacy invalid occurs 65 times and corrected true 38 times, with overlap. See the per-member trace for all outcomes.

The matched development pages have 170 versus 167 eligible members, and 3 versus 9 planned members. At 600 DPI six planned members have invalid legacy geometry and all groups fail final quorum; at 300 DPI the three planned members survive. The fixture does not reproduce the large 300-DPI retirement rate of the spent corpus and does not isolate how much of that corpus gap comes from genuine detail versus sampling, OCR, or upstream grouping. The spent-sheet filter counts and the paired fixture point to an upstream bottleneck as well as the known veto; they do not provide a controlled causal estimate for each stage.

## Scale and visual investigation
The 2.0 relative and 0.08 absolute limits apply to squared coverage error normalized by total maximum ink on a 64×64 canvas scaled by line x-height, not a direct distance in source pixels. A raw multiplication of either ceiling by DPI is not physically justified. Registration translation bounds are also in this normalized canvas. The source preparation does use a fixed two-pixel grayscale halo and `dist <= 1.5` source pixels; it has a different physical extent at 600 DPI. Its purpose includes excluding nearby foreign ink and sampling antialiased edges, so physical rescaling alone is not proof of a defect or of safe improvement; the available halo would also need careful treatment. No counterfactual trial here establishes how much this quantity contributes to the gap.

For a diagnostic only, `rejected_pairs.py` selects 12 P2 sheet 6 pairs whose best structural/hygiene/band/relative passing fit exceeds 0.08. The native source crops are `local/c2b/rejected-pairs.png` (SHA-256 `7d2dcdb01a8f9692db7849c608c604ed75b879b328a19c0c28832da5a8f0aac2`). The sample includes clear variations in serif, proportions and weight, and apparent same-label OCR mismatches. The earlier report incorrectly described `w000028s0007` versus `w000012s0007` as C versus S. Pristine labels identify both as lowercase s in NimbusSans-Regular at 15 pt. Their scanned source is damaged. The `w000078s0003` versus `w000069s0000` a pair has different truth fonts. OCR boxes can include neighbours and these are source crops, not isolated rendered substitutions; inspect them as diagnostic examples, not a population estimate. The source crops contain scan damage; they do not visualize the prepared ownership mask. See the follow-up for measured mask loss and truth-matched pair classification.

Claude’s prior C2 review found 35 additional 600-DPI substitutions and only 7,423 bytes saved from corrected-only, with visible weight/proportion changes and individual pristine-error increases. The present run does not repeat that experiment or qualify those substitutions. No sharing candidate was implemented, so all-new-substitution panels, fidelity/ownership assessments, holdout, off/main/candidate economy, renderer diffs and candidate runtime comparison are inapplicable. The worrying examples above are rejected pairs, not newly admitted glyphs.

## Verification

| DPI | exact main SHA-256 | instrumented unset | trace enabled |
|---|---|---|---|
| 300 | `ecf17e104958122eca02e75def058914d21d10fc567a0159cf09905be0a34e61` | identical | identical |
| 600 | `b501ec7ce919c58fdee2736cde97c85cbf3e96c67a1e26c585dffc9d51d4d924` | identical | identical |

`cargo test --workspace --locked` and the CI clippy command passed; generated `qualification/evidence` files were restored. Python CI results and retry logs are under `local/c2b/checks`. The corpus adapter initially could not find `qualification/.venv` in this worktree; it was linked to the requested environment for the retry. The retry passed with the configured qpdf and OTS paths; the other 19 Python gates passed on their first run. The fixture manifest and all measurement scripts are evidence for independent review; no evidence files are committed by this worktree.

Python retry log SHA-256: `6ea89b4eb29055be3517a089ba27b713a003415a54178378f2c2a8eb93118f14`.


## Claude review follow-up: A–D

### A. Spent-sheet rates by DPI

Each column pools 12 sheets, with rates divided by eligible cohort members. P-sheets are different content at different DPIs, so this is a useful corpus comparison, not a matched-content causal experiment. Pair-existence stages and deterministic cover stages are different views of the same cohort, not a single sequential waterfall.

| stage | 200 DPI | 300 DPI | 600 DPI |
|---|---:|---:|---:|
| eligible members | 2847 (100.0%) | 3718 (100.0%) | 4233 (100.0%) |
| any non-self structural pass | 942 (33.1%) | 1532 (41.2%) | 1908 (45.1%) |
| plus hygiene and band | 749 (26.3%) | 1210 (32.5%) | 1450 (34.3%) |
| plus relative ≤2 | 688 (24.2%) | 1158 (31.1%) | 1418 (33.5%) |
| plus absolute ≤0.08 | 399 (14.0%) | 712 (19.2%) | 794 (18.8%) |
| self-admissible canonical | 1628 (57.2%) | 2459 (66.1%) | 2848 (67.3%) |
| cover below distinct-design quorum | 1543 (54.2%) | 2312 (62.2%) | 2714 (64.1%) |
| no self candidate left in cover | 1195 (42.0%) | 1224 (32.9%) | 1358 (32.1%) |
| planned group | 109 (3.8%) | 182 (4.9%) | 161 (3.8%) |
| combined ownership veto | 0 (0.0%) | 9 (0.2%) | 88 (2.1%) |
| survives final quorum before economy | 109 (3.8%) | 159 (4.3%) | 33 (0.8%) |

The absolute-pass rate is 19.2% at 300 versus 18.8% at 600; it does not collapse in this comparison. Planned membership falls from 4.9% to 3.8%, while post-ownership/quorum survival falls from 4.3% to 0.8%. Combined-veto counts are 9 versus 88. The rates do not prove that DPI alone causes these differences. All per-document counts and stage definitions are in `measurements.json` and `dpi-rates.json`.

### B. Pristine design and source-mask decomposition

Match method: take the OCR symbol box and find the pristine glyph whose ink has the largest captured fraction; require ≥50% captured ink, reject a second glyph with more than half the top score, and reject OCR/truth character disagreement. This is an approximate spatial match and can still be imperfect. A same design has the same truth character and font hash; point size is retained independently. All tested non-self fits are considered, including fits failing safety checks; only the 24-nearest candidate fits exist. Statistics below use each matched member’s lowest error in each design class.

| DPI | matched / eligible | design | members with fit | best error median / p90 | best > 0.08 | tested pairs > 0.08 / total |
|---|---:|---|---:|---:|---:|---:|
| 300 | 2638 / 2968 (88.9%) | same | 1934 | 0.1045 / 0.3503 | 1162 | 3410 / 4618 |
| 300 | 2638 / 2968 (88.9%) | different | 2638 | 0.1731 / 0.3221 | 2340 | 35850 / 36342 |
| 600 | 3204 / 3523 (90.9%) | same | 2509 | 0.0934 / 0.3348 | 1443 | 4347 / 6180 |
| 600 | 3204 / 3523 (90.9%) | different | 3204 | 0.1902 / 0.3397 | 2939 | 48224 / 48765 |

`design-pairs-summary.json` gives document-level match and exclusion counts; `local/c2b/truth-pair-details.json` records matched members and their best same/different-design fits. These are observed distributions, not evidence that every rejected pair should be substituted.

The seeded sample selects 60 same-design members per DPI with a best same-design error above 0.08, round-robin by document, plus the 12 previously reviewed pairs. Of the 12 examples, one could not be conservatively matched; the completed sample has 60 same-design cases at 300 and 63 at 600, plus other-design examples. `local/c2b/decomposition-records.json` contains all 132 records and pair identities. Fractions are weighted by pristine ink intensity; “mask-only” means true ink present in the scanned source but absent from the prepared local source at a 0.05 coverage threshold. It is a diagnostic threshold, not an exact causal ownership proof.

| same-design sample metric (median / p90) | 300 | 600 |
|---|---:|---:|
| original fit | 0.15427 / 0.58059 | 0.16627 / 0.58432 |
| pristine ink missing in prepared source | 0.04503 / 0.23203 | 0.05151 / 0.18258 |
| pristine ink missing in scan | 0.05803 / 0.20510 | 0.05474 / 0.18374 |
| additional mask-only missing ink | 0.00012 / 0.00128 | 0.00000 / 0.00066 |
| unregistered fit | 0.27201 / 0.63246 | 0.26926 / 0.65364 |
| fit reduction from registration | 0.07916 / 0.20995 | 0.08125 / 0.19348 |
| fit after source-ink repair | 0.15338 / 0.58052 | 0.16624 / 0.58430 |
| fit after oracle relative scale | 0.14676 / 0.26941 | 0.12869 / 0.25903 |
| fit after both; residual | 0.14138 / 0.26840 | 0.12865 / 0.25895 |

Median / p90 absolute log error between x-height scale ratio and oracle point-size ratio is 0.0256 / 0.2937 at 300 DPI and 0.0161 / 0.2155 at 600 DPI. Registration translation norm medians are 1.066 / 0.956 normalized-canvas pixels. After repair, 0 of 60 at 300 DPI and 0 of 63 at 600 DPI pass 0.08; after oracle relative scale, 5 of 60 and 8 of 63 pass, respectively. The scale counterfactual anchors the member to the canonical’s measured x-height adjusted by the truth point-size ratio; it is not an independently known absolute scale. The source-ink repair uses pristine support and excludes overlapping pristine neighbor ink, keeps the canonical fixed, and reoptimizes registration; it cannot be implemented without truth. The residual after both corrections still includes genuine shape, damage, fitting and antialias differences and is not an isolated antialias measurement. Reconstructed prepared fields and original errors agree with Rust to at worst 4.5e-16 and 2.6e-15 respectively.

`local/c2b/masking-contact.png` shows prepared | scan | pristine for the 40 highest mask-only-loss 600-DPI examples in this sample; SHA-256 `061a2720c8d744924982c453145c6340a958f2964b8a450bc6828ea7bd05010e`. Visible white cuts also occur in the scan, so they must not be attributed to masking merely from the old source-only panel.

### C. Physical-halo diagnostic

With both `SCANWEAVE_RESEARCH_C2B_HALO` and `SCANWEAVE_RESEARCH_C2B_TRACE` set, the experiment uses a 4-pixel grayscale halo and a 3-pixel distance limit at 600 DPI, preserving the foreign-ink exclusion rule, q3 checks, quorum and economy. This changes normalized fields and is an **unqualified diagnostic**, not a proposed candidate. The baseline keeps the original two-pixel halo and 1.5-pixel limit. All per-document new/lost member IDs and overlap details are in `halo-results.json`; all newly passing non-self pairs, their truth classifications and IDs are in `local/c2b/halo-pairs.json`.

| document | baseline planned | halo planned | newly planned | no longer planned | new passing same / different / unmatched pairs | OCR-box overlap cases |
|---|---:|---:|---:|---:|---:|---:|
| font01-test-2 | 18 | 18 | 0 | 0 | 0 / 0 / 0 | 1 |
| font01-train-2 | 15 | 15 | 0 | 0 | 2 / 2 / 0 | 2 |
| font01-validation-2 | 6 | 6 | 0 | 0 | 1 / 0 / 0 | 0 |
| p2-6 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | 3 |
| p2-7 | 6 | 6 | 0 | 0 | 2 / 0 / 0 | 3 |
| p2-8 | 22 | 25 | 3 | 0 | 6 / 4 / 0 | 1 |
| p2pp-6 | 12 | 9 | 0 | 3 | 7 / 1 / 0 | 1 |
| p2pp-7 | 22 | 23 | 4 | 3 | 8 / 6 / 0 | 2 |
| p2pp-8 | 23 | 23 | 3 | 3 | 3 / 5 / 1 | 3 |
| p2prime-6 | 12 | 12 | 0 | 0 | 1 / 2 / 0 | 2 |
| p2prime-7 | 8 | 9 | 1 | 0 | 8 / 0 / 0 | 5 |
| p2prime-8 | 17 | 17 | 0 | 0 | 11 / 0 / 2 | 3 |
| **total** | **161** | **163** | **11** | **9** | **49 / 20 / 3** | **26** |

New passing pairs passed structural, hygiene, weight band, relative and absolute fit filters in the halo run and did not pass that combination in baseline. Every listed pair was tested in baseline. OCR-box overlap counts use newly admitted support pixels with scan grayscale <245 inside another OCR symbol box; boxes can overlap the member’s own ink, so these are risk flags, not proven foreign-ink admissions. Truth-unmatched pairs are explicitly flagged, not assumed safe.

### D. Decision and checks

The halo counterfactual gained 11 planned members and lost 9, for a net gain of 2, versus the required few hundred, and admitted 20 different-design pairs. Mask-only loss was negligible in the sampled cases; oracle-relative scaling improved some fits at both DPIs but did not demonstrate a 600-specific, implementable physical correction or a few-hundred-member planned-group gain. Recommend closing #27 item 2 as **no useful safe gain for the tested bounded approach**, while retaining the raw evidence and uncertainty about untested methods. No candidate was implemented and no Phase 3 qualification, holdout, or new-substitution review panels are claimed.

The capture build produced byte-identical PDFs to the baseline trace for 21/21 completed baseline captures. With both research switches enabled, 200- and 300-DPI controls matched baseline hashes (`detail-identity.json`, `halo-identity.json`). Workspace tests passed before the final trace-only guard, focused glyph-sharing tests passed after it, and CI clippy passed after the guard. Test-generated `qualification/evidence/` files were restored. The earlier Python CI gates were not rerun because no candidate was introduced. The stored full-page counterfactual PDFs are research artifacts and are not qualified for use.
