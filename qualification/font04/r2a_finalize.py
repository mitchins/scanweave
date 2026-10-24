"""Close R2a evidence after all explicit development-only qualifications pass."""
import json
from pathlib import Path
import subprocess

from qualification.font04.metrics import sha
from qualification.font04.r2a_metrics import summaries

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'qualification/font04'
LOCAL = BASE/'local/R2a'
GROUPS = ('forms','receipts','mixed','historical','financial')


def load(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def runs(directory):
    result = {}
    for group in GROUPS if directory.name != 'resume-reporting' else ('financial',):
        labels = ['off','cover-2.0']
        if directory.name == 'resume-optimized': labels.append('cover-2.0-repeat')
        if group == 'financial' and directory.name != 'paired-final': labels.insert(2,'cover-1.5')
        result[group] = {}
        for label in labels:
            stem = directory/f'{group}-{label}.pdf'
            row = load(stem.with_suffix('.run.json'))
            assert row['returncode'] == 0 and row['byte_identical_to_baseline']
            assert row['sha256'] == sha(stem.with_suffix('.pdf')) == row['expected_sha256']
            timing = stem.with_suffix('.time').read_text()
            row['peak_rss_kib'] = int(next(line.split(':',1)[1] for line in timing.splitlines() if 'Maximum resident set size (kbytes)' in line))
            result[group][label] = row
    return result


def main():
    optimized = runs(LOCAL/'resume-optimized')
    reporting = runs(LOCAL/'resume-reporting')
    paired = runs(LOCAL/'paired-final')
    blind = load(BASE/'r2a-blind-review.json')
    assert blind['key_revealed'] is False
    public = Path(blind['review_pdf']).parent
    assert sha(Path(blind['review_pdf'])) == blind['receipt']['review_sha256']
    assert sha(public/'README.md') == blind['receipt']['readme_sha256']
    rule = (ROOT/'FONT_04_REVIEW_R2A_STOP.md').read_text().split('4. **Decision rule, fixed now, before grading.**',1)[1].rstrip()
    assert '4. **Decision rule, fixed now, before grading.**'+rule in (public/'README.md').read_text()
    save = load(BASE/'r2a-save-controls.json')
    corpus = load(BASE/'r2a-partial-corpus.json')
    aggregates = {'metrics': ([],[]), 'context-metrics': ([],[])}
    for group, row in corpus['documents'].items():
        for kind in ('metrics','context-metrics'):
            path = LOCAL/f'{kind}/{group}/metrics.json'
            full = load(path)
            assert full['default_sha256'] == row['default_pdf_sha256']
            assert full['candidate_sha256'] == row['sharing_pdf_sha256']
            row[kind] = {k:v for k,v in full.items() if k not in ('records','floors')}
            row[kind]['full_records_path'] = str(path.relative_to(ROOT))
            row[kind]['full_records_sha256'] = sha(path)
            for key, dest in zip(('records','floors'), aggregates[kind]):
                dest.extend(dict(r, draw=f"{group}:{r['draw']}") for r in full[key])
        row['metrics_status'] = 'complete: contextual every visible draw; isolated available owned-source witnesses with explicit unavailable counts'
        row['final_optimized_qualification'] = 'PASS: output byte-identical before/after optimization and final paired runs'
        row['save_only_comparison'] = save['documents'][group]
        row['runtime'] = paired[group]
        assert paired[group]['off']['sha256'] == row['default_pdf_sha256']
        assert paired[group]['cover-2.0']['sha256'] == row['sharing_pdf_sha256']
    corpus.update(schema='font04-R2a-corpus-evidence-v2', status='EVIDENCE COMPLETE; blind materiality decision pending',
                  metrics_financial_not_run=False,save_only_controls_not_run=False,
                  final_optimized_build_not_qualified=False,blind_package_not_sealed=False)
    corpus['totals']['fidelity'] = {kind:summaries(*data) for kind,data in aggregates.items()}
    corpus['totals']['save_only'] = save['totals']
    corpus['totals']['runtime'] = {mode:dict(wall_seconds=sum(r[mode]['wall_seconds'] for r in paired.values()),
        peak_rss_kib=max(r[mode]['peak_rss_kib'] for r in paired.values())) for mode in ('off','cover-2.0')}
    dump(BASE/'r2a-corpus.json',corpus)
    profile = dict(schema='font04-R2a-profile-v2',
        reporting=reporting, byte_verification=optimized, paired_final=paired,
        optimization='Independent row workers; unchanged numerical evaluation order within each row; ordered joins before reductions',
        profiling_limit='Reporting and byte-qualification runs overlapped other qualification jobs; final paired runs are serial with no other FONT-04 jobs.',
        rss_definition='GNU time -v Maximum resident set size in KiB; maximum for a run, not a sum across documents or processes',
        stage_definition='stage_timings are pipeline milliseconds; sharing_stage_seconds are seconds. planning_* are nested within planning, and sharing stages within sharing_total; do not sum nested timings.',
        all_outputs_byte_identical=True)
    dump(BASE/'r2a-profile.json',profile)
    checkpoint = load(BASE/'checkpoint-R2a.json')
    checkpoint.update(status='STOP AT CHECKPOINT R2a: evidence complete; independent sealed blind review required',
        checkpoint_R2a_reached=True,qualification_complete=True,reviewer_pending=True,
        product_commit=subprocess.check_output(['git','rev-parse','feat/glyph-sharing'],cwd=ROOT,text=True).strip(),
        incomplete_due_to_stop=[],next_action='STOP for independent blind review under dc0849b. Materiality is unknown until grading. No P2, Reader workaround, product PR or merge.')
    checkpoint['completed'].update(financial_golden_reruns=True,financial_all_draw_fidelity=True,
        save_only_controls=True,final_paired_runtime_RSS=True,repeat_hashes=True,
        fidelity_complete_documents=list(GROUPS),all_outputs_byte_identical=True)
    checkpoint['optimization'].update(qualified=True,reverted=False,shipped=True,output_changes_observed=False,
        completed_byte_comparisons=[f'{g} {mode}' for g, modes in optimized.items() for mode in modes],
        description=profile['optimization'])
    checkpoint['blind_review'] = blind
    checkpoint['materiality'] = dict(status='UNKNOWN: independent blind grading pending',materially_worse_rate=None,
        decision_rule='4. **Decision rule, fixed now, before grading.**'+rule)
    artifacts = ['r2a-baseline.json','r2a-partial-corpus.json','r2a-corpus.json','r2a-profile.json',
        'r2a-save-controls.json','r2a-blind-review.json','r2a-binding-evidence.json','R2A_BLIND_README.md']
    checkpoint['artifacts'] = [dict(path=str((BASE/name).relative_to(ROOT)),sha256=sha(BASE/name)) for name in artifacts]
    dump(BASE/'checkpoint-R2a.json',checkpoint)
    write_results(corpus,checkpoint)


def write_results(corpus,checkpoint):
    target = ROOT/'FONT_04_RESULTS.md'
    original = target.read_text()
    prefix = original.split('## Checkpoint R2a',1)[0]
    lines = ['## Checkpoint R2a','',
        '**STOP for independent sealed blind review. Evidence gathering is complete; materiality remains unknown.**',
        'The stop decision `dc0849b` and R1 acceptance `fa8a08b` were verified and read. The method stayed frozen: no threshold, floor, scale-bound, guard or membership changes; member 518 was not fixed.', '',
        f"Product `{checkpoint['product_commit']}` on `feat/glyph-sharing` adds ordered planner-row workers with serial numerical evaluation inside each row and ordered joins. Reporting-build financial default, cover-2.0 and cover-1.5 reruns reproduce `74c31136…`, `b007a27d…` and `dbdf30d3…`. Every corpus output, both financial sharing arms, final paired runs and repeats are byte-identical to their baselines. Five native unit tests and six integration tests pass, including the 23 regression cases. The changed Rust file passes rustfmt; the full workspace check reports pre-existing formatting differences outside this change.", '',
        'All runs use pinned PDFium chromium/8100, SHA-256 `b8784cbd652ad2993332b7695e2c80f3a797f877fc47d9be97b66bca9639539e`. Its canonical loaded path and SHA-256 are reported; the runtime exposes no version query.', '',
        '| Document | Font B default → sharing | Retired / added / net | PDF B default → sharing | Saving vs save-only B |',
        '|---|---:|---:|---:|---:|']
    for group,row in corpus['documents'].items():
        a=row['actual_design_accounting']
        lines.append(f"| {group.title()} | {row['default_font_bytes']:,} → {row['sharing_font_bytes']:,} | {a['retired_outlines']} / {a['added_canonicals']} / {a['net_outlines_retired']} | {row['default_pdf_bytes']:,} → {row['sharing_pdf_bytes']:,} | {row['save_only_comparison']['sharing_saving_vs_save_only']:,} |")
    t=corpus['totals']
    lines += [f"| Total | {t['default_font_bytes']:,} → {t['sharing_font_bytes']:,} | {t['retired_outlines']} / {t['added_canonicals']} / {t['net_outlines_retired']} | {t['default_pdf_bytes']:,} → {t['sharing_pdf_bytes']:,} | {t['save_only']['sharing_saving_vs_save_only']:,} |",'',
        'Forms correctly emits default: the attempted font would grow 41,147 → 46,879 B with net retirement −8. Receipts and historical have no surviving groups. Mixed has 5 zero-credit groups (1,798 B outlines + 234 B stubs); financial has 54 (24,086 + 3,268 B). These are reported separately and receive no invented retirement credit.', '',
        'All five documents pass Poppler default/layout/raw, PDFium and MuPDF extraction equality, qpdf, OTS, raster-stream/placement and text-geometry checks. Exact final PDF hashes carry those checks forward. Save-only controls independently pass the same transport checks. All 5,630 visible draws have contextual analytic/PDFium/Poppler scores; isolated owned-source scores report unavailable witnesses explicitly. Per-document and aggregate all/substituted means, p95, worst ten and floors are in [r2a-corpus.json](qualification/font04/r2a-corpus.json); full records remain in ignored local artifacts.', '',
        'Financial isolated scoring required an evidence-harness correction: a visible-only first-shape reconstruction missed earlier invisible font-union programs. A research-only native occurrence/CID/matrix export binds every draw bijectively, with exact default-PDF and source-snapshot hash checks. No product output or metric formula changed.', '',
        '| Document | Default s / peak MiB | Sharing s / peak MiB | Sharing/default wall |',
        '|---|---:|---:|---:|']
    for group,row in corpus['documents'].items():
        a,b=row['runtime']['off'],row['runtime']['cover-2.0']
        lines.append(f"| {group.title()} | {a['wall_seconds']:.2f} / {a['peak_rss_kib']/1024:.1f} | {b['wall_seconds']:.2f} / {b['peak_rss_kib']/1024:.1f} | {b['wall_seconds']/a['wall_seconds']:.3f}× |")
    a,b=t['runtime']['off'],t['runtime']['cover-2.0']
    lines += [f"| Total / max peak | {a['wall_seconds']:.2f} / {a['peak_rss_kib']/1024:.1f} | {b['wall_seconds']:.2f} / {b['peak_rss_kib']/1024:.1f} | {b['wall_seconds']/a['wall_seconds']:.3f}× |",'',
        'Final paired runs were serial after other FONT-04 qualification jobs finished. Peak is GNU time maximum RSS, not a process-tree sum. Pipeline milliseconds and nested sharing/planner seconds, reporting-build profiles, optimization byte checks and repeats are retained in [r2a-profile.json](qualification/font04/r2a-profile.json). Earlier overlapping qualification timings are not claimed as isolated benchmarks.', '']
    blind=checkpoint['blind_review']
    lines += [f"The sealed package contains **{blind['receipt']['panels']} panels**, ≥300 random accepted and ≥150 random rejected members stratified by document, repeated words, cross-style probes, all registered regression cases, and member 518. All 326 mixed substitutions are included, including all **{blind['mixed_tail']}** mixed isolated-error tail draws, matched to **{blind['matched_financial_tail']}** financial tail draws using the same >0.02 error definition across analytic, direct-outline, PDFium and Poppler. Full-word contexts use randomized A/B/C source/current/candidate arms in both renderers at 100% and 400%. The key is held separately and has not been read. The review decision rule was copied verbatim into the README before sealing.", '',
        f"Review: `{blind['review_pdf']}`. [Seal receipt and selection](qualification/font04/r2a-blind-review.json); [checkpoint and artifact hashes](qualification/font04/checkpoint-R2a.json). The earlier member-518 diagnostics remain in [r2a-stop-evidence](qualification/font04/r2a-stop-evidence/README.md); the review upheld that defect and deferred its materiality to blind grading.", '',
        '**STOP.** P2 was not opened, generated or rendered. Adobe Reader remains **BLOCKED-ON-OWNER**. Neither `~/.wine-acrobat-xi` nor display `:99` was touched. No product PR, merge, or PR #24/#25 action.']
    target.write_text(prefix+'\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
