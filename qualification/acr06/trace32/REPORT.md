# Issue 32 qualification: skip source tracing for raster-owned regions

Status: qualified against the owner's amended contract, subject to independent review. Product base `36ad4eaf4eee8084335ea5f4be3ecc2a4ab6fc2e`. The original byte-identity requirement was amended to permit font design bounds and trace diagnostics to reflect the shapes actually constructed, contingent on exact renderer and semantic parity. The changed PDFs are explicitly identified below.

## Profile and implementation

The unmodified release baseline on competitive 600 (`--dpi 600 --profile clearscan --glyph-sharing off`) took 74.47 s, 869380 KiB peak RSS; page tracing/placement/cleanup summed to 49.862 s. A temporary instrumented build (script `instrument.py`) produced the same PDF hash as main. It recorded 190 geometry-rejected source traces, all successful: 179 had final raster reason `ContactNonText`, 11 `UnsupportedContent`. These are counts of occurrences, not an assertion that all tracing-stage time is solely these calls.

After donor-geometry rejection, the local trace is now called only if the unit index appears in a currently vector-disposition region. No DPI, thresholds, donor geometry, region planning, or fidelity decision was changed. `plan_regions` places each owned unit into exactly one text region; subsequent transitions only degrade vector regions to raster. Thus an already-raster region cannot later emit a visible local shape. Encoding walks vector regions only; invisible owner CIDs use the semantic owner shape. The skip neither inserts `missing` nor changes the raster disposition, coverage, or fallback reason: a failure or success of a local trace for that region cannot promote it to vector. Removing a successful unused shape can change diagnostics and document-wide font bounds, which are deliberately computed from the actual remaining shapes. This proof is limited to the existing region and encoding flow and the no-promotion invariant.

The unit callback test checks that raster-owned work is never invoked and vector-eligible work is invoked. The `geometry_fallback` integration fixture forces a real `rejected_donor_geometry` using existing m1d ink. With protection, the local shape is absent, the glyph remains invisible and no occurrence, encoding, or owner CID points to it; without protection, the same geometry rejection produces its source shape. All glyph IDs in the font are derived from those encoding entries.

## PDF identity and trace census

Hashes are SHA-256. All three repetitions within each timed arm produced the same hash. The removed-shape count is the reduction in summed page `font_glyphs`, i.e. successful local traces removed, not a count of any skipped traces that would have failed. Receipts has zero geometry rejections, so no geometry trace is skipped there; its PDF is identical. Zero removed successful shapes on other inputs does not establish that no failed trace was skipped.

| Input / mode | Main SHA-256 | Candidate SHA-256 | PDF identical | Removed successful local shapes |
|---|---|---|---|---:|
| competitive600 | `24999ab886a138bfebc21d5806c15d4cab6d43456b5c3c33092fd3842c637ef4` | `4a93a5fa1fd39c3b35bfb2f7564fd0b4802ea9e783ba9f99358d0c87f3dbb329` | no | 179 |
| competitive300 | `78ca459663e5aa0f9530f597cd3e49dd67d6a2da0ecba5afff4a5e3bb74df48b` | `78ca459663e5aa0f9530f597cd3e49dd67d6a2da0ecba5afff4a5e3bb74df48b` | yes | 0 |
| single | `7f3806abecc6a2fda5661318ca753c00893084f6a90b53de4747d4a4ad85c77f` | `7f3806abecc6a2fda5661318ca753c00893084f6a90b53de4747d4a4ad85c77f` | yes | 6 |
| financial | `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd` | `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd` | yes | 59 |
| forms | `1aa7b517618cf129b976d26aa7dd781e838bac79e96380e14b7ad74f2d0c0639` | `75dfda81cef2a5857328ede7dd76279d72e65a838fb6d352b7f6ea6673d383ff` | no | 255 |
| historical | `8486f69c3d694c4a760ad4845c2cb6b64161467adc3e4061fef9b771b84abd2e` | `8486f69c3d694c4a760ad4845c2cb6b64161467adc3e4061fef9b771b84abd2e` | yes | 0 |
| mixed | `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a` | `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a` | yes | 97 |
| receipts | `d2da6b69bb803e6c3a5f5db0c6735f3d3357a2f84f12a98fc99fc3ef836d9360` | `d2da6b69bb803e6c3a5f5db0c6735f3d3357a2f84f12a98fc99fc3ef836d9360` | yes | 0 |
| competitive600-q3 | `24999ab886a138bfebc21d5806c15d4cab6d43456b5c3c33092fd3842c637ef4` | `4a93a5fa1fd39c3b35bfb2f7564fd0b4802ea9e783ba9f99358d0c87f3dbb329` | no | 179 |
| single-q3 | `aa274aec2fcc3542768cfd9a8703ea7118980135392ddacf1d7bef0cefbed68b` | `aa274aec2fcc3542768cfd9a8703ea7118980135392ddacf1d7bef0cefbed68b` | yes | 6 |

## Font and PDF byte audit

For each of the three changed input/mode pairs, fontTools compared **every** embedded table. `head` alone differs; `glyf`, `loca`, `hmtx`, `cmap`, `hhea`, `OS/2`, `maxp`, `post`, `name` and all remaining tables are byte-identical. Thus all retained glyph programs and horizontal metrics are unchanged. The `head` table bytes differ only in the indicated bounds; its table-directory checksum changes accordingly. `checkSumAdjustment` is unchanged. No outlines are rewritten. The PDF font descriptor, including `/FontBBox [0 -50 4096 4096]`, is unchanged.

| Input | main head (xMin,yMin,xMax,yMax) | candidate head | Other changed tables |
|---|---|---|---|
| competitive600, off and q3 | -12, -9, 17236, 1030 | -9, -8, 17236, 1030 | none |
| forms | -19, -12, 814, 1024 | -19, -9, 814, 1024 | none |

Original-PDF object comparison found only font stream object 6 changed for forms; in the two competitive600 outputs object 6 and the cross-reference stream object 71 changed. For competitive600 the compressed font stream is 8101 versus 8100 bytes, with unchanged 14112-byte decoded font length; compressed xref data and its offsets account for the remaining file size/offset differences (414503 versus 414505 bytes). Forms' compressed font stream stays 43745 bytes, decoded 103616 bytes, and PDF length and xref remain unchanged (831974 bytes). The original PDFs have no trailer `/ID`; the differing IDs observed in `qpdf --qdf` are generated by that inspection rewrite, not original output bytes. Content streams and raw and decoded image streams are identical. The stream comparison includes text matrices and raster patches.

For all ten pairs, explicit font-dictionary comparisons found identical `/Encoding`, CID-to-GID streams, ToUnicode streams, `/W` and `/DW`. All retained font tables above, page content, and image streams match. PDFium extracted text and Poppler `pdftotext -layout` and `-raw` output match; PDFium sample word searches compare hit offsets/counts on each page (`runs/*-search.log`). Semantic-owner records are equal in the non-timing report diffs. `qpdf --check` and OTS 9.3.0 passed for each PDF and extracted embedded font. Detailed logs and per-page searches are under `qualification/acr06/local/trace32/runs/`; audit scripts are alongside this report.

## Renderer parity

For every byte-changed document, full-page RGB images were compared at 200, 217.3, 300 and 600 DPI. Each matrix entry below means zero changed pixels on every page. MuPDF used only the specified dedicated 1.28.x environment. Byte-identical documents need no raster comparison to establish parity.

| Input | Pages | Poppler 200 / 217.3 / 300 / 600 | PDFium 200 / 217.3 / 300 / 600 | MuPDF 200 / 217.3 / 300 / 600 |
|---|---:|---|---|---|
| competitive600 off | 8 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| competitive600 q3 | 8 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| forms | 2 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

In particular Poppler was tested directly despite `head.yMin` changing; no Poppler pixels changed at any tested scale. Renderer logs are `runs/<input>-<renderer>.log`.

## Sidecar differences

Every pair was recursively diffed; exact paths and list lengths are in `report-diff-<input>.json`. Timing fields include `*_ms`, `stage_timings[_ms]`, and q3 `stage_seconds`. Outside timing and hOCR provenance, differences are only: page `glyph_stats` and `font_glyphs` (omitted unused traces, including their shape indices), document and candidate `font_bytes` / `pdf_bytes` (actual serialized size), and q3 `encoded_font_bytes_before` / `encoded_font_bytes_after` (the measured font serialization size). No ownership, fallback, fidelity, decision, semantic owner, or other reconstruction field differed. Each `pages[].hocr` and `hocr_sha256` differs because Tesseract embeds a random temporary directory in its image path. `check_hocr.py` verified every page equals after normalizing only that directory. `stage_seconds` entries in the raw diff files are timing fields, not behavioral differences.

## Timing and memory

Release `--locked`; sequential, same machine, main/candidate interleaved per repetition (order reversed on repetition 2), three repetitions for the four requested timing inputs. Wall time from `/usr/bin/time -v`; trace is the sum of page `tracing_placement_cleanup`, which includes placement and cleanup as well as tracing. Values are median [minimum, maximum]; RSS is MiB.

| Input | Arm | Wall s | Trace stage s | Peak RSS MiB |
|---|---|---:|---:|---:|
| competitive600 | main | 70.36 [70.29, 71.36] | 46.86 [46.80, 47.38] | 850.18 [849.07, 850.80] |
| competitive600 | candidate | 39.24 [36.72, 39.42] | 15.39 [14.63, 15.53] | 846.90 [845.92, 847.64] |
| single | main | 32.44 [31.99, 32.78] | 22.01 [21.25, 22.01] | 154.53 [154.06, 154.69] |
| single | candidate | 32.16 [32.05, 33.15] | 21.72 [21.50, 22.24] | 154.88 [154.52, 155.15] |
| mixed | main | 112.82 [111.75, 113.28] | 86.94 [85.91, 87.68] | 353.10 [352.73, 353.88] |
| mixed | candidate | 109.02 [108.22, 110.07] | 83.09 [82.47, 83.64] | 352.66 [352.46, 353.02] |
| historical | main | 64.91 [64.50, 65.10] | 6.29 [6.15, 6.30] | 698.37 [698.10, 698.50] |
| historical | candidate | 65.14 [64.63, 65.95] | 6.22 [6.19, 6.42] | 698.43 [697.99, 698.52] |

Competitive600 median wall time fell by 44.2%; median tracing/placement/cleanup fell by 67.1%. Single, mixed and historical results should be interpreted with their ranges rather than as proof of a small speed change.

First-run stage split for every input follows, in seconds. Seg = segmentation/ownership, plan = planning/matching/reconstruction, trace = tracing/placement/cleanup, compose = raster composition/owners. The document-level import, donor collection, font union/build, PDF assembly and all repetitions are retained in `results.json` and the original report JSON; the page stage sums need not add to wall time.

| Input | Arm | Wall | Seg | Plan | Trace | Compose | Peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| competitive600 | main | 70.29 | 1.02 | 6.30 | 46.86 | 1.19 | 850.80 |
| competitive600 | candidate | 39.42 | 1.07 | 6.29 | 15.39 | 1.28 | 845.92 |
| competitive300 | main | 34.43 | 0.22 | 21.76 | 7.15 | 0.85 | 208.60 |
| competitive300 | candidate | 35.30 | 0.22 | 22.54 | 7.21 | 0.88 | 206.76 |
| single | main | 31.99 | 0.11 | 0.27 | 21.25 | 7.23 | 154.06 |
| single | candidate | 32.05 | 0.11 | 0.27 | 21.72 | 6.94 | 154.52 |
| financial | main | 464.71 | 1.49 | 144.72 | 279.76 | 12.19 | 1431.08 |
| financial | candidate | 475.68 | 1.46 | 145.19 | 290.21 | 12.28 | 1432.74 |
| forms | main | 49.09 | 0.94 | 5.38 | 23.99 | 11.77 | 427.90 |
| forms | candidate | 42.16 | 1.00 | 5.36 | 17.59 | 11.57 | 424.71 |
| historical | main | 65.10 | 5.36 | 0.65 | 6.30 | 26.89 | 698.10 |
| historical | candidate | 64.63 | 5.36 | 0.64 | 6.22 | 26.69 | 698.52 |
| mixed | main | 112.82 | 0.57 | 10.71 | 86.94 | 8.00 | 352.73 |
| mixed | candidate | 110.07 | 0.59 | 11.12 | 83.64 | 8.18 | 352.46 |
| receipts | main | 28.42 | 0.98 | 0.11 | 3.04 | 10.44 | 523.24 |
| receipts | candidate | 30.06 | 0.99 | 0.13 | 4.08 | 11.02 | 527.52 |
| competitive600-q3 | main | 69.27 | 0.94 | 5.91 | 44.68 | 1.15 | 855.22 |
| competitive600-q3 | candidate | 39.47 | 0.94 | 5.95 | 15.03 | 1.15 | 847.80 |
| single-q3 | main | 59.11 | 0.10 | 0.26 | 21.07 | 6.38 | 172.92 |
| single-q3 | candidate | 59.35 | 0.11 | 0.25 | 21.03 | 6.43 | 173.58 |

Financial candidate and the later untimed qualification inputs overlapped required Rust/Python checks; their single-run times are not controlled comparisons. The four timing inputs were completed before those checks. The CLI accepts q3 as `--glyph-sharing cover-2.0-ceiling-q3`; the brief's shorthand `q3` was rejected immediately and was rerun using the supported spelling with PDFium set.

## Checks and limits

- `cargo test --workspace --locked`: passed with the new integration test; test-generated tracked `qualification/evidence/` restored afterward.
- `cargo clippy --locked -p scanweave-core -p scanweave-io -p scanweave-cli -- -D warnings`: passed; focused geometry regression rerun after formatting passed.
- All 20 Python CI gates passed. The corpus adapter initially lacked this worktree's `qualification/.venv` and then a manually omitted qpdf environment; it passed when rerun with the supplied shared venv and the same environment as the CI runner. The temporary symlink was removed.
- The renderer tests establish parity on the specified inputs, renderers and scales, not on every possible PDF or rendering implementation. Q3 outputs were tested as requested, not with timing repetitions. Skipped failed traces are not separately counted outside the instrumented main profile. No claim is made that metadata bounds are universally rendering-neutral.

Product commit: `d01c43c32cf3a1e78d7c5ea8175df7d5a3b24477`, pushed to `perf/skip-rejected-donor-trace-32`. No PR was opened. For competitive600 q3, both `encoded_font_bytes_before` and `encoded_font_bytes_after` change from 8101 to 8100, matching the actual compressed embedded font stream; these are derived font-byte diagnostics.
