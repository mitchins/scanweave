#!/usr/bin/env python3
"""Create a concise Markdown summary from the Phase 2 results."""
import collections,json,math,pathlib,statistics
P=pathlib.Path(__file__).resolve().parent;r=json.loads((P/'results.json').read_text());pages=r['pages'];groups=r['groups'];comps=r['comparisons'];anomalies=r['anomalies'];rows=['sw-E','mrc-M','ocrmypdf-E','adobe-E']; lines=['# BOOKS-01 Phase 2 — development benchmark','',f"36 development pages; {sum(p['rows']['sw-E'].get('status')=='ok' for p in pages.values())} ScanWeave, {sum(p['rows']['mrc-M'].get('status')=='ok' for p in pages.values())} MRC, {sum(p['rows']['ocrmypdf-E'].get('status')=='ok' for p in pages.values())} OCRmyPDF and {sum(p['rows']['adobe-E'].get('status')=='ok' for p in pages.values())} Adobe outputs scored. Six pilot outputs were reused after source and output hash verification; the hOCR text matches after image-path redaction. Adobe uses default unmatched OCR language, no Fraktur support and deskews; GUI wall times include fixed sleeps and are not comparable to CLI times. Its retry recovered both Estor pages; six GUI-automation failures remain. The last four retries failed in about 52 seconds while the root filesystem was full, a possible contributing cause rather than an established cause (evidence: `$B/runs/adobe-p2-retry2/`). FineBooks are processed lossy-origin derivatives. Line pairing is approximate; matched tracks inherit hOCR boxes and cannot independently measure order. Detector counts are automated suspicions, unreviewed.", '', '## Overall', '', '| Row | Pages | Total MB | Median kB | Text SSIM | Text ink recall | Reading CER / WER | Diplomatic CER / WER | Bag recall | Text present | Literal / diplomatic hits | Median conversion s |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
def fmt(v,n=3):return '—' if v is None else f'{v:.{n}f}'
for row in rows:
 x=groups['overall'][row];lines.append(f"| {row} | {x['n']} | {x['bytes_total']/1e6:.2f} | {fmt(x['bytes_median']/1000 if x['bytes_median'] is not None else None,1)} | {fmt(x['aligned_text_ssim_median'])} | {fmt(x['aligned_text_ink_recall_median'])} | {fmt(x['reading_cer_median'])} / {fmt(x['reading_wer_median'])} | {fmt(x['diplomatic_cer_median'])} / {fmt(x['diplomatic_wer_median'])} | {fmt(x['reading_bag_recall_median'])} | {x['nonempty_text']}/{x['n']} | {x['literal_hits']}/{x['recognized_words']} · {x['diplomatic_hits']}/{x['recognized_words']} | {fmt(x['conversion_wall_median'],1)} |")
lines+=['','## Size and aligned fidelity by type and tag','','Tag groups use the frozen selection tags; FineBooks volumes have no such tags and are grouped by volume.','', '| Group | Row | n | Total MB | Median kB | Text SSIM | Text recall | Ill. SSIM / recall / ΔE | Paper SSIM / recall |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for name,x in groups.items():
 if name=='overall':continue
 for row in rows:
  v=x[row];lines.append(f"| {name} | {row} | {v['n']} | {v['bytes_total']/1e6:.2f} | {fmt(v['bytes_median']/1000 if v['bytes_median'] is not None else None,1)} | {fmt(v['aligned_text_ssim_median'])} | {fmt(v['aligned_text_ink_recall_median'])} | {fmt(v['aligned_illustration_ssim_median'])} / {fmt(v['aligned_region_medians']['illustration']['ink_recall'])} / {fmt(v['aligned_region_medians']['illustration']['deltaE2000_mean'])} | {fmt(v['aligned_paper_ssim_median'])} / {fmt(v['aligned_region_medians']['paper']['ink_recall'])} |")
lines+=['','## Size–fidelity comparisons','','A competitor matches when its text SSIM and ink recall are each no more than 0.01 below ScanWeave, and it is smaller. “ScanWeave better” requires both measures above the competitor by more than 0.01; these automated metrics do not establish visual defects.','','| Competitor | Valid comparisons | ScanWeave better | Smaller competitor matches |','|---|---:|---:|---:|']
for row in ['mrc-M','ocrmypdf-E','adobe-E']:
 a=[x for x in comps if x['competitor']==row];lines.append(f"| {row} | {len(a)} | {sum(x['sw_better_both_by_0_01'] for x in a)} | {sum(x['smaller_competitor_matches_both_within_0_01'] for x in a)} |")
for row in ['mrc-M','ocrmypdf-E','adobe-E']:
 for flag,label in [('sw_better_both_by_0_01','ScanWeave better'),('smaller_competitor_matches_both_within_0_01','smaller competitor matches')]:
  a=[x['page'].split('/')[-1] for x in comps if x['competitor']==row and x[flag]];lines.append(f"- {row}, {label}: {', '.join(a) if a else 'none'}.")
lines+=['','## Opportunity examples','','Largest ScanWeave/MRC ratios; background attribution uses the largest non-mask image and DPI assumes page fill. Semantic-owner visible fraction is a vector-word proxy.','','| Page | SW / MRC | SW background kB | SW font kB | MRC background + mask kB | SW visible fraction |','|---|---:|---:|---:|---:|---:|']
ranks=[]
for id,p in pages.items():
 a=p['rows']['sw-E'];b=p['rows']['mrc-M']
 if a.get('status')=='ok' and b.get('status')=='ok':ranks.append((a['size']['file_bytes']/b['size']['file_bytes'],id))
for ratio,id in sorted(ranks,reverse=True)[:10]:
 o=pages[id].get('opportunity',{});lines.append(f"| {id.split('/')[-1]} | {ratio:.2f} | {o.get('sw_background_bytes',0)/1000:.1f} | {o.get('sw_font_program_bytes',0)/1000:.1f} | {o.get('mrc_background_plus_mask_bytes',0)/1000:.1f} | {fmt(o.get('visible_tounicode_fraction'))} |")
lines+=['','## Render latency at 150 DPI','','| Row | PDFium median s | Poppler median s | MuPDF median s |','|---|---:|---:|---:|']
for row in rows:
 values=[]
 for renderer in ['pdfium','poppler','mupdf']:
  a=[p['rows'][row].get('render_150',{}).get(renderer,{}).get('median_seconds') for p in pages.values()];a=[x for x in a if x is not None];values.append(statistics.median(a) if a else None)
 lines.append(f"| {row} | {' | '.join(fmt(x) for x in values)} |")
lines+=['','## Anomalies','','Per-page anomaly details and local example paths are in `results.json`. Crops show the same region across rows; low-text-SSIM cases target a difference, while other cases use page-centre context. A source has no text layer by design; source emptiness is excluded.','','| Page | Anomalies | Local example |','|---|---|---|']
by=collections.defaultdict(list)
for a in anomalies:by[a['page']].append(a)
for id,aa in sorted(by.items()):
 kinds=collections.Counter(x['kind'] for x in aa);lines.append(f"| {id.split('/')[-1]} | {', '.join(k+' ×'+str(v) for k,v in sorted(kinds.items()))} | {aa[0].get('example') or 'unavailable'} |")
lines+=['','All page × row metrics, byte attribution, opportunity inputs, anomaly details and scatter data are in `results.json`; renderer peak RSS and individual timing samples are included per row.',''];(P/'RESULTS.md').write_text('\n'.join(lines))
