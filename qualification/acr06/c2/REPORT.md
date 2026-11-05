# ACR-06 C2: high-DPI ownership measurement
This is a research-only measurement on previously opened inputs. The enumerated corpus has 38 documents (27 P-sheets, nine FONT-01 sheets, financial and mixed); the request also called this 41. No additional holdout was opened. Page and member indices are zero-based. The document-level data, every member of N, and the full pristine records are in the adjacent JSON files.

The research switch is read only in q3 ownership preflight. `trace` writes each evaluated assignment’s legacy, corrected, combined result and crop geometry to a separate JSON file; it uses the original combined veto. `corrected-only` uses `corrected.unwrap_or(true)`. The rest of q3, including the 2.0 relative and 0.08 absolute ceilings, final three-distinct-design quorum, structural checks and economy fallback, is unchanged. The variable being unset retains q3 behavior. `run.py` uses the pinned PDFium library, `OMP_THREAD_LIMIT=1`, and `RAYON_NUM_THREADS=4`. The sidecars, logs, and PDFs are in `/data/coding/scanweave/qualification/acr06/local/c2/`.

Clean 79b30e5 main and the research build with the switch unset produced the following SHA-256 values (P2″ sheets). Both builds ran with the same environment.

| DPI | main | research unset |
|---|---|---|
| 200 | 397459e597019b70118caa50181e05df3649476a110338df1f39e071ffd675b1 | 397459e597019b70118caa50181e05df3649476a110338df1f39e071ffd675b1 |
| 300 | 6b27432cf3e6964ed2cc3c525736db2bb2946f57dd9d0b530f7f8396d730586d | 6b27432cf3e6964ed2cc3c525736db2bb2946f57dd9d0b530f7f8396d730586d |
| 600 | a81ac0b203e3e3e9b7d9b22df31ca9427172a7012583178c499b1cd29a1b4db3 | a81ac0b203e3e3e9b7d9b22df31ca9427172a7012583178c499b1cd29a1b4db3 |

Trace PDF comparisons with the saved PR #26 q3 outputs: 38/38 byte-identical; mismatches: none. Both `cargo test -p scanweave-io` runs passed, with and without the pinned PDFium override, and generated evidence was restored.

## Ownership contingency

Each cell counts preflight assignments, not final substitutions. `false` means the check did not find an exception, `true` means it did, and `none` means invalid geometry; invalid counts as an exception. Legacy-only means legacy is true or invalid while corrected is false. Corrected rejects include true and invalid. Financial is separated because of its non-integer transform.

| DPI/category | legacy false, corrected false | legacy false, corrected true | legacy true, corrected false | legacy true, corrected true | other cells including invalid | legacy-only | corrected rejects |
|---|---:|---:|---:|---:|---|---:|---:|
| 200 | 108 | 0 | 0 | 0 | {} | 0 | 0 |
| 300 | 406 | 0 | 0 | 10 | {} | 0 | 10 |
| 600 | 73 | 23 | 0 | 0 | {"none/false": 47, "none/true": 15} | 47 | 38 |
| financial-nonint | 1513 | 0 | 2 | 11 | {} | 2 | 11 |

## New substitutions and economy

N comprises non-self substitutions accepted by corrected-only but not q3. A legacy-only preflight assignment need not enter N: canonical rejection, final quorum and economy can discard its group. `measurements.json` records every N member, its page, ID, canonical, absolute and relative fit error, final distinct-design witness count, and check outcomes. The preflight does not expose a continuous margin. Font bytes are the sidecar’s encoded font-byte total; PDF bytes are file sizes.

The minimum final witness count in N is 3; the largest absolute and relative fit errors are 0.078791 and 1.402098.

| Document | DPI | N | off PDF/font bytes | q3 PDF/font bytes | corrected PDF/font bytes | q3 → corrected retired outlines (gross/net) |
|---|---:|---:|---:|---:|---:|---:|
| p2-0 | 200 | 0 | 351126/79436 | 350887/78942 | 350887/78942 | 6/4 → 6/4 |
| p2-1 | 200 | 0 | 423847/97113 | 423847/97113 | 423847/97113 | 0/0 → 0/0 |
| p2-2 | 200 | 0 | 395569/82800 | 395486/82489 | 395486/82489 | 6/4 → 6/4 |
| p2-3 | 300 | 0 | 235970/99037 | 232962/95398 | 232962/95398 | 16/12 → 16/12 |
| p2-4 | 300 | 0 | 219351/96964 | 218405/95765 | 218405/95765 | 6/4 → 6/4 |
| p2-5 | 300 | 0 | 539438/124259 | 538465/121690 | 538465/121690 | 22/15 → 22/15 |
| p2-6 | 600 | 0 | 1060220/110008 | 1060220/110008 | 1060220/110008 | 0/0 → 0/0 |
| p2-7 | 600 | 4 | 1091322/128334 | 1091322/128334 | 1090335/126997 | 0/0 → 6/4 |
| p2-8 | 600 | 6 | 1007964/118641 | 1007790/118085 | 1005995/116249 | 6/4 → 15/10 |
| p2prime-0 | 200 | 0 | 369241/76646 | 367912/75039 | 367912/75039 | 11/7 → 11/7 |
| p2prime-1 | 200 | 0 | 407463/78991 | 405558/76840 | 405558/76840 | 15/11 → 15/11 |
| p2prime-2 | 200 | 0 | 421335/107234 | 419438/104994 | 419438/104994 | 16/11 → 16/11 |
| p2prime-3 | 300 | 0 | 539878/114823 | 538022/112648 | 538022/112648 | 15/10 → 15/10 |
| p2prime-4 | 300 | 0 | 487097/115928 | 484796/113319 | 484796/113319 | 13/9 → 13/9 |
| p2prime-5 | 300 | 0 | 545200/112450 | 543873/110814 | 543873/110814 | 6/4 → 6/4 |
| p2prime-6 | 600 | 2 | 1102835/134327 | 1102835/134327 | 1102986/134170 | 0/0 → 3/2 |
| p2prime-7 | 600 | 3 | 1270843/140221 | 1270843/140221 | 1270403/139459 | 0/0 → 4/3 |
| p2prime-8 | 600 | 6 | 1132113/135408 | 1131082/134058 | 1129226/132162 | 6/4 → 13/9 |
| p2pp-0 | 200 | 0 | 364598/90471 | 362882/88476 | 362882/88476 | 10/7 → 10/7 |
| p2pp-1 | 200 | 0 | 337666/78158 | 337496/77759 | 337496/77759 | 3/2 → 3/2 |
| p2pp-2 | 200 | 0 | 335312/69766 | 333659/67832 | 333659/67832 | 14/10 → 14/10 |
| p2pp-3 | 300 | 0 | 227702/104922 | 227435/104365 | 227435/104365 | 5/3 → 5/3 |
| p2pp-4 | 300 | 0 | 429926/105470 | 427945/103188 | 427945/103188 | 11/8 → 11/8 |
| p2pp-5 | 300 | 0 | 477347/110300 | 474257/106772 | 474257/106772 | 26/19 → 26/19 |
| p2pp-6 | 600 | 2 | 926741/117322 | 926703/116949 | 926139/116337 | 3/2 → 6/4 |
| p2pp-7 | 600 | 0 | 988893/125027 | 988787/124611 | 988787/124611 | 3/2 → 3/2 |
| p2pp-8 | 600 | 6 | 937899/131451 | 937968/131175 | 937010/129861 | 5/3 → 11/7 |
| font01-train-0 | 200 | 0 | 328837/77422 | 326727/74997 | 326727/74997 | 17/12 → 17/12 |
| font01-train-1 | 300 | 0 | 451502/99861 | 449001/97057 | 449001/97057 | 12/9 → 12/9 |
| font01-train-2 | 600 | 0 | 898250/101221 | 898250/101221 | 898250/101221 | 1/0 → 1/0 |
| font01-validation-0 | 200 | 0 | 273701/66504 | 273609/66141 | 273609/66141 | 6/4 → 6/4 |
| font01-validation-1 | 300 | 0 | 180461/91281 | 179456/90042 | 179456/90042 | 4/3 → 4/3 |
| font01-validation-2 | 600 | 2 | 750491/88745 | 750491/88745 | 750254/88239 | 0/0 → 2/1 |
| font01-test-0 | 200 | 0 | 294280/61746 | 294235/61464 | 294235/61464 | 2/1 → 2/1 |
| font01-test-1 | 300 | 0 | 196306/96085 | 195466/94804 | 195466/94804 | 8/5 → 8/5 |
| font01-test-2 | 600 | 4 | 825528/96379 | 825397/95954 | 824660/95189 | 3/2 → 9/6 |
| financial | 300 | 6 | 2849237/727259 | 2792966/662103 | 2792816/661940 | 499/326 → 501/327 |
| mixed | 300 | 0 | 917603/249013 | 911922/241136 | 911922/241136 | 107/81 → 107/81 |

| DPI/category | N | off PDF/font | q3 PDF/font | corrected PDF/font | q3 → corrected retired outlines (gross/net) |
|---|---:|---:|---:|---:|---:|
| 200 | 0 | 4302975/966287 | 4291736/952086 | 4291736/952086 | 106/73 → 106/73 |
| 300 | 0 | 5447781/1520393 | 5422005/1486998 | 5422005/1486998 | 251/182 → 251/182 |
| 600 | 35 | 11993099/1427084 | 11991688/1423688 | 11984265/1414503 | 27/17 → 73/48 |
| financial-nonint | 6 | 2849237/727259 | 2792966/662103 | 2792816/661940 | 499/326 → 501/327 |

## Pristine fidelity

The opened pristine glyph images were composited into each pristine page exactly as in `p2pp_eval.py`; the unchanged PR #26 metric implementation scores every glyph and sheet for both renderers. This is numeric evaluation only. The table gives corrected-only minus q3 and corrected-only minus off in the mean, followed by the corrected-only minus q3 p95, pooled over per-glyph measurements. Per-sheet summaries and every per-glyph record are in the JSON artifacts. Area-bias p95 is the p95 of absolute bias.

| DPI | renderer | metric | corrected − q3 mean | corrected − off mean | corrected − q3 p95 |
|---|---|---|---:|---:|---:|
| 200 | pdfium | error | 0 | 5.77556e-05 | 0 |
| 200 | pdfium | iou | 0 | -0.000281263 | 0 |
| 200 | pdfium | contour_distance | 0 | -0.0020438 | 0 |
| 200 | pdfium | rigid_contour_distance | 0 | -0.00307012 | 0 |
| 200 | pdfium | area_bias | 0 | -0.000278791 | 0 |
| 200 | poppler | error | 0 | 4.32848e-05 | 0 |
| 200 | poppler | iou | 0 | -0.00019144 | 0 |
| 200 | poppler | contour_distance | 0 | -0.00184427 | 0 |
| 200 | poppler | rigid_contour_distance | 0 | -0.00229793 | 0 |
| 200 | poppler | area_bias | 0 | -0.000268098 | 0 |
| 300 | pdfium | error | 0 | 0.000164339 | 0 |
| 300 | pdfium | iou | 0 | -0.000364105 | 0 |
| 300 | pdfium | contour_distance | 0 | -0.000425595 | 0 |
| 300 | pdfium | rigid_contour_distance | 0 | -0.000106388 | 0 |
| 300 | pdfium | area_bias | 0 | -0.00033451 | 0 |
| 300 | poppler | error | 0 | 0.000132646 | 0 |
| 300 | poppler | iou | 0 | -0.000259597 | 0 |
| 300 | poppler | contour_distance | 0 | -0.00110361 | 0 |
| 300 | poppler | rigid_contour_distance | 0 | -0.00116261 | 0 |
| 300 | poppler | area_bias | 0 | -0.000354388 | 0 |
| 600 | pdfium | error | 7.07392e-05 | 8.71561e-05 | 0.000175778 |
| 600 | pdfium | iou | -0.000120758 | -0.000160785 | 0 |
| 600 | pdfium | contour_distance | 0.000445329 | 0.00039666 | 0 |
| 600 | pdfium | rigid_contour_distance | 0.000416605 | 0.000577902 | 0 |
| 600 | pdfium | area_bias | -6.96909e-05 | -8.88417e-05 | 0 |
| 600 | poppler | error | 6.41033e-05 | 7.67972e-05 | 0 |
| 600 | poppler | iou | -0.000111683 | -0.000144605 | 0 |
| 600 | poppler | contour_distance | 0.000337997 | 0.000363127 | 0 |
| 600 | poppler | rigid_contour_distance | 0.000965554 | 0.00130745 | 0 |
| 600 | poppler | area_bias | -6.7425e-05 | -8.36149e-05 | 0 |

Largest individual increases in pristine error at 600 DPI (truth IDs, not OCR symbol IDs; boxes may overlap):

| Document | truth ID | renderer | q3 error | corrected error | increase |
|---|---|---|---:|---:|---:|
| p2-7 | 88ebe5e5c67a5c9290f5e5a7 | poppler | 0.085716 | 0.143299 | 0.057583 |
| p2-7 | 88ebe5e5c67a5c9290f5e5a7 | pdfium | 0.087838 | 0.145152 | 0.057314 |
| p2-7 | 3bef0e8a7fbcc2746cd98711 | poppler | 0.094963 | 0.138235 | 0.043272 |
| p2pp-8 | bf71dbf986873cca59c6f6e0 | poppler | 0.090935 | 0.133588 | 0.042653 |
| p2prime-8 | 3f8b9057fc5b64e1493c2a53 | poppler | 0.128776 | 0.169758 | 0.040982 |
| p2-7 | a7c3e6b9d9a81e5924a6d379 | pdfium | 0.089093 | 0.129882 | 0.040789 |
| p2prime-8 | 3f8b9057fc5b64e1493c2a53 | pdfium | 0.131070 | 0.171162 | 0.040092 |
| p2-7 | 3bef0e8a7fbcc2746cd98711 | pdfium | 0.098494 | 0.138173 | 0.039679 |
| p2-7 | a7c3e6b9d9a81e5924a6d379 | poppler | 0.088159 | 0.126618 | 0.038459 |
| p2pp-8 | bf71dbf986873cca59c6f6e0 | pdfium | 0.105711 | 0.138384 | 0.032673 |

## Ownership, panels and function

An additional native-resolution render comparison applies the existing owned-component thresholds to source crops and text-only default and corrected crops with each renderer; it removes image and form XObjects before rendering. 3 of 82 renderer/member checks fired. Nearby text can overlap, and the source mask is inferred from grayscale, so this is an approximate independent check, not an exact ownership proof. Flags are in `panels-and-owned-check.json`. Accepted fits also passed the existing hard structural checks.

For the 35 members of N at 600 DPI, the contact sheets contain 70 rows (one per renderer/member), sampling: none. Each row uses native 600-DPI pixels for source, default, corrected and the canonical at its own accepted placement. Paths and SHA-256 hashes are in `panels-and-owned-check.json`.

Functional checks: qpdf, OTS on each embedded font, and PDFium and Poppler extraction versus q3 across off, q3 and corrected-only. Issues: none. Exact results are in `functional.json`.

## Serial runtime

These `/usr/bin/time -v` runs were performed one at a time after the other study processes completed, using the same thread limits and CPU affinity 0,6,10,18,22. At the start the shared host was about 77% idle overall; other user processes were active, so external contention cannot be ruled out. Each arm has one run, with q3 first; caching and run-to-run variation can affect the comparison.

| Document | arm | wall seconds | peak RSS KiB |
|---|---|---:|---:|
| p2pp-6 | q3 | 116.74 | 444168 |
| p2pp-6 | corrected-only | 117.44 | 444228 |
| p2pp-7 | q3 | 132.90 | 444852 |
| p2pp-7 | corrected-only | 133.15 | 445560 |
| p2pp-8 | q3 | 131.78 | 444164 |
| p2pp-8 | corrected-only | 131.93 | 443940 |
| financial | q3 | 893.38 | 1920768 |
| financial | corrected-only | 897.05 | 1782812 |

## Financial non-integer transform

The 1813 px over 435 pt dimension gives 435/1813 = 0.239933811362 pt per source pixel; the trace records horizontal scales [0.2399338113623828] and vertical scales [0.239924670433145] pt per pixel. The horizontal scale matches 435/1813. Financial has 6 members in N and 7 removals in the PR #26 ledger, with 4 in both, 2 only in N and 3 only in the earlier removal list. The complete IDs are retained in `measurements.json`.

## Findings requiring review

P2′ sheet 6 is an economy anomaly: its encoded font shrank by 157 bytes while its PDF grew by 151 bytes under corrected-only.

The largest observed 600-DPI pristine-error increase is on P2 sheet 7: truth glyph `88ebe5e5c67a5c9290f5e5a7` overlaps N member `w000102s0005`; Poppler error rises from 0.085716 to 0.143299. Two other high-increase P2 sheet 7 truth boxes overlap N members `w000001s0004` and `w000044s0001`. The box overlap links are spatial, not a claim of oracle identity. These are concrete fidelity concerns for review, even though the owned-component screen may not flag them.

Native-render owned-component flags: [('p2-7', 0, 'w000044s0001', 'poppler', [{'area': 6, 'mass': 3.3058823529411763}]), ('p2prime-8', 0, 'w000050s0005', 'pdfium', [{'area': 7, 'mass': 3.729411764705882}]), ('p2prime-8', 0, 'w000050s0005', 'poppler', [{'area': 13, 'mass': 6.239215686274511}])]. Functional issues: none. Q3-only accepted members: none. Changed retained bindings: none. The approximate independent check has the limitations described above; a clear result is not proof of isolated source ownership. Review the panels and all member records before drawing a stronger conclusion.

At 600 DPI, corrected-only recovered 35 substitutions and saved 7,423 aggregate PDF bytes against q3, or 0.0619% of the 11,991,688 q3 bytes. This is a negligible practical PDF-size benefit on this spent corpus. The pooled mean error increases and the larger individual increases are reported above; these measurements do not establish behavior on new data.
