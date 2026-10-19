"""Produce tables from executed results, never infer unmeasured quality truth."""
import json,csv,re
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[1]
rows=json.loads((B/'group-measurements.json').read_text());assert len(rows)==30 and not any(r.get('missing') for r in rows)
arms=['input','adobe','scanweave','ocrmypdf1','ocrmypdf3','archive'];names=['receipts','historical','financial','mixed','forms'];by={(r['group'],r['arm']):r for r in rows}
score=[]
for r in rows:
 q=[q for p in r['pages'] for q in p['queries']];d={'collection':r['group'],'arm':r['arm'],'pages':len(r['members']),**r['resources'],'converter_visible_owned_occurrences':({'receipts':83,'historical':58,'financial':3569,'mixed':757,'forms':500}[r['group']] if r['arm']=='scanweave' else None),'vectorized_nonspace_pdf_chars':sum(p['visible_nonspace_chars'] for p in r['pages']),'pdfium_nonspace_chars':sum(p['total_nonspace_chars'] for p in r['pages']),'source_Tesseract_queries_passed':sum(qi['found'] for qi in q),'source_Tesseract_queries_total':len(q),'seconds':r['run']['seconds'] if r['run'] else None,'peak_kib':r['peak_kib'] if r['arm']!='adobe' else None,'peak_scope':'GUI runner RSS not Acrobat; unavailable' if r['arm']=='adobe' else 'GNU time command RSS; not aggregated process-tree peak','qpdf_status':r['qpdf']['status'],'ttf_ots_statuses':';'.join(str(f['status']) for f in r['font_validation'])};score.append(d)
with (B/'scorecard.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(score[0]));writer.writeheader();writer.writerows(score)
(B/'scorecard.json').write_text(json.dumps(score,indent=2))
real=json.loads((B/'real-measurements.json').read_text());realby={r['id']:r for r in real}
worst=[('scan-linn','Dense small type and two-column layout; 279 vector occurrences but the single-page PDF grows 95%. Native raster + many font outlines coexist.'),('cord-05','Photographed, weak thermal print; only 37 OCR characters, no vector replacements; 155.9 seconds for the single-page conversion. Raw colour raster dominates.'),('cord-00','Tesseract returns no words. The image survives but the page has no searchable text and no glyph observations.'),('cord-01','OCR is confined to narrow border artefacts (23 characters); 0.04pt-wide invisible runs are lost by PDFium while Poppler extracts them. Main receipt text remains unrecognized.'),('cord-06','Only 12 OCR characters, no vectors; the same very narrow invisible-run / PDFium loss occurs. The background photograph must remain raster.'),('history-03','Faded blackletter, show-through and decorative content; 404 OCR characters, zero vector replacements, 14.99MB output.'),('history-00','Ornament, stamp and aged paper; 906 OCR characters, zero vectors, 9.28MB output. OCR availability alone does not imply usable glyph evidence.'),('history-02','Historical text and shaded page texture; 860 OCR characters but zero vectors, 7.58MB output. No lossless binary mask can preserve its tonal samples.'),('cord-02','34 vectors out of 139 supplied characters; retained native content plus font cost makes the page 17% larger. OCR/number correctness remains distinct from its sharper vector appearance.'),('scan-c03-29','494 vectors coexist with a genuine illustration and textured scan. Native content remains and the single-page output grows 6%.')]
byte_rows=json.loads((B/'byte-accounting.json').read_text());native=json.loads((B/'native-inventory.json').read_text());strict=json.loads((B/'content-ablation.json').read_text())
def fmt(n):return f'{n:,}'
size_table='\n'.join('| '+n+' | '+str(len(by[n,'input']['members']))+' | '+' | '.join(fmt(by[n,a]['resources']['pdf_bytes']) for a in arms)+' |' for n in names)
total={a:sum(by[n,a]['resources']['pdf_bytes'] for n in names) for a in arms}
size_table+='\n| **Total** | **32** | '+' | '.join('**'+fmt(total[a])+'**' for a in arms)+' |'
runtime='\n'.join(f"| {n} | {by[n,'scanweave']['run']['seconds']:.2f} | {by[n,'scanweave']['run']['seconds']/len(by[n,'input']['members']):.2f} | {by[n,'scanweave']['peak_kib']/1024:.1f} |" for n in names)
worst_table='\n'.join(f"| {id} | {fmt(realby[id]['arms']['scanweave']['pdf_bytes'])} | {realby[id]['arms']['scanweave']['reported_vectors']} | {reason} |" for id,reason in worst)
strict_table='\n'.join('| '+str(dpi)+' | '+' | '.join(fmt(next(r['pdf_bytes'] for r in strict if r['dpi']==dpi and r['content_compressed']==c and r['objects_compressed']==o)) for c,o in [(False,False),(True,False),(False,True),(True,True)])+' |' for dpi in [300,600])
transport={a:(sum(s['source_Tesseract_queries_passed'] for s in score if s['arm']==a),sum(s['source_Tesseract_queries_total'] for s in score if s['arm']==a)) for a in arms}
known=json.loads((B/'cord-known-numeric-search.json').read_text());numeric={a:(sum(q['found'] for r in known if r['arm']==a for q in r['queries']),sum(len(r['queries']) for r in known if r['arm']==a)) for a in arms if a!='input'}
search_table='\n'.join(f"| {a} | {transport[a][0]}/{transport[a][1]} | {numeric[a][0]}/{numeric[a][1]} |" for a in arms if a!='input')
# font counts are embedded payloads, not decoded TTF sizes.
totals=[]
for arm in arms:
 totals.append({'arm':arm,'pdf_bytes':total[arm],'raster_bytes':sum(by[n,arm]['resources']['raster_bytes'] for n in names),'font_bytes':sum(by[n,arm]['resources']['font_bytes'] for n in names),'content_bytes':sum(by[n,arm]['resources']['content_bytes'] for n in names),'visible_pdf_nonspace_chars':sum(s['vectorized_nonspace_pdf_chars'] for s in score if s['arm']==arm)})
(B/'totals.json').write_text(json.dumps(totals,indent=2))
report=f'''# ClearScan PDF packaging and real-use delivery

Implementation: **`80b2a42`**. Starting HEAD: `b2ec997e5cce5923da2ad050fc289a5e731d7dce`; tracked tree was clean. Untracked work was recorded and preserved. The sealed holdout was not opened. The prior glyph, contour, paper reconstruction and faithful-profile behavior were retained.

## Delivered

- Lossless Flate encoding of page graphics, embedded TrueType programs, CID maps and Unicode maps.
- Deterministic PDF 1.7 object streams and compressed cross-reference streams, in the existing Rust writer. The compactor accepts **only our own writer output**, not arbitrary input PDFs. Non-stream objects are packed in groups of at most 100; stream payloads and their object identities are retained.
- **`scanweave input.pdf output.pdf`** through Poppler, real Tesseract character boxes, normalized pixel-bound OCR and the existing document-wide ClearScan converter. No new reconstruction mode or OCR engine. `--profile faithful` remains available; the existing image/bundle CLI and library remain available.
- Actual optimized synthetic PDFs, five matched real-document collections / 32 genuine pages, two-renderer measurements, search probes and native-resource accounting.

## 1. Actual optimized PDFs

| Eight-page fixture | Frozen b2ec997 | New Rust output | Saved | Frozen Adobe XI |
|---|---:|---:|---:|---:|
| 300 DPI | 257,972 | **185,119** | **72,853 (28.24%)** | 37,100 |
| 600 DPI | 326,692 | **258,890** | **67,802 (20.75%)** | 50,779 |

Review [300 DPI](qualification/pdf_packaging/300/final.pdf) / [600 DPI](qualification/pdf_packaging/600/final.pdf). These are the native converter outputs, not postprocessed pikepdf files.

**Every decoded stream is unchanged**, including page graphics operations, Unicode/CID maps and glyph programs. DCT image data and colour interpretation remain byte-identical. MediaBox, CropBox and rotation are unchanged. All eight pages at each matched physical resolution render pixel-identically old/new in **both Poppler and PDFium**. Raw and layout Poppler extraction and complete PDFium extraction are unchanged; old/new native search results on the recorded token probes are unchanged. The 300 DPI ordinary conversion repeat is byte-identical.

Thus prior measured glyph fidelity, 531/517 visible vector occurrences and 52/57 painted outlines remain intact. There is **no new typography-quality claim** from this packaging change. The previous 300/600 PDFium pristine-relative IoUs remain 0.9566875 / 0.9682678 by identical rendered pixels.

### Independent serializer ablation

The requested pikepdf result was reproduced exactly: **181,540 / 258,021 B**. Those are a reference, not the shipped ScanWeave sizes. The remaining native-writer difference is 3,579 / 869 B.

The strict factorial below compresses **page content only**, keeping fonts, Unicode maps and images separate. All rows use the same pikepdf resave baseline, so QPDF's own rewrite is not credited to content compression.

| DPI | Resave, neither | Content only | Objects/xref only | Content + objects/xref |
|---|---:|---:|---:|---:|
{strict_table}

Content alone saves 52,780 / 49,076 B; object/xref compression alone saves 3,449 / 1,277 B against that normalized reference. Their strict combination saves 56,229 / 50,353 B. Compressing **all** eligible streams, including fonts/maps, plus object compression gives the requested 181,540 / 258,021 B. The plain resave itself differs from the original by 4,919 / 1,578 B; it is not a content-compression saving. [Independent controls](qualification/pdf_packaging/content-ablation.json), [all-stream controls](qualification/pdf_packaging/serialization-ablation.json).

Native-writer savings reconcile exactly:

| Contribution | 300 DPI saved | 600 DPI saved |
|---|---:|---:|
| Page content payload | 53,115 | 49,325 |
| Embedded font payload | 10,029 | 13,433 |
| Unicode/CID payload | 822 | 855 |
| Net object/xref/syntax representation | 8,887 | 4,189 |
| **Total** | **72,853** | **67,802** |

Raster payload stays **118,980 / 218,200 B**. Font payload is now **15,311 / 19,103 B**, with identical decoded programs. Content is **8,217 / 6,908 B**, only 4.4% / 2.7% of the PDF. Grouped `TJ` emission was therefore not pursued. **`/ActualText` and ownership/spacing operations were not removed or changed.** [Exact accounting](qualification/pdf_packaging/byte-accounting.json).

Synthetic conversion took 41.13 / 88.00 seconds for eight pages (5.14 / 11.00 s/page), with peak RSS 194.6 / 725.5 MiB. These are observed wall times, not an isolated speedup claim; glyph/page processing dominates. The synthetic bundle runs do not include a new OCR pass. Full stage timings are in the run files.

## 2. The ordinary command works

```sh
cargo build --release -p scanweave-cli
./target/release/scanweave input.pdf output.pdf
# optional: --dpi 600 --lang eng+jpn --profile faithful
```

Requires Poppler (`pdfinfo`, `pdftoppm`), Tesseract and installed language data. The new path defaults to ClearScan / 300 DPI. It renders each cropped/rotated page, runs Tesseract with `hocr_char_boxes=1`, creates the existing normalized representation internally and calls the same document converter. Pristine fonts, annotation text and annotation crop boxes are not inference inputs.

A genuine two-page NARA form input converts through that command from **1,294,232 to 850,313 B**, with **500 accepted visible-owned vector occurrences** (678 PDFium paintable text characters). Its current-HEAD repeat is byte-identical; the two observed runs took 57.75 and 89.74 seconds, illustrating timing variability rather than a speed guarantee. Review [input](qualification/pdf_packaging/representative/forms-input.pdf) and [completed output](qualification/pdf_packaging/representative/forms-clearscan.pdf). The CLI also converted a three-page receipt PDF directly (3,236,775 B); two pages have no PDFium text, so that receipt demonstration is **not** presented as successful OCR on every page.

The JSON sidecar includes source/tool identities, page geometry, hashes, actual hOCR and effective arguments. Temporary images/OCR are cleaned up. Input/output/report alias checks protect the input; output and report are staged before publication. Publication comprises two renames, not one transaction. Missing tools, missing languages, malformed inputs and geometry/resource limits report explicit errors. CropBox plus 0/90-degree rotation, invalid input and absent dependencies were checked. Current limits are 80 million pixels/page and 512 MiB of accumulated RGB samples; process peak memory can exceed that sample budget. Large documents may need splitting. `/UserUnit` variants were not independently qualified.

## 3. Genuine development corpus: results, not synthetic extrapolation

32 distinct pages: ten CORD receipts, five OCR-D historical pages, thirteen pages of a 1920 town annual report (financial tables/statements), two illustrated/brochure pages and two scanned federal forms. The thirteen financial pages are **one source publication**, not thirteen independent documents. This is a limited stratified development sample, not population-wide validation.

All engines receive image-only PDFs encoding the same full-page imagery and physical geometry, in five fixed collections with identical membership/order. Converter-internal rasterization is not sample-identical: ScanWeave's Poppler raster differs by one pixel from the embedded image on history-02 (1676×2287 → 1675×2287), scan-linn (2550×3301 → 2550×3300), and both NARA forms (2544×3301 → 2544×3300). This limits OCR/fidelity attribution on those pages; it does not change collection membership or the shared-PDF size comparison. Shared image-only inputs remove prior PDF text. The source image resources are lossless; source photographic capture DPI is unknown where noted. Normal PDF metadata/IDs from initial collection assembly are not typography evidence. Collection bytes below are **actual complete serialized files**, not sums of independently split pages. Single-page diagnostics are kept separately.

| Collection | Pages | Shared raster input | Adobe XI | ScanWeave | OCRmyPDF -O1 | OCRmyPDF -O3 | archive-pdf-tools |
|---|---:|---:|---:|---:|---:|---:|---:|
{size_table}

ScanWeave is smaller than input for financial reports and forms, larger for receipts, historical pages and mixed artwork. Its total is only **0.80% smaller than the shared raster inputs**. It does **not** match Adobe or OCRmyPDF `-O3` on real compression. OCRmyPDF `-O1` preserves the encoded input images closely; `-O3` permits lossy colour/quality optimization. archive-pdf-tools uses its layered raster/mask representation with **CCITT**, not lossy JBIG2 symbol substitution. Its much smaller files are not evidence of canonical vector-font reconstruction.

ScanWeave emits 5,360 visible non-space PDF characters across the collections; Adobe emits 24,142. OCRmyPDF/archive text is invisible semantic overlay, not reconstructed vector coverage. These are text-character counts, not glyph-draw counts or correctness scores. The converter reports 4,967 accepted visible-owned vector occurrences across these collections; ActualText can expand one glyph into several extracted characters. These figures are not a pristine-relative identity test. Unknown real source fonts are not invented as ground truth. Encoded raster/font totals and per-page coverage are in [scorecard.csv](qualification/pdf_packaging/scorecard.csv), [totals](qualification/pdf_packaging/totals.json) and [page measurements](qualification/pdf_packaging/real-measurements.json).

### Readability, content and search

Both renderers were run on every real page/arm. Full-page sheets and native/800% context crops preserve neighbouring content. Photo backgrounds, paper colour, stains, stamps, illustrations, rules and faint print were visually checked in the recorded examples. Source-relative pixel differences are diagnostics, **not** pristine-relative accuracy or a single acceptance gate. The existing converter still makes small typography changes; the brochure mixes a minority of vector glyphs with native raster and retains uneven edge/stroke appearance in enlarged crops; forms retain renderer/extraction ordering differences. No claim of universally correct visual substitution is made.

| Engine | Same-input Tesseract-reference native probes | Known CORD financial-number probes |
|---|---:|---:|
{search_table}

The first column measures transport/agreement with a reference Tesseract pass. archive-pdf-tools consumes that hOCR, so 84/84 is expected preservation, **not independent recognition superiority**. The second column uses 49 distinct per-document query instances from CORD annotations, preserving exact numeric punctuation; none was supplied to OCR/conversion. Adobe's 24/49 versus ScanWeave's 11/49 exposes a real recognition/search gap. It is not automatically a visual glyph-reconstruction error. Zero-query pages are not counted as passes.

One receipt has no recognized words. CORD-01 and CORD-06 have 23/12 supplied characters located in narrow border artefacts; their invisible text matrices have 0.04pt horizontal scale. Poppler extracts those labels while PDFium omits them. Other pages have native ordering/cardinality differences. These remain product defects/limitations, not hidden exclusions. A bounded Tesseract sparse-layout probe increased word counts on some receipts, but was not integrated or credited without a full quality comparison.

The new ScanWeave collection PDFs pass qpdf and embedded-TTF OTS checks. Adobe outputs retain qpdf status-3 linearization/hint-table warnings; they parse and render, and the warnings are preserved. Adobe CFF programs were not asserted to pass standalone TTF OTS. archive-pdf-tools' small glyphless font fails OTS (`cmap: no supported subtables`) despite working PDF rendering/search; that comparator limitation is retained.

### Ten worst real page/document cases

This is a triage list using OCR/search failure, zero/low vector coverage, size growth and runtime, with source inspection. It is not a fabricated pristine-font ranking. Bytes/vectors here are the separately executed **single-page** diagnostics.

| Case | PDF B | Vectors | Observed cause |
|---|---:|---:|---|
{worst_table}

### Runtime and memory

| ScanWeave collection | Wall s | s/page | Command max RSS MiB |
|---|---:|---:|---:|
{runtime}

Timings include ordinary import/OCR/conversion on this host; some jobs ran concurrently. The GNU-time RSS numbers are command-process accounting, **not an aggregated process-tree peak**; concurrent Poppler/Tesseract child memory is not summed. They must not be interpreted as total end-to-end RAM. Adobe times include approximately 83 seconds of GUI automation per collection; its GNU-time RSS is the runner's RSS, **not Acrobat's memory**, so Acrobat memory is unavailable. Archive recoding and separately measured OCR preparation are labelled separately; their sum is an estimate, not one observed end-to-end invocation. A separate ordinary three-page receipt run sampled the CLI and descendants every 50ms: **10.19 seconds, 74.7 MiB peak summed RSS**. Shared pages are counted per process; this is not PSS, and short peaks can be missed. Its PDF was byte-identical to the earlier three-page output. [Process-tree observation](qualification/pdf_packaging/process-tree-memory.json).

Financial-page conversion accounts for 477.8 of 486.1 pipeline seconds, versus 1.44 seconds assembling the reconstructed PDF. Historical donor collection alone takes 130.0 seconds and page conversion 229.0 seconds. **Serialization is no longer the material runtime bottleneck.** [Stage timings and per-arm measurements](qualification/pdf_packaging/group-measurements.json).

## 4. Native raster inventory and bounded packing control

The optimized synthetic documents retain:

| DPI | Raster B | Native exception objects | Native exception B | Reduced paper B |
|---|---:|---:|---:|---:|
| 300 | 118,980 | 199 | 72,448 | 46,532 |
| 600 | 218,200 | 54 | 167,721 | 50,479 |

The real inventory distinguishes reduced paper, native whole-page fallback and native exceptions. Across the 32 individual-page diagnostics, native whole-page resources cost **69,154,419 B**; 1,671 native exceptions cost **7,073,319 B**. These are single-page diagnostic totals, not the separately reconstructed collection totals.

Of grayscale native samples in the synthetic exceptions, 13.065% / 15.779% are 1–244, 60.699% / 49.682% are 245–254, and 26.236% / 34.540% are 255 at 300 / 600 DPI; none is exactly 0. Full 256-bin histograms and colour-resource status are recorded. Coloured resources are not falsely reclassified as grayscale.

There are **zero pure black/white native objects**, but **nine tiny two-tone detail/fringe objects** in the brochure (lower gray 198–232 plus 255), costing only 147 encoded bytes combined. One 16×8 two-tone patch (221/255) was compared with a painted grayscale stencil mask: payload 17→15 B, but total PDF **857,806→857,996 B**, including the extra paint operations. PDFium was pixel-identical; Poppler changed four pixels (maximum difference 20). This is not a successful source-exact mask promotion or a useful size saving. Thresholding the general multilevel native content would discard tonal information. No general/product mask encoder was added. [Mask control](qualification/pdf_packaging/mask-control/metrics.json).

One actual atlas control packed 17 native resources into one image. It reduced a same-writer page from **54,471 to 54,199 B (272 B)**, but changed 19,721 PDFium / 19,948 Poppler pixels through image sampling (maximum channel differences 76 / 118). Original stored samples alone do not guarantee rendered equality. **Rejected for the product.** The related fallback sampling defect remains. [Inventory](qualification/pdf_packaging/native-inventory.json), [packing control](qualification/pdf_packaging/native-control/metrics.json).

## 5. Verification, review and remaining blockers

101 passing Rust test executions (98 distinct tests; the legacy CLI alias repeats three), with the two known inherited failures explicitly rerun and recorded: `regress_auto_reports_the_selected_candidate` and `clearscan_repairs_a_damaged_glyph_from_same_document_donors`. Five raw-PDF substring checks initially failed when compression hid the syntax; they now use an independent parser to inspect decoded syntax, preserving their behavioral assertions. E0–E7 pass. Inherited P01–P08 visual/native-cardinality failures remain. Test-generated tracked evidence was backed up and restored; unrelated material was preserved.

Independent review found and prompted corrections to encoded-byte accounting, sparse-xref free chains, report/input collisions, pre-OCR limits, report staging and provenance. It also required separating pikepdf/native sizes, matching 600 DPI renders and correctly limiting search claims. Final measured-results review is recorded beside the artifacts.

Specific remaining blockers:

1. **Real OCR/geometry and usable glyph evidence.** Photo receipts and difficult historical types yield few qualified replacements, missing words or narrow border-only OCR. Correct searchable text cannot be recovered by compressing PDF syntax.
2. **Native colour/tonal raster retention.** This dominates the real corpus and much of the 600 DPI synthetic file. Full-resolution lossless retention costs far more than Adobe's reduced/compressed backgrounds or OCRmyPDF's lossy optimization. Preserving an original suitable encoded source image when exact geometry/samples permit is a bounded future ingestion/resource opportunity; it was not silently approximated here.
3. **Font cardinality and conversion cost.** The financial collection still spends 1,024,162 B on embedded font payload versus Adobe's 297,667 B, and hundreds of seconds in page conversion. Canonical assignment and fallback eligibility remain separate existing-product work; no glyph-dictionary redesign or CFF encoder was attempted.
4. **Native extraction/sampling edge cases.** Very narrow invisible owners, table reading order and source-patch sampling remain concrete reproducible failures.

**Delivered:** smaller losslessly serialized PDFs and the ordinary PDF-to-PDF workflow, with actual real-use successes and failures. The real corpus does not support claiming competitive compression or universally reliable OCR. Large artifacts remain in the workspace with hashes/manifests and public source references; only small representative PDFs, images, scripts and evidence are committed. See [artifact/reproduction map](qualification/pdf_packaging/README.md).
'''
(R/'CLEARSCAN_PACKAGING_REPORT.md').write_text(report)
print('report and scorecards written')
