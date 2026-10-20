"""Generate the engineering report from measured tables; no converter inference."""
import json,gzip
from pathlib import Path
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
load=lambda p:json.loads(p.read_text() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes()))
s=load(B/'scorecard.json');lines=[]
def add(t):lines.append(t)
add('''# ClearScan typography improvement

Review the completed [300 DPI PDF](qualification/clearscan_typography/300/final.pdf), [native-size pages](qualification/clearscan_typography/300/final-native-page00.png), and [800% word comparison](qualification/clearscan_typography/300/final-serif-800pct.png). The equivalent [600 DPI PDF](qualification/clearscan_typography/600/final.pdf) is also complete.

The existing ClearScan implementation now fits bounded contour changes to its retained grayscale witnesses. It reduces excess stroke weight at 300 DPI while preserving canonical sharing and source ownership. A separate concrete defect was fixed: invisible OCR labels depended on a reconstructed glyph's changing geometry. They now use one stable, full-em hidden glyph in the existing shared font, improving native extraction and positional text ordering. Faithful remains independent.

Starting HEAD was `903580f4911ce0ca15377781b70f2acedc960a99`; `08431a7` is its ancestor. The tracked tree was initially clean; unrelated untracked research and frozen evidence were preserved. Implementation commits are `53b949f`, `ec7bcdc`, and `6495218`. Exact input/code/artifact hashes and tool versions are in [run-manifest.json](qualification/clearscan_typography/run-manifest.json). No sealed holdout, new OCR engine, PDF writer, or public experimental profile was used.

Frozen competitor: Acrobat XI Pro11.0.20 under Wine9.0, English(US), ClearScan, Downsample To600dpi; actual reduced backgrounds150dpi. The same eight-page300/600DPI outputs are hash-verified against the original run manifest, not compared with an unrelated three-page document.

## Same-input scorecard

Primary glyph fidelity is fixed-position isolated ink IoU over the same **552 non-space instances**. PDFium uses exact physical dimensions; Poppler uses integer physical DPI. Renderers are not averaged. Raw source samples remain distinct from a renderer's resampled image-only PDF.
''')
for dpi in ['300','600']:
 d=s['documents'][dpi];p=d['previous'];n=d['final'];a=d['adobe'];g=load(B/dpi/'final-geometry.json')['summary'];stage={arm:load(B/dpi/arm/'stages/stage-errors.json')['means'] for arm in ['previous','final']}
 add(f'### {dpi} DPI\n\n| Metric | Previous | Improved | Adobe XI |\n|---|---:|---:|---:|')
 vals=[('Glyph fidelity, PDFium',*[f"{x['isolated_iou']['exact']['pdfium']:.5f}" for x in [p,n,a]]),('Glyph fidelity, Poppler',*[f"{x['isolated_iou']['exact']['poppler']:.5f}" for x in [p,n,a]]),('Moderate-damage PDFium gain over source',*[f"{x['severity']['moderate']['pdfium']['mean_gain']:+.5f}" for x in [p,n,a]]),('PDFium ink-area bias',*[f"{100*g[k+'/pdfium']['mean_ink_area_bias']:+.2f}%" for k in ['previous','final','adobe']]),('PDFium counter-count mismatches /552',*[str(g[k+'/pdfium']['counter_mismatches']) for k in ['previous','final','adobe']]),('Paired vector-only to final IoU change',f"{stage['previous']['composition_delta']:+.5f}",f"{stage['final']['composition_delta']:+.5f}",'not separated'),('Canonical replacements / assigned IDs',f"{p['canonical_replacements']}/{p['canonical_id_count']}",f"{n['canonical_replacements']}/{n['canonical_id_count']}",'not inferred'),('Visible vector occurrences',*[str(x['painted_occurrences']) for x in [p,n,a]]),('Distinct painted outlines',*[str(x['distinct_painted_outline_hashes']) for x in [p,n,a]]),('Raster stream bytes',*[f"{x['streams']['raster']:,}" for x in [p,n,a]]),('Embedded font bytes',*[f"{x['streams']['font']:,}" for x in [p,n,a]]),('Total PDF bytes',*[f"{x['bytes']:,}" for x in [p,n,a]]),('Searchable extracted errors vs source Unicode',*[str(x['ocr_ground_truth_char_errors']['pdfium']) for x in [p,n,a]])]
 for row in vals:add('| '+' | '.join(row)+' |')
 add(f"\nRaw source IoU: **{d['raw_source_isolated_iou']:.5f}**. Improved/searchable-raster size ratio: {n['bytes']/n['qualified_searchable_raster_bytes']:.4f} ({n['qualified_searchable_raster_bytes']:,} B raster candidate); improved/Adobe: {n['bytes']/a['bytes']:.2f}×. Both ScanWeave outputs preserve the inherited one-character OCR error independently of visible glyph identity. Adobe recognition errors are not automatically outline errors.\n")
 add(f"Wall time / peak RSS: previous {p['wall_seconds']:.2f}s / {p['peak_rss_kb']:,}KiB; improved {n['wall_seconds']:.2f}s / {n['peak_rss_kb']:,}KiB. Some runs overlap independent measurements; these are execution records, not an isolated performance benchmark. Pipeline timings remain in the full reports.\n")
add('''The 300 DPI result improves; 600 DPI regresses slightly (about 0.00016 IoU) and is not claimed as an accuracy gain. Neither output exceeds the raw scan's aggregate fidelity. At 300 DPI, moderate-damage mean recovery rises from +0.00429 to +0.01322; 196/253 instances improve over the source and 54 regress. Initially healthy instances still regress on average, though less than before. At 600 DPI only three instances meet the moderate-damage definition; there is no evidence here of general severe-damage recovery.

## What changed in the contours

[Isolated vector paths](qualification/clearscan_typography/300/isolated-vector-outlines.svg) show pristine, previous and final designs in a shared physical frame, independently of bitmap antialiasing.

`trace.rs` evaluates the actual quadratic glyph construction against the original grayscale witness, with local p90 paper and p5 ink normalization. This normalized gamma-encoded intensity is an appearance proxy, not a calibrated physical coverage measurement. Candidate changes are bounded spline configurations and normal displacements of ±0.075/0.15 source pixels. The baseline stays available. A candidate must improve the grayscale objective, preserve component/counter structure and geometric validity, pass the existing 0.90 prototype gate, and retain the ordinary source-preservation floor for unqualified local uses. Acceptance thresholds were not lowered.

The construction frame is held fixed when a contour is inset; the outline is not expanded back into its old damaged ink box. Zero-offset equivalence, counter expansion, disconnected marks, crossed holes and faithful isolation have regression tests. Source observations/masks, donor assignment, Unicode and style groups remain intact. The improved shape is built once through the existing canonical dictionary and font assembler, rather than retraced for each occurrence.

The selected donor masks include antialias fringe from ownership segmentation; binary tracing loses grayscale edge position and preserves scanner-grid staircase turns. This is the measured reason useful witness information is lost. Applying local Otsu indiscriminately to cross-page donors was already a failed earlier variant; this round does not repeat that threshold-only change.

### Independent design-outline evidence

The original-font control validates nominal geometry: 514 identity-matched instances have mean symmetric boundary error about 0.0000007 px and effectively zero area error. One inherited OCR CID selects italic c for pristine e; it is excluded only from that control. Independent PDF renderers need not reproduce the generator's Pillow bitmap, even when design geometry is exact.

Across the same 515 emitted ScanWeave occurrences, mean symmetric design-boundary distance improves **0.3899→0.3690 px**, and mean absolute geometric ink-area bias improves **10.35%→4.33%**. The diagnostic translation-only gain stays about 0.08 px: this is primarily a contour-size correction, not a placement fix. See [design review](qualification/clearscan_typography/design-geometry-review.md) and [hash/placement binding](qualification/clearscan_typography/geometry-binding.json).

The bounded 43-instance stem sample improves mean signed width error **+0.423→+0.218 px** and mean absolute width error **0.539→0.433 px**. Matched cross-sections rise 6,029→6,060; unmatched intervals fall 287→256 out of 6,316 eligible source intervals. These populations/missing intervals are reported, not silently discarded as complete recovery. Kana still has conspicuous terminal/stroke error; the sample is too small to generalize to Japanese typography.

Winding-derived counter-area error also improves: mean relative absolute error7.13%→4.79% across427 source-counter-bearing emitted instances (10.65→7.06 source-pixel² absolute error). This uses exact per-contour Bézier areas and actual placement scale, not thresholded pixels or a fully verified topology model. Thirteen spurious winding-counter instances remain unchanged; this differs from the raster counter-count definition above. The product population retains the known p07s0000 OCR-label conflict, measuring its traced source observation against pristine e; only the original-font control selects original c from that label.

The final 300 DPI PDF has 515 visible occurrences, including 495 canonical replacements from 35 assigned IDs. One a outline still serves 58 healthy/damaged uses across six pages, and e serves 71. There remain 51 distinct painted outlines at 300 and 49 at 600; not every excess partition has been proved a legitimate variant. The additional private hidden rectangle is semantic infrastructure, not a reconstructed character identity.

### Techniques retained and rejected

| Actual 300 DPI trial | PDFium isolated IoU | Outcome |
|---|---:|---|
| Binary spline configurations | 0.92656 | Poppler regression; not selected alone |
| Initial continuous grayscale isocontours | 0.90428 | Lost qualified replacements; rejected |
| Coverage fit without geometric guard | 0.93610 | Extra small counter errors (5→10); rejected |
| Bounded fairing | 0.93596 | More font points/bytes, no gain over simpler fit |
| Stronger fairing/simplification | 0.93216 | Lower PDFium fidelity than simpler fit |
| Local grayscale edge descent | 0.91352 | Lower witness MSE did not imply better final PDF |
| Blur-aware/local descent and continuous variants | about 0.915–0.916 | Rejected |
| Final guarded coverage fit | 0.93114 | Retained; counter errors remain 5, Poppler unchanged |

The failed PDFs, metric tables and source snapshots remain available. No fusion benefit is claimed. This is a bounded improvement in weight and geometry; Adobe remains visibly smoother at 800%. Residual staircase edges, small serifs, punctuation and kana are not solved by the current contour model.

## Stage and final-composition diagnosis

S1–S3 use unique witness populations; S0/S4/S5 use emitted target occurrences. Their means must not be subtracted to form an additive error budget.

| 300 DPI stage | Previous | Improved |
|---|---:|---:|
| S0 source occurrence | 0.94443 | 0.94443 |
| S1 grayscale witness | 0.97279 | 0.97279 |
| S2 binary canonical raster | 0.94173 | 0.94173 |
| S3 actual nominal embedded outline | 0.94737 | 0.94638 |
| S4 placed vector-only PDF | 0.93453 | 0.94255 |
| S5 actual final PDF | 0.91625 | 0.93804 |
| Paired S5−S4 | −0.01829 | −0.00450 |

Nominal-witness bitmap IoU slightly regresses even while design geometry and placed output improve; it is not concealed as a universal stage gain. Final paired loss at 600 DPI remains approximately zero.

Independent inspection reproduced the old 300 DPI penalty: 3,778 PDFium edge samples cross the fixed threshold, predominantly 170.91→167.48 on paper around248.11. Raster-only has zero dark samples in these accepted glyph crops. Alpha-over-paper predicts the change within1.23 gray levels. Poppler has zero threshold crossings and identical S4/S5 thresholded masks. This is normal antialiased composition over near-white paper, not retained dark source text, shifted vectors, or evidence for rectangle whitening. Better fitted contours reduce threshold-sensitive edge samples without changing the paper layer. [Pixel-level findings](qualification/clearscan_typography/composition-review/findings.md) retain the crops and renderer-specific results.

No new cleanup/downsampling operation was added. The named fallback8 source-patch sampling discrepancy remains renderer-dependent; its prior finding is preserved. Image payloads and placement machinery are unchanged by contour fitting.

## Raster, reuse and size

The ownership audit finds **zero original dark pixels retained in raster beneath accepted vectors**, at both resolutions. Superseded source ink is123,760 pixels at300 and479,523 at600; validated fringe suppression is69,324 and212,454. The final raster payload is exactly the baseline622,682/1,153,207B. Background/native byte classes remain582,949/39,733B at300 and359,328/793,879B at600. Mixed native streams are not falsely split into text/artwork compressed bytes by pixel proportions.

Lossless grayscale encoding and exact image-resource sharing are retained. This round spends slightly more font bytes for better300 DPI weight; it does not claim compression improvement. Actual font point counts, nonempty outlines and bytes are in `outline-complexity.json`. The large Adobe size gap remains residual raster content, with native uncertain detail especially costly at600. No CFF or MRC project was started.

## Native text fix and real documents

The first contour rerun exposed a real regression: improving a local outline could fail its unchanged0.98 source gate and unnecessarily return that occurrence to raster. Candidate selection now preserves the prior source gate. All15 real pages retain their previous vector-owned ink inventory.

A second defect was more important for text usability: hidden OCR labels reused arbitrary reconstructed glyphs. Contour changes therefore changed native extraction boxes even on raster-only pages. Hidden labels now use separate CIDs bound to one fixed full-em/half-em-advance glyph in the existing shared font. The initial tiny200-unit frame improved receipt extraction but caused Poppler positional layout sorting errors through overly large text matrices; it was corrected before delivery. With the full-em frame, all eight300 DPI pages have equal normalized Poppler raw/layout text in supplied OCR order, and the formerly affected receipt has **423 PDFium characters =423 Poppler characters**, versus467 previously (56 edit operations). This fixes an ordinary path defect without replacing OCR. A Rust test proves same-Unicode visible/hidden CIDs stay separate and the frame is deduplicated/remapped across pages. [Independent native-text review](qualification/clearscan_typography/owner-frame-review.md) records the exact inspected PDFs.

All ten CORD receipts and five OCR-D historical pages were converted and rendered with both engines using the existing full-page inputs and supplied OCR. Their PDFs, native text, search checks, timing/memory and comparison images are in `qualification/clearscan_typography/real/final/`. Attribution and source licences remain in `qualification/clearscan_competitive/real/ATTRIBUTION.md`. No pristine-font truth is invented for real scans.

Eight of15 pages contain vectors; seven remain raster-only. For example, cord05's corner estimate is luminance116.82 while median paper inside OCR words is219.39: the segmenter measures the table, then treats much of the receipt paper as foreground (median75.6% of word-box pixels). Cord06 yields only one sub-character observation. These cases fail before contour reconstruction because paper/ink ownership is wrong; they are not evidence that more contour smoothing would help. Historical connected text/ornaments also reach ContactNonText/fallback decisions. `real/source-diagnosis.json` records the measured causes. Faint details and full-page artwork remain raster; no broad scanner/segmentation rewrite was introduced.

Native renderer text disagreements fall from10/15 pages to5/15: cord04 and history00–03. All real Poppler raw non-space character sequences and the previous vector-ink inventory are retained. Remaining native hyphen/order discrepancies and low vector coverage are reported in the machine-readable real table. They are not claimed as pristine-relative restoration. Native PDFium finds77/77 receipt numerical-string queries taken from supplied OCR, including the negative cash-change string -16,000. This tests transport/search, not independent recognition accuracy. Remaining glyph/reading-order limits are not hidden by those successful queries.

## Verification and remaining limitations

Workspace tests pass with two independently inherited failures excluded and separately reproduced: `regress_auto_reports_the_selected_candidate` and `clearscan_repairs_a_damaged_glyph_from_same_document_donors`. Their generated evidence was preserved separately and frozen prior evidence restored. E0–E7 pass; inherited P01–P08 visual/native-cardinality failures remain recorded. All final ScanWeave PDFs parse withqpdf, embedded fonts passOTS, native PDFium search executes, and actualCID Unicode matches ActualText. Frozen Adobe600 retains its prior linearization warnings. Determinism is checked by repeating the ordinary300 DPI converter.

Independent review found no blocker in the bounded fit, frame conversion or faithful isolation. Geometric validation still does not model every possible nested-component arrangement; unchanged ownership/topology plus source gates remain necessary. The six-character visual-identity diagnostic observes0/448 mistakes per resolution and renderer; it excludes punctuation/kana/style confusion and cannot establish arbitrary-document safety.

**Largest remaining typography defect:** scanner-grid contour bias and small-feature geometry, not missing reuse or duplicated dark raster. The measured correction improves300 DPI weight and moderate repairs, but does not deliver pristine parity, uniformly smoother serifs/kana, or a600 DPI quality gain. The next contour change should be judged against the calibrated design-boundary and stem diagnostics as well as final rendering; lower witness gray MSE alone proved insufficient in several failed methods. On receipt photographs, local paper/ink ownership is a distinct upstream limitation. These limits remain visible in the completed product PDFs and before/after sheets.
''')
real=load(B/'real/final/metrics.json')
add('## Completed real-page inventory\n\n| Page | Observations | Painted glyphs | Visible GIDs | PDF bytes |\n|---|---:|---:|---:|---:|')
for r in real:add(f"| {r['name']} | {r['observations']} | {r['actual_vector_occurrences']} | {r['actual_used_visible_font_gids']} | {r['bytes']:,} |")
add('\nInspect [receipt02](qualification/clearscan_typography/real/final/cord-02.comparison.png) and [historical00](qualification/clearscan_typography/real/final/history-00.comparison.png). Receipt02 still shows rougher reconstructed small digits than the scan; the source is not declared worse simply because vectors were emitted. Real typography remains less thoroughly improved than the matched synthetic300 DPI families.')
(ROOT/'CLEARSCAN_TYPOGRAPHY_REPORT.md').write_text('\n'.join(lines)+'\n')
