#!/usr/bin/env python3
"""Generate the study report from the measured artifacts."""
import collections, json
from pathlib import Path
import numpy as np
from analyze import HERE, paths
from run import OUT

def read(p): return json.loads(Path(p).read_text())
def mdrow(v): return '| '+' | '.join(map(str,v))+' |\n'
m=read(HERE/'measurements.json');num=read(HERE/'numeric-records.json');func=read(HERE/'functional.json'); panels=read(HERE/'panels-and-owned-check.json');times=read(OUT/'runtime/results.json'); identity=read(HERE/'byte-identity.json')
report=[]
def add(x):report.append(x)
add('# ACR-06 C2: high-DPI ownership measurement')
add('This is a research-only measurement on previously opened inputs. The enumerated corpus has 38 documents (27 P-sheets, nine FONT-01 sheets, financial and mixed); the request also called this 41. No additional holdout was opened. Page and member indices are zero-based. The document-level data, every member of N, and the full pristine records are in the adjacent JSON files.\n')
add('The research switch is read only in q3 ownership preflight. `trace` writes each evaluated assignment’s legacy, corrected, combined result and crop geometry to a separate JSON file; it uses the original combined veto. `corrected-only` uses `corrected.unwrap_or(true)`. The rest of q3, including the 2.0 relative and 0.08 absolute ceilings, final three-distinct-design quorum, structural checks and economy fallback, is unchanged. The variable being unset retains q3 behavior. `run.py` uses the pinned PDFium library, `OMP_THREAD_LIMIT=1`, and `RAYON_NUM_THREADS=4`. The sidecars, logs, and PDFs are in `/data/coding/scanweave/qualification/acr06/local/c2/`.\n')
add('Clean 79b30e5 main and the research build with the switch unset produced the following SHA-256 values (P2″ sheets). Both builds ran with the same environment.\n')
add('| DPI | main | research unset |\n|---|---|---|')
for i,d in [('0',200),('3',300),('6',600)]: add(mdrow([d,identity[i]['main'],identity[i]['research']]).strip())
trace_bad=[r['document'] for r in m['documents'] if not r['q3_vs_trace_pdf_identical']]
add(f"\nTrace PDF comparisons with the saved PR #26 q3 outputs: {len(m['documents'])-len(trace_bad)}/{len(m['documents'])} byte-identical; mismatches: {trace_bad or 'none'}. Both `cargo test -p scanweave-io` runs passed, with and without the pinned PDFium override, and generated evidence was restored.\n")
add('## Ownership contingency\n')
add('Each cell counts preflight assignments, not final substitutions. `false` means the check did not find an exception, `true` means it did, and `none` means invalid geometry; invalid counts as an exception. Legacy-only means legacy is true or invalid while corrected is false. Corrected rejects include true and invalid. Financial is separated because of its non-integer transform.\n')
add('| DPI/category | legacy false, corrected false | legacy false, corrected true | legacy true, corrected false | legacy true, corrected true | other cells including invalid | legacy-only | corrected rejects |\n|---|---:|---:|---:|---:|---|---:|---:|')
for cat,t in m['contingency'].items():
    x=lambda a,b:t.get(a+'/'+b,0)
    other={k:v for k,v in t.items() if 'none' in k}; legacyonly=x('true','false')+x('none','false'); correctedrej=sum(v for k,v in t.items() if k.split('/')[1] in ('true','none'))
    add(mdrow([cat,x('false','false'),x('false','true'),x('true','false'),x('true','true'),json.dumps(other,sort_keys=True),legacyonly,correctedrej]).strip())
add('\n## New substitutions and economy\n')
add('N comprises non-self substitutions accepted by corrected-only but not q3. A legacy-only preflight assignment need not enter N: canonical rejection, final quorum and economy can discard its group. `measurements.json` records every N member, its page, ID, canonical, absolute and relative fit error, final distinct-design witness count, and check outcomes. The preflight does not expose a continuous margin. Font bytes are the sidecar’s encoded font-byte total; PDF bytes are file sizes.\n')
if m['n_members']:
 add(f"The minimum final witness count in N is {min(x['witness_count'] for x in m['n_members'])}; the largest absolute and relative fit errors are {max(x['absolute_error'] for x in m['n_members']):.6f} and {max(x['relative_error'] for x in m['n_members']):.6f}.\n")
add('| Document | DPI | N | off PDF/font bytes | q3 PDF/font bytes | corrected PDF/font bytes | q3 → corrected retired outlines (gross/net) |\n|---|---:|---:|---:|---:|---:|---:|')
for r in m['documents']:
 e=r['economy']; f=lambda a:f"{e[a]['pdf_bytes']}/{e[a]['font_bytes']}"
 add(mdrow([r['document'],r['dpi'],r['n'],f('off'),f('q3'),f('corrected'),f"{e['q3']['retired_outlines']}/{e['q3']['net_outlines_retired']} → {e['corrected']['retired_outlines']}/{e['corrected']['net_outlines_retired']}"]).strip())
add('\n| DPI/category | N | off PDF/font | q3 PDF/font | corrected PDF/font | q3 → corrected retired outlines (gross/net) |\n|---|---:|---:|---:|---:|---:|')
for cat in ('200','300','600','financial-nonint'):
 rows=[r for r in m['documents'] if r['category']==cat]
 def total(arm, key): return sum(r['economy'][arm][key] for r in rows)
 def fmt(arm): return f"{total(arm,'pdf_bytes')}/{total(arm,'font_bytes')}"
 add(mdrow([cat,sum(r['n'] for r in rows),fmt('off'),fmt('q3'),fmt('corrected'),f"{total('q3','retired_outlines')}/{total('q3','net_outlines_retired')} → {total('corrected','retired_outlines')}/{total('corrected','net_outlines_retired')}"]).strip())
add('\n## Pristine fidelity\n')
add('The opened pristine glyph images were composited into each pristine page exactly as in `p2pp_eval.py`; the unchanged PR #26 metric implementation scores every glyph and sheet for both renderers. This is numeric evaluation only. The table gives corrected-only minus q3 and corrected-only minus off in the mean, followed by the corrected-only minus q3 p95, pooled over per-glyph measurements. Per-sheet summaries and every per-glyph record are in the JSON artifacts. Area-bias p95 is the p95 of absolute bias.\n')
add('| DPI | renderer | metric | corrected − q3 mean | corrected − off mean | corrected − q3 p95 |\n|---|---|---|---:|---:|---:|')
for dpi in (200,300,600):
 for engine in ('pdfium','poppler'):
  rr=[r for r in num if r['dpi']==dpi and r['renderer']==engine]
  for metric in ('error','iou','contour_distance','rigid_contour_distance','area_bias'):
   a={arm:np.array([r[arm][metric] for r in rr]) for arm in ('off','q3','corrected')};p=lambda x:np.quantile(np.abs(x) if metric=='area_bias' else x,.95)
   add(mdrow([dpi,engine,metric,f"{np.mean(a['corrected']-a['q3']):.6g}",f"{np.mean(a['corrected']-a['off']):.6g}",f"{p(a['corrected'])-p(a['q3']):.6g}"]).strip())
add('\nLargest individual increases in pristine error at 600 DPI (truth IDs, not OCR symbol IDs; boxes may overlap):\n')
add('| Document | truth ID | renderer | q3 error | corrected error | increase |\n|---|---|---|---:|---:|---:|')
for r in sorted((r for r in num if r['dpi']==600),key=lambda x:x['corrected']['error']-x['q3']['error'],reverse=True)[:10]:
 add(mdrow([r['document'],r['id'],r['renderer'],f"{r['q3']['error']:.6f}",f"{r['corrected']['error']:.6f}",f"{r['corrected']['error']-r['q3']['error']:.6f}"]).strip())
add('\n## Ownership, panels and function\n')
fired=[x for x in panels['checks'] if x['fired']]; add(f"An additional native-resolution render comparison applies the existing owned-component thresholds to source crops and text-only default and corrected crops with each renderer; it removes image and form XObjects before rendering. {len(fired)} of {len(panels['checks'])} renderer/member checks fired. Nearby text can overlap, and the source mask is inferred from grayscale, so this is an approximate independent check, not an exact ownership proof. Flags are in `panels-and-owned-check.json`. Accepted fits also passed the existing hard structural checks.\n")
add(f"For the {panels['member_count_600']} members of N at 600 DPI, the contact sheets contain {panels['panel_rows']} rows (one per renderer/member), sampling: {panels['sampling']}. Each row uses native 600-DPI pixels for source, default, corrected and the canonical at its own accepted placement. Paths and SHA-256 hashes are in `panels-and-owned-check.json`.")
issues=[]
for f in func:
 for arm,c in f['checks'].items():
  if c['qpdf_returncode'] or c['ots_failures'] or not c['font_count']:issues.append((f['document'],arm,'qpdf/OTS/font'))
 for arm,c in f['extraction'].items():
  if not all(c.values()):issues.append((f['document'],arm,'extraction'))
add(f"\nFunctional checks: qpdf, OTS on each embedded font, and PDFium and Poppler extraction versus q3 across off, q3 and corrected-only. Issues: {issues or 'none'}. Exact results are in `functional.json`.")
add('\n## Serial runtime\n')
add('These `/usr/bin/time -v` runs were performed one at a time after the other study processes completed, using the same thread limits and CPU affinity 0,6,10,18,22. At the start the shared host was about 77% idle overall; other user processes were active, so external contention cannot be ruled out. Each arm has one run, with q3 first; caching and run-to-run variation can affect the comparison.\n')
add('| Document | arm | wall seconds | peak RSS KiB |\n|---|---|---:|---:|')
for t in times:add(mdrow([t['document'],t['arm'],f"{t['wall_seconds']:.2f}",t['peak_rss_kb']]).strip())
f=next(x for x in m['documents'] if x['document']=='financial');nset=set(f['n_members']);prior={x['member'] for x in f['prior_removed']};ft=read(str(paths('financial')['trace'])+'.ownership.json'); sx=sorted({x['source_scale_pt'][0] for x in ft});sy=sorted({x['source_scale_pt'][1] for x in ft})
add(f"\n## Financial non-integer transform\n\nThe 1813 px over 435 pt dimension gives 435/1813 = {435/1813:.12g} pt per source pixel; the trace records horizontal scales {sx} and vertical scales {sy} pt per pixel. The horizontal scale {'matches' if all(abs(v-435/1813)<1e-10 for v in sx) else 'does not uniformly match'} 435/1813. Financial has {len(nset)} members in N and {len(prior)} removals in the PR #26 ledger, with {len(nset & prior)} in both, {len(nset-prior)} only in N and {len(prior-nset)} only in the earlier removal list. The complete IDs are retained in `measurements.json`.\n")
add('## Findings requiring review\n')
add('P2′ sheet 6 is an economy anomaly: its encoded font shrank by 157 bytes while its PDF grew by 151 bytes under corrected-only.\n')
add('The largest observed 600-DPI pristine-error increase is on P2 sheet 7: truth glyph `88ebe5e5c67a5c9290f5e5a7` overlaps N member `w000102s0005`; Poppler error rises from 0.085716 to 0.143299. Two other high-increase P2 sheet 7 truth boxes overlap N members `w000001s0004` and `w000044s0001`. The box overlap links are spatial, not a claim of oracle identity. These are concrete fidelity concerns for review, even though the owned-component screen may not flag them.\n')
add(f"Native-render owned-component flags: {[(x['document'], x['page'], x['id'], x['engine'], x['fired']) for x in fired] or 'none'}. Functional issues: {issues or 'none'}. Q3-only accepted members: {[(r['document'],r['q3_only_members']) for r in m['documents'] if r['q3_only_members']] or 'none'}. Changed retained bindings: {[(r['document'],r['changed_bindings']) for r in m['documents'] if r['changed_bindings']] or 'none'}. The approximate independent check has the limitations described above; a clear result is not proof of isolated source ownership. Review the panels and all member records before drawing a stronger conclusion.\n")
r600=[x for x in m['documents'] if x['dpi']==600]; n=sum(x['n'] for x in r600);save=sum(x['economy']['q3']['pdf_bytes']-x['economy']['corrected']['pdf_bytes'] for x in r600)
total=sum(x['economy']['q3']['pdf_bytes'] for x in r600)
add(f"At 600 DPI, corrected-only recovered {n} substitutions and saved {save:,} aggregate PDF bytes against q3, or {100*save/total:.4f}% of the {total:,} q3 bytes. This is a negligible practical PDF-size benefit on this spent corpus. The pooled mean error increases and the larger individual increases are reported above; these measurements do not establish behavior on new data.")
(HERE/'REPORT.md').write_text('\n'.join(report)+'\n')
