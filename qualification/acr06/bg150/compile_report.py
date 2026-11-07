#!/usr/bin/env python3
"""Compile the review report from the frozen evidence and completed runs."""
import hashlib,json,re
from pathlib import Path
q=Path('/data/coding/scanweave/qualification'); e=q/'acr06/bg150'; local=q/'acr06/local/bg150'
groups=['financial','forms','historical','mixed','receipts']; extras=['single','competitive300','competitive600','fresh1','fresh2','freshtruth1','freshtruth2']; docs=groups+extras
def read(path, default=None):
 return json.loads(path.read_text()) if path.exists() else default
def val(x): return '—' if x is None else (f'{x:.4f}' if isinstance(x,float) else str(x))
def words(a): return ', '.join('`'+str(w)+'`' for w in a) if a else 'none'
def size(path): return path.stat().st_size if path.exists() else None
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'MISSING'
def section_rows(row):
 v=row['visual']; bg=row.get('background_ocr'); o=row['complete_ocr']; b=row.get('backgrounds')
 return f"| {row['page']} | {o['source_words']} | {o['default_recalled']}→{o['candidate_recalled']} | {str(bg['default_recalled'])+'→'+str(bg['candidate_recalled']) if bg else '—'} | {str(b[0]['bytes'])+'→'+str(b[1]['bytes']) if b else '—'} | {v['small_components_2_to_20px']} | {val(v['small_survival_default'])}→{val(v['small_survival_candidate'])} | {val(v['line_continuity_default'])}→{val(v['line_continuity_candidate'])} | {val(v['ssim_default'])}→{val(v['ssim_candidate'])} |"
def word_rows(row):
 o=row['complete_ocr']; b=row.get('background_ocr'); s=[f"Page {row['page']} complete: lost {words(o['lost_source_words'])}; gained {words(o['gained_source_words'])}."]
 s.append(f"Page {row['page']} complete, all OCR tokens: lost {words(o['all_lost_words'])}; gained {words(o['all_gained_words'])}.")
 if b:
  s.append(f"Page {row['page']} background: lost {words(b['lost_source_words'])}; gained {words(b['gained_source_words'])}.")
  s.append(f"Page {row['page']} background, all OCR tokens: lost {words(b['all_lost_words'])}; gained {words(b['all_gained_words'])}.")
 return s
lines=['# ACR-06: guarded 150-DPI background experiment','',
'## Recommendation and scope','','**Recommendation: revise; do not open a PR.** This guard has not demonstrated a meaningful corpus saving: the observed totals are below. We did not find a guard in this experiment that both meets the page-level preservation bar and achieves a meaningful saving; this does not prove no such guard exists. Source-pixel thresholds are conservative engineering choices, not a proof of visual fidelity. Layout cost estimates remain at the existing 200-DPI setting. Auto mode and glyph sharing bypass the experiment to preserve their size-based decisions. Faithful, protected, raster-baseline, native-exception and source-JPEG paths remain on their existing representations. The document first makes the original lossless-versus-compact choice, and only then considers a smaller experimental compact PDF.','','## Frozen protocol','','The development split and predeclared material-regression thresholds are in [protocol.md](protocol.md). The source-pixel guard requires a maximum channel error of five levels over the full image after a 150-DPI JPEG round trip, and mean error of at most one level on horizontal source edge pairs two pixels apart and at least 20 levels apart. It requires an existing reduced representation and a smaller 150-DPI image. Every failure returns the existing image. The guard was frozen after development pages and before held-out or fresh result review. These limits are deliberately strict because the development measurements showed that counting only errors of 20 or more levels misses a material OCR loss.','','The fresh generator is [fresh.py](fresh.py), seed 609150, with generator, font, truth and input hashes in [fresh-sha256.txt](fresh-sha256.txt). It uses DejaVu Serif (Bitstream Vera license; DejaVu changes public domain, `/usr/share/doc/fonts-dejavu-core/copyright`). No permissively licensed blackletter font was identified. The generator includes aged paper, 6–8 pt text, punctuation and decimal points, faint/broken print, tables, halftone and synthetic tonal artwork, at 300 DPI and a non-integer page scale. Source PNGs are the pristine raster truth; it is not photographic ground truth.','','## Main release baseline','','Built from `36ad4eaf4eee8084335ea5f4be3ecc2a4ab6fc2e` with `cargo build --release --locked`, `--dpi 300 --profile clearscan --glyph-sharing off`. Hashes are from the actual new main outputs; the reviewer can compare them with the post-#34 reference.','','| Document | SHA-256 |','|---|---|']
for g in groups: lines.append(f'| {g} | `{sha(local/"baseline"/(g+".pdf"))}` |')
lines+=['','Product branch `exp/acr06-bg150` is committed and pushed at `5c037d62c43c528f1a4a9af08ab8ccc4f5b77188`. No pull request was opened.']
lines+=['','## Phase 1: unguarded 150-DPI product output','','All page numbers below are one-based. The historical CP3 identifier `historical-p4` is page 5. Entries are source matched words; the source render is Tesseract English PSM 3 and counts are multisets. A dash means no qualifying whole-page DCT background was identified. Small-component survival uses source dark connected components of 2–20 pixels and a 30-level local contrast threshold. The line proxy uses 12-pixel morphological openings, and includes some text strokes. The SSIM is whole page at quarter scale; manually selected artwork crops are in `phase1-artwork-*.json`. These are proxies rather than semantic punctuation, true line classification, or a visual inspection. The PDFium and Poppler 300-DPI output render comparisons are in `phase1-render-*.json`; the source render check is in `source-renders.json`. The unguarded research build made its own complete-PDF lossless-versus-compact decision: on forms it switched the default lossless whole page to 150-DPI JPEG. Those pages are not existing reduced backgrounds and are excluded from guard calibration. The guarded implementation first preserves the default document-level choice, so this forms switch cannot occur there.','','| Page | Source words | Complete default→150 | Background default→150 | Background image bytes default→150 | Small components | Survival default→150 | Rule continuity default→150 | Source SSIM default→150 |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
phase={}
for g in groups:
 files=([e/'phase1-dev-financial.json',e/'phase1-heldout-financial.json'] if g=='financial' else [e/('phase1-dev-historical.json' if g=='historical' else f'phase1-heldout-{g}.json')])
 rows=[]
 for f in files: rows.extend((read(f,{}) or {}).get('pages',[]))
 phase[g]=sorted(rows,key=lambda x:x['page']); lines.append(f'| **{g}** | | | | | | | | |')
 lines.extend(section_rows(r) for r in phase[g])
lines+=['','### Phase 1 lost and gained words','','These lists are source-matched multiset differences; additional raw-token changes, image dimensions and raw values are retained in the corresponding `phase1-*.json` files.']
flagged=[]
for g,rows in phase.items():
 for row in rows:
  reasons=[]
  for key in ('complete_ocr','background_ocr'):
   if key in row:
    before=row[key]['default_recalled']; after=row[key]['candidate_recalled']; loss=before-after
    if loss>=5 or (before>=10 and loss/before>=.10): reasons.append(key)
  v=row['visual']
  for before,after,label in [('small_survival_default','small_survival_candidate','small components'),('line_continuity_default','line_continuity_candidate','rules')]:
   if v[before] is not None and v[after] is not None and v[before]-v[after]>.05: reasons.append(label)
  if reasons: flagged.append(f"{g} p{row['page']} ({', '.join(reasons)})")
lines+=['','**Predeclared unguarded flags:** '+('; '.join(flagged) if flagged else 'none')+'. Forms flags arise from the ineligible lossless-to-JPEG research artifact described above.','']
for g in groups:
 lines+=['',f'**{g}**','']
 for r in phase[g]: lines+=word_rows(r)+['']
detail=read(e/'historical-detail.json',{})
lines+=['## Historical page 5 / CP3 p4','','The archived CP3 offline re-encoding reproduces 114→88 recalled words, with 37 lost and 11 gained source-matched tokens; [cp3_page4.json](cp3_page4.json) lists every token. That result re-encodes an already compressed background and is not the product experiment. In the actual product comparison the complete page falls from 128 to 101 source-matched tokens, and the background alone from 121 to 103. Examples of lost background tokens include `princeps`, `legere`, and `ingenui`; all lost and gained tokens are listed above. The new main baseline and the direct source-residual encoding differ from the older CP3 input and its double-JPEG simulation.','',f"At 300-DPI render scale, the source thresholded-component median height was {val(detail.get('source',{}).get('median_component_height_300px'))} pixels and the estimated median skeleton stroke width {val(detail.get('source',{}).get('median_skeleton_stroke_width_300px'))} pixels; the latter corresponds to about {val((detail.get('source',{}).get('median_skeleton_stroke_width_300px') or 0)/2)} pixels at 150 DPI. Tesseract's boxes labeled as lower-case x-height letters have source median {val(detail.get('source',{}).get('ocr_lowercase_xheight_proxy_300px',{}).get('median'))} pixels at 300 DPI, about {val((detail.get('source',{}).get('ocr_lowercase_xheight_proxy_300px',{}).get('median') or 0)/2)} pixels at 150 DPI; blackletter misrecognition may bias this estimate. The component and skeleton measures are whole-page proxies. Mean dark contrast in the actual backgrounds changed from {val(detail.get('default_background',{}).get('mean_dark_contrast'))} to {val(detail.get('150_background',{}).get('mean_dark_contrast'))} levels, and mean absolute source error near dark ink changed from {val(detail.get('default_background',{}).get('near_source_ink_mean_abs_error_vs_source'))} to {val(detail.get('150_background',{}).get('near_source_ink_mean_abs_error_vs_source'))}. Resampling and JPEG recompression plausibly soften fine strokes and introduce local ringing; the near-ink statistic also contains registration and resampling error and does not isolate ringing. Tesseract's English OCR on this blackletter is unstable, so the changed tokens are evidence of risk rather than a ground-truth transcription. Full physical proxies are in [historical-detail.json](historical-detail.json).",'', '## Guarded qualification','','| Page | Source words | Complete default→candidate | Background default→candidate | Background image bytes default→candidate | Small components | Survival default→candidate | Rule continuity default→candidate | Source SSIM default→candidate |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
quality={}
for name in docs:
 quality[name]=(read(e/f'quality-{name}.json',{}) or {}).get('pages',[]); lines.append(f'| **{name}** | | | | | | | | |'); lines.extend(section_rows(x) for x in quality[name])
lines+=['','### Guard decisions and source-matched word changes','','A guard log entry is the per-page decision before complete-PDF size selection. A document decision of `default` means the final PDF retained the default representation even if a preliminary page entry says 150. Missing page entries mean the experimental encoder was not invoked for that page; inspect the image and document logs rather than assuming a particular eligibility reason. The final release logs are under `local/bg150/release-verify/`.']
for name in docs:
 log=(local/'release-verify'/f'{name}.log'); text=log.read_text() if log.exists() else ''
 decisions=[s for s in text.splitlines() if 'background150' in s]
 lines+=['',f'**{name}**','',*['- `'+s.replace('`','')+'`' for s in decisions], '']
 for r in quality[name]: lines+=word_rows(r)+['']
lines+=['## PDF bytes and preservation','','| Document | Main default | Guarded | Adobe XI | Archive MRC | Saving |','|---|---:|---:|---:|---:|---:|']
total=[0,0,0,0]
for name in docs:
 paths=[local/'baseline'/f'{name}.pdf',local/'candidate'/f'{name}.pdf',q/f'pdf_packaging/groups/{name}-adobe.pdf',q/f'pdf_packaging/groups/{name}-archive.pdf']; vals=[size(p) for p in paths]
 if name in groups:
  total=[a+(b or 0) for a,b in zip(total,vals)]
 lines.append(f"| {name} | {val(vals[0])} | {val(vals[1])} | {val(vals[2])} | {val(vals[3])} | {val(vals[0]-vals[1] if vals[0] is not None and vals[1] is not None else None)} |")
lines.append(f'| **Group total** | {total[0]} | {total[1]} | {total[2]} | {total[3]} | {total[0]-total[1]} |')
lines+=['','### Unguarded complete-PDF sizes','','| Document | Default | Unguarded 150 | Difference |','|---|---:|---:|---:|']
for name in groups:
 d=size(local/'baseline'/f'{name}.pdf'); c=size(local/'unguarded'/f'{name}.pdf')
 lines.append(f'| {name} | {val(d)} | {val(c)} | {val(d-c if d is not None and c is not None else None)} |')
lines+=['','Adobe and Archive are reference outputs only. Page image streams and per-page sizes are recorded in `preservation-*.json`; the full stream classification is in `bytes.json`. PDFium and Poppler 300-DPI renderer diff statistics, raw font and content stream hashes, named image hashes, and text extraction equality are in the same preservation JSON. A whole-page rendered diff is attributed to a changed background only where all other streams match; compositing edges are included.','','| Document | Font streams | Content streams | PDFium text | Poppler text | Changed image paths | qpdf | Repeat byte-identical |','|---|---|---|---|---|---:|---|---|']
det={}
if (local/'determinism.txt').exists(): det=dict(line.split() for line in (local/'determinism.txt').read_text().splitlines())
checks={}
if (local/'qualification/qpdf-status.txt').exists(): checks=dict(line.split() for line in (local/'qualification/qpdf-status.txt').read_text().splitlines())
for name in docs:
 p=read(e/f'preservation-{name}.json',{}) or {}; rows=p.get('pages',[])
 def allfield(k): return 'yes' if rows and all(r[k] for r in rows) else 'NO / missing'
 changed=sum(len(r['changed_image_paths']) for r in rows)
 lines.append(f"| {name} | {allfield('font_streams_equal')} | {allfield('content_streams_equal')} | {allfield('pdfium_text_equal')} | {allfield('poppler_text_equal')} | {changed} | {'pass' if checks.get(name)=='0' else 'MISSING / FAIL'} | {'yes' if det.get(name)=='0' else 'MISSING / FAIL'} |")
lines+=['','### Page decisions, images and renderer differences','','Image bytes are the sum of reachable named image streams on the page, without amortizing shared images. Renderer differences are maximum-channel absolute differences over the complete page at 300 DPI; a zero value means no rendered pixels changed.','', '| Document | Page | Final changed images | Decision record | Image bytes default→candidate | PDFium changed / mean / max | Poppler changed / mean / max |','|---|---:|---:|---|---:|---|---|']
for name in docs:
 p=read(e/f'preservation-{name}.json',{}) or {}; rows=p.get('pages',[])
 log=local/'release-verify'/f'{name}.log'; text=log.read_text() if log.exists() else ''
 for r in rows:
  page=r['page']; match=re.search(rf'background150 page={page} decision=(\S+)',text)
  decision=match.group(1) if match else 'not evaluated'
  if not r['changed_image_paths']: decision+='; final default'
  a=sum(x['bytes'] for x in r['images_default'].values()); b=sum(x['bytes'] for x in r['images_candidate'].values())
  def rd(key):
   d=r[key]; return f"{d.get('changed_pixels','size mismatch')} / {val(d.get('mean_max_channel_abs'))} / {val(d.get('max_abs'))}"
  lines.append(f"| {name} | {page} | {len(r['changed_image_paths'])} | {decision} | {a}→{b} | {rd('pdfium_render_diff')} | {rd('poppler_render_diff')} |")
lines+=['','Individual page review sheets and comparator references for every changed page are indexed under `local/bg150/panels/`; each index contains crop coordinates and SHA-256 hashes. Empty indices indicate no changed image stream. No independent visual review by Claude is claimed.','','## Validation','','The workspace Rust tests, denied-warning clippy, and Python CI logs/statuses are under `local/bg150/checks/`. The isolated Python runner uses the existing CPU-only torch installation at `/tmp/scanweave-donorfix-torch` and OTS 9.3.0. qpdf 12.4.2 requires `LD_LIBRARY_PATH=/data/coding/scanweave/tools/dist/lib`; the first checks without it failed to start (exit 127), and the fixed checks are recorded separately.','','## Limits and judgment','','OCR is a noisy proxy, especially for historical blackletter. Small components include noise; line openings include text and the artwork crops are manually selected. No binary claim about punctuation preservation follows from the proxy alone. Thresholds were tuned conservatively on a small, non-random development split, and the fresh pages share one generator. The frozen guard may reject many safe pages; the results do not establish that no less conservative guard could work. A smooth synthetic assembly unit test exercises acceptance, but the qualification PDFs do not provide a positive changed-page example when all guarded outputs fall back, so unchanged non-background streams in a changed full document remain unproven by this corpus. Default-to-candidate identity, where observed, directly limits the output risk for those inputs but does not prove safety on unseen inputs.']
lines+=['','## Review sheet index hashes','','| Document | Changed-page sheets | Index SHA-256 |','|---|---:|---|']
for name in docs:
 idx=local/'panels'/f'{name}-index.json'; entries=read(idx,[]) or []
 lines.append(f'| {name} | {len(entries)} | `{sha(idx)}` |')
 for entry in entries:
  lines.append(f"| {name} p{entry['page']} | `{entry['panel']}` | `{entry['sha256']}` |")
  if 'references' in entry: lines.append(f"| {name} p{entry['page']} references | `{entry['references']}` | `{entry['references_sha256']}` |")
lines+=['','## Additional checks and decisions','','| Check | Result |','|---|---|']
for label,path in [('workspace tests','checks/cargo-test-release.status'),('clippy','checks/clippy-release.status'),('focused assembly','checks/assembly-test.status'),('CLI invalid values','checks/cli-test.status'),('protected and auto mode','checks/auto-protection-final.status'),('Python runner','checks/python-release-driver.status')]:
 p=local/path; lines.append(f'| {label} | {p.read_text().strip() if p.exists() else "MISSING"} (0 is success) |')
faith=local/'faithful/status.txt'; lines.append(f"| faithful default vs flag | `{faith.read_text().strip().replace(chr(10), '; ') if faith.exists() else 'MISSING'}` |")
default=local/'release-default/identity.txt'; lines.append(f"| main vs final product default | `{default.read_text().strip().replace(chr(10), '; ') if default.exists() else 'MISSING'}` |")
policies=read(e/'default-policies.json',{}) or {}; lines.append(f"| default serialized policies | {'all equal' if len(policies)==5 and all(x['equal'] for x in policies.values()) else 'MISSING / FAIL'}; see `default-policies.json` |")
audit=local/'release-verify/status.txt'; lines.append(f"| final release vs measured candidate | `{audit.read_text().strip().replace(chr(10), '; ') if audit.exists() else 'MISSING'}` |")
cross=read(e/'audit.json',{}) or {}; lines.append(f"| Cross-check | {len(cross.get('documents',{}))} documents, {sum(x.get('pages',0) for x in cross.get('documents',{}).values())} pages; failures: {cross.get('failures','MISSING')}; see `audit.json` |")
python_rows=read(local/'checks/python-results.json',[]) or []
lines.append(f"| Python gate failures | {', '.join(x['gate'] for x in python_rows if x['returncode']) or ('none' if len(python_rows)==20 else 'results incomplete')} ({len(python_rows)} recorded) |")
lines+=['','The source-residual instrumentation and unguarded product build can be reproduced with `build_unguarded.sh` and `unguarded.patch`. After fresh results, auto-mode containment was added to the single-image API, page-skip logging was expanded, and the false option was omitted from serialized default policy; none of those changes modified the guard. The final release outputs are compared byte for byte with the measured candidates above.','',f'The remaining group saving is **{total[0]-total[1]} bytes** across {total[0]} default bytes. Historical pages 3 and 5 have material unguarded OCR regressions, and all twelve development pages have a small-component proxy decline above the predeclared threshold. These pages remain of particular concern for any future, less conservative guard.']
lines+=['','## Independent pristine-truth fresh set','','A second fresh generator, [fresh_truth.py](fresh_truth.py), seed 609151, was frozen before running these inputs; [fresh-truth-sha256.txt](fresh-truth-sha256.txt) records the generator, font, clean PNGs, damaged source PNGs and PDFs. Clean 6–8 pt text, punctuation, lines and artwork are saved independently of the simulated faint and broken source ink. The manifest contains intended text and pixel boxes. No guard change was made after reviewing the first fresh set. The following table compares each arm with that pristine truth; the component test is a threshold proxy, and OCR uses the manifest text multiset.','','| Page | Arm | Truth words | Recalled | Small components | Small-component survival | Rule continuity | Artwork SSIM |','|---|---|---:|---:|---:|---:|---:|---:|']
fresh=read(e/'fresh-truth-quality.json',{}) or {}
for name,rows in fresh.items():
 for r in rows: lines.append(f"| {name} | {r['arm']} | {r['truth_words']} | {r['recalled_truth_words']} | {r['small_truth_components']} | {val(r['small_truth_component_survival'])} | {val(r['truth_line_pixel_continuity'])} | {val(r['artwork_ssim'])} |")
for name,rows in fresh.items():
 lines+=['',f'**{name}: pristine-truth OCR differences**','']
 for r in rows: lines.append(f"{r['arm']}: truth tokens not recalled: {words(r['truth_words_not_recalled'])}; unmatched OCR tokens: {words(r['unmatched_ocr_tokens'])}.")
lines+=['','## Artwork and photographic crops','','Coordinates are normalized to the source page; these manually chosen crops are not an exhaustive artwork detector. Values compare each rendered arm with the source.','','| Document | Page | Region | Crop | Default SSIM | Candidate SSIM |','|---|---:|---|---|---:|---:|']
for name in ['historical','mixed','receipts','fresh1','fresh2']:
 for prefix,label in [('artwork','guarded'),('phase1-artwork','unguarded')]:
  for r in read(e/f'{prefix}-{name}.json',[]) or []:
   lines.append(f"| {name} ({label}) | {r['page']} | {r['region']} | `{r['relative_box']}` | {val(r['ssim_default'])} | {val(r['ssim_candidate'])} |")
lines+=['','## Phase 1 renderer differences','','The PDFium and Poppler figures below cover the whole page at 300 DPI; raw stream comparisons in the JSON identify changed image resources. The forms lossless-to-JPEG artifact is described above.','','| Document | Page | Changed image streams | PDFium pixels / mean / max | Poppler pixels / mean / max |','|---|---:|---:|---|---|']
for name in groups:
 for r in (read(e/f'phase1-render-{name}.json',{}) or {}).get('pages',[]):
  def render_diff(key):
   d=r[key]; return f"{d.get('changed_pixels','size mismatch')} / {val(d.get('mean_max_channel_abs'))} / {val(d.get('max_abs'))}"
  lines.append(f"| {name} | {r['page']} | {len(r['changed_image_paths'])} | {render_diff('pdfium_render_diff')} | {render_diff('poppler_render_diff')} |")
lines+=['','## One- and two-pixel line proxy','','At 300 DPI, source dark pixels in a horizontal or vertical opening at least 12 pixels long are retained only where the perpendicular five-pixel neighborhood contains at most two dark pixels. Continuity is the fraction retaining at least 20 levels of contrast against the source local-paper estimate. Text strokes and scan noise can meet this geometric rule. Unguarded values apply only to group documents.','','| Document | Page | Source line pixels | Source contrast / continuity | Default contrast / continuity | Guarded contrast / continuity | Unguarded contrast / continuity |','|---|---:|---:|---|---|---|---|']
for name,rows in (read(e/'thin-rules.json',{}) or {}).items():
 for r in rows:
  def arm(a):
   x=r['arms'].get(a,{}); return f"{val(x.get('mean_contrast'))} / {val(x.get('continuity_20_levels'))}"
  lines.append(f"| {name} | {r['page']} | {r['source_line_pixels']} | {arm('source')} | {arm('default')} | {arm('candidate')} | {arm('unguarded')} |")
(e/'REPORT.md').write_text('\n'.join(lines)+'\n')
