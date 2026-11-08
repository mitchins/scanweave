import json,statistics
from pathlib import Path
p=Path('/data/coding/scanweave/qualification/acr06/trace32');r=json.load(open(p/'results.json'));names=['competitive600','competitive300','single','financial','forms','historical','mixed','receipts','competitive600-q3','single-q3']
s='''# Issue 32 qualification: skip source tracing for raster-owned regions

Status: qualified against the owner's amended contract, subject to independent review. Product base `36ad4eaf4eee8084335ea5f4be3ecc2a4ab6fc2e`. The original byte-identity requirement was amended to permit font design bounds and trace diagnostics to reflect the shapes actually constructed, contingent on exact renderer and semantic parity. The changed PDFs are explicitly identified below.

## Profile and implementation

The unmodified release baseline on competitive 600 (`--dpi 600 --profile clearscan --glyph-sharing off`) took 74.47 s, 869380 KiB peak RSS; page tracing/placement/cleanup summed to 49.862 s. A temporary instrumented build (script `instrument.py`) produced the same PDF hash as main. It recorded 190 geometry-rejected source traces, all successful: 179 had final raster reason `ContactNonText`, 11 `UnsupportedContent`. These are counts of occurrences, not an assertion that all tracing-stage time is solely these calls.

After donor-geometry rejection, the local trace is now called only if the unit index appears in a currently vector-disposition region. No DPI, thresholds, donor geometry, region planning, or fidelity decision was changed. `plan_regions` places each owned unit into exactly one text region; subsequent transitions only degrade vector regions to raster. Thus an already-raster region cannot later emit a visible local shape. Encoding walks vector regions only; invisible owner CIDs use the semantic owner shape. The skip neither inserts `missing` nor changes the raster disposition, coverage, or fallback reason: a failure or success of a local trace for that region cannot promote it to vector. Removing a successful unused shape can change diagnostics and document-wide font bounds, which are deliberately computed from the actual remaining shapes. This proof is limited to the existing region and encoding flow and the no-promotion invariant.

The unit callback test checks that raster-owned work is never invoked and vector-eligible work is invoked. The `geometry_fallback` integration fixture forces a real `rejected_donor_geometry` using existing m1d ink. With protection, the local shape is absent, the glyph remains invisible and no occurrence, encoding, or owner CID points to it; without protection, the same geometry rejection produces its source shape. All glyph IDs in the font are derived from those encoding entries.

## PDF identity and trace census

Hashes are SHA-256. All three repetitions within each timed arm produced the same hash. The removed-shape count is the reduction in summed page `font_glyphs`, i.e. successful local traces removed, not a count of any skipped traces that would have failed. Receipts has zero geometry rejections, so no geometry trace is skipped there; its PDF is identical. Zero removed successful shapes on other inputs does not establish that no failed trace was skipped.

| Input / mode | Main SHA-256 | Candidate SHA-256 | PDF identical | Removed successful local shapes |
|---|---|---|---|---:|
'''
counts={'competitive600':179,'competitive300':0,'single':6,'financial':59,'forms':255,'historical':0,'mixed':97,'receipts':0,'competitive600-q3':179,'single-q3':6}
for n in names:
 a=r[n]['main'][0]['sha256'];b=r[n]['candidate'][0]['sha256'];s+=f'| {n} | `{a}` | `{b}` | {"yes" if a==b else "no"} | {counts[n]} |\n'
s+='''
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
'''
for n in ['competitive600','single','mixed','historical']:
 for a in ['main','candidate']:
  z=r[n][a];fmt=lambda v:f'{statistics.median(v):.2f} [{min(v):.2f}, {max(v):.2f}]';s+=f'| {n} | {a} | {fmt([x["wall"] for x in z])} | {fmt([x["page_stages_s"]["tracing_placement_cleanup"] for x in z])} | {fmt([x["rss_kib"]/1024 for x in z])} |\n'
s+='''
Competitive600 median wall time fell by 44.2%; median tracing/placement/cleanup fell by 67.1%. Single, mixed and historical results should be interpreted with their ranges rather than as proof of a small speed change.

First-run stage split for every input follows, in seconds. Seg = segmentation/ownership, plan = planning/matching/reconstruction, trace = tracing/placement/cleanup, compose = raster composition/owners. The document-level import, donor collection, font union/build, PDF assembly and all repetitions are retained in `results.json` and the original report JSON; the page stage sums need not add to wall time.

| Input | Arm | Wall | Seg | Plan | Trace | Compose | Peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|
'''
for n in names:
 for a in ('main','candidate'):
  x=r[n][a][0]; t=x['page_stages_s'];s+=f'| {n} | {a} | {x["wall"]:.2f} | {t["segmentation_ownership"]:.2f} | {t["planning_matching_reconstruction"]:.2f} | {t["tracing_placement_cleanup"]:.2f} | {t["raster_composition_and_owners"]:.2f} | {x["rss_kib"]/1024:.2f} |\n'
s+='''
Financial candidate and the later untimed qualification inputs overlapped required Rust/Python checks; their single-run times are not controlled comparisons. The four timing inputs were completed before those checks. The CLI accepts q3 as `--glyph-sharing cover-2.0-ceiling-q3`; the brief's shorthand `q3` was rejected immediately and was rerun using the supported spelling with PDFium set.

## Checks and limits

- `cargo test --workspace --locked`: passed with the new integration test; test-generated tracked `qualification/evidence/` restored afterward.
- `cargo clippy --locked -p scanweave-core -p scanweave-io -p scanweave-cli -- -D warnings`: passed; focused geometry regression rerun after formatting passed.
- All 20 Python CI gates passed. The corpus adapter initially lacked this worktree's `qualification/.venv` and then a manually omitted qpdf environment; it passed when rerun with the supplied shared venv and the same environment as the CI runner. The temporary symlink was removed.
- The renderer tests establish parity on the specified inputs, renderers and scales, not on every possible PDF or rendering implementation. Q3 outputs were tested as requested, not with timing repetitions. Skipped failed traces are not separately counted outside the instrumented main profile. No claim is made that metadata bounds are universally rendering-neutral.
'''
(p/'REPORT.md').write_text(s)
