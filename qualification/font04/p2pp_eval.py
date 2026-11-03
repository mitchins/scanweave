"""P2'' single-use evaluation (frozen before opening). Stages, run in order:

  convert    9 sheets x arms {off, cover-2.0-ceiling (reference), cover-2.0-ceiling-q3 (candidate)} + candidate repeat
  pristine   unchanged R2c pristine method (composited pristine page, observation boxes, PDFium + Poppler)
  numeric    class non-inferiority vs p2pp-margins.json and per-renderer tail sign test
  functional extraction / native search / qpdf / OTS, candidate vs default; determinism
  economy    sidecar economy, actual font bytes, PDF bytes, runtime, peak RSS
  package    blind package + sealed key + sealed oracle census (local/P2pp/sealed)
  unseal     join committed grades to the key (only after grades are committed)

Oracle labels never enter conversion or candidate selection; the census is sealed until grading ends.
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
F4 = ROOT / 'qualification/font04'
P = Path(os.environ.get('P2PP_DIR', F4 / 'local/P2pp'))  # override only for pre-opening dry runs
OUTDIR = Path(os.environ.get('P2PP_OUT', F4))
DPIS = (200, 300, 600)
BIN = {'off': F4/'local/R2a/resume-optimized/scanweave',
       'cover-2.0-ceiling': F4/'local/S1d/scanweave',
       'cover-2.0-ceiling-q3': F4/'local/S2/scanweave'}
EXPECTED_BIN = {'off': '85fc1aa659f9729aebd510c1c6bb0328757b4130d02040965c94bf047a009a57',
                'cover-2.0-ceiling': 'd3a26c6d0677563858f2c57e393ec538d0395335a7460f960ef228705aee4177',
                'cover-2.0-ceiling-q3': '8667f6dd0594d4f7d488df392c7a2f639ac01a21c665a7ab4147c036af68ee70'}
ARMS = ('off', 'cover-2.0-ceiling', 'cover-2.0-ceiling-q3')
CAND, REF = 'cover-2.0-ceiling-q3', 'cover-2.0-ceiling'
PACKAGE_SEED = 20261103
CONTROLS = 100


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_doc():
    rows = [json.loads(x) for x in (P/'p2pp/observations.jsonl').read_text().splitlines()]
    truth = {x['id']: x for x in map(json.loads, (P/'p2pp/oracle/labels.jsonl').read_text().splitlines())}
    return rows, truth


def convert():
    import pikepdf
    assert (P/'OPENED').exists()
    for arm, b in BIN.items():
        assert sha(b) == EXPECTED_BIN[arm], arm
    env = dict(os.environ, SCANWEAVE_PDFIUM_LIBRARY=str(ROOT/'tools/src/pdfium/lib/libpdfium.so'),
               SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python', OMP_THREAD_LIMIT='1', RAYON_NUM_THREADS='4')
    with pikepdf.open(P/'p2pp/scan.pdf') as src:
        assert len(src.pages) == 9
        for i in range(9):
            if not (P/f'sheet-{i}.pdf').exists():
                pdf = pikepdf.Pdf.new()
                pdf.pages.append(src.pages[i])
                pdf.save(P/f'sheet-{i}.pdf')
    for i in range(9):
        for label, arm in [(a, a) for a in ARMS] + [(CAND + '-repeat', CAND)]:
            out = P/f'sheet-{i}-{label}.pdf'
            if (P/f'sheet-{i}-{label}.run.json').exists():
                continue
            assert not out.exists(), f'interrupted output needs manual review: {out}'
            cmd = [str(BIN[arm]), str(P/f'sheet-{i}.pdf'), str(out), '--dpi', str(DPIS[i//3]), '--profile', 'clearscan', '--glyph-sharing', arm]
            started = time.monotonic()
            with open(str(out) + '.log', 'w') as log:
                r = subprocess.run(['/usr/bin/time', '-v', '-o', str(out) + '.time', *cmd], env=env, stdout=log, stderr=subprocess.STDOUT)
            row = dict(sheet=i, label=label, arm=arm, returncode=r.returncode, wall_seconds=time.monotonic() - started,
                       binary_sha256=sha(BIN[arm]), sha256=sha(out) if r.returncode == 0 else None)
            (P/f'sheet-{i}-{label}.run.json').write_text(json.dumps(row, indent=1) + '\n')
            print(json.dumps(row), flush=True)
            if r.returncode:
                raise RuntimeError('conversion failed')


def pristine():
    from PIL import Image, ImageChops
    from qualification.font04.metrics import measure, render
    rows, truth = load_doc()
    records = []
    for i in range(9):
        dpi = DPIS[i//3]
        selected = [r for r in rows if r['page'] == i//3 and r['sheet'] == i % 3]
        pristine_page = Image.new('L', (6*dpi, 9*dpi), 255)
        for r in selected:
            with Image.open(P/'p2pp/oracle'/f"{r['id']}-pristine.png") as glyph:
                pristine_page.paste(ImageChops.darker(pristine_page.crop(r['bbox']), glyph), r['bbox'][:2])
        reference = np.asarray(pristine_page)
        for engine in ('pdfium', 'poppler'):
            images = {a: render(P/f'sheet-{i}-{a}.pdf', 0, dpi, engine) for a in ARMS}
            for r in selected:
                x, y, xx, yy = r['bbox']
                ref = 1 - reference[y:yy, x:xx].astype(float)/255
                t = truth[r['id']]
                rec = dict(id=r['id'], sheet=i, character=t['character'], dpi=dpi, damage='D' + str(t['severity']), renderer=engine)
                for a in ARMS:
                    rec[a] = measure(ref, 1 - images[a][y:yy, x:xx].astype(float)/255)
                records.append(rec)
        print('scored', i, flush=True)
    (P/'pristine-records.json').write_text(json.dumps(records) + '\n')


def numeric():
    from scipy.stats import binomtest
    margins = json.loads((F4/'p2pp-margins.json').read_text())
    records = json.loads((P/'pristine-records.json').read_text())
    out = dict(margins_sha256=sha(F4/'p2pp-margins.json'), classes={}, tail={}, overall={})
    passed = True
    for engine in ('pdfium', 'poppler'):
        rs = [r for r in records if r['renderer'] == engine]
        by = defaultdict(list)
        for r in rs:
            by[r['character']].append(r)
        for c, v in sorted(by.items()):
            if len(v) < 10:
                continue
            stat = {a: (float(np.mean([r[a]['error'] for r in v])), float(np.quantile([r[a]['error'] for r in v], .95))) for a in ARMS}
            m = margins['class_margins'].get(f'{c}|{engine}')
            d_mean, d_p95 = stat[CAND][0] - stat['off'][0], stat[CAND][1] - stat['off'][1]
            ok = m is not None and d_mean <= m['mean_margin'] and d_p95 <= m['p95_margin']
            passed &= ok
            out['classes'][f'{c}|{engine}'] = dict(n=len(v), default=stat['off'], reference=stat[REF], candidate=stat[CAND],
                                                    delta_mean=d_mean, delta_p95=d_p95, margin=m, pass_=ok)
        tau = margins['tail_threshold'][engine]
        d = np.array([r[CAND]['error'] - r['off']['error'] for r in rs])
        w, b = int((d > tau).sum()), int((d < -tau).sum())
        p = binomtest(w, w + b, .5, alternative='greater').pvalue if w + b else 1.0
        out['tail'][engine] = dict(tau=tau, worse=w, better=b, p_value=p, pass_=p >= .05,
                                   review_selected=int((d > .5*tau).sum()))
        passed &= p >= .05
        out['overall'][engine] = {a: dict(mean=float(np.mean([r[a]['error'] for r in rs])),
                                          p95=float(np.quantile([r[a]['error'] for r in rs], .95))) for a in ARMS}
    out['pass_'] = passed
    (OUTDIR/'p2pp-numeric.json').write_text(json.dumps(out, indent=1) + '\n')
    print('numeric pass', passed, json.dumps(out['tail']))


def functional():
    from qualification.font04.r2a_audit import extraction, fonts, command
    from qualification.font04.functional_guard import native
    res = []
    for i in range(9):
        d, c = P/f'sheet-{i}-off.pdf', P/f'sheet-{i}-{CAND}.pdf'
        ed, ec = extraction(d), extraction(c)
        qpdf = command([ROOT/'tools/dist/bin/qpdf', '--check', c]).decode()
        w = P/'functional'/str(i)
        w.mkdir(parents=True, exist_ok=True)
        ots = []
        for digest, (data, _) in fonts(c).items():
            f = w/(digest + '.ttf')
            f.write_bytes(data)
            ots.append(command([ROOT/'tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize', f, str(f) + '.sanitized']).decode())
        row = dict(sheet=i, extraction_equal={k: ed[k] == ec[k] for k in ed}, native_search_equal=native(d, 0)[1] == native(c, 0)[1],
                   qpdf_ok='No syntax or stream encoding errors' in qpdf, ots_fonts=len(ots),
                   repeat_identical=sha(c) == sha(P/f'sheet-{i}-{CAND}-repeat.pdf'))
        row['pass_'] = all(row['extraction_equal'].values()) and row['native_search_equal'] and row['qpdf_ok'] and row['ots_fonts'] > 0 and row['repeat_identical']
        res.append(row)
        print('functional', i, row['pass_'], flush=True)
    (OUTDIR/'p2pp-functional.json').write_text(json.dumps(dict(sheets=res, pass_=all(r['pass_'] for r in res)), indent=1) + '\n')


def economy():
    from qualification.font04.r2a_audit import fonts
    out = []
    for i in range(9):
        row = dict(sheet=i, dpi=DPIS[i//3], arms={})
        for a in ARMS:
            p = P/f'sheet-{i}-{a}.pdf'
            conv = json.loads(Path(str(p) + '.json').read_text())['conversion']
            g = conv.get('glyph_sharing') or {}
            t = Path(str(p) + '.time').read_text()
            row['arms'][a] = dict(pdf_bytes=p.stat().st_size, font_bytes=sum(x[1] for x in fonts(p).values()),
                                  substituted=g.get('substituted'), retired=g.get('retired_outlines'), added=g.get('added_canonicals'),
                                  net_outlines_retired=g.get('net_outlines_retired'), fallback=g.get('fallback'),
                                  wall=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)', t).group(1),
                                  max_rss_kib=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', t).group(1)))
        out.append(row)
    tot = {a: {k: sum(r['arms'][a][k] or 0 for r in out) for k in ('pdf_bytes', 'font_bytes', 'substituted', 'net_outlines_retired')} for a in ARMS}
    (OUTDIR/'p2pp-economy.json').write_text(json.dumps(dict(sheets=out, totals=tot), indent=1) + '\n')
    print(json.dumps(tot, indent=1))


def decisions(i, arm):
    conv = json.loads(Path(str(P/f'sheet-{i}-{arm}.pdf') + '.json').read_text())['conversion']
    obs = {o['symbol_id']: o for o in conv['page_reports'][0]['reconstruction']['observations']}
    return conv['glyph_sharing']['decisions'], obs


def package():
    from PIL import Image, ImageDraw
    from qualification.font04.metrics import render
    from qualification.font04.s1d_eval import join, classify
    rng = random.Random(PACKAGE_SEED)
    rows, truth = load_doc()
    margins = json.loads((F4/'p2pp-margins.json').read_text())
    records = json.loads((P/'pristine-records.json').read_text())
    tail_ids = {(r['sheet'], r['id']) for r in records if r[CAND]['error'] - r['off']['error'] > .5*margins['tail_threshold'][r['renderer']]}
    items, census = [], {}
    for i in range(9):
        cand, obs = decisions(i, CAND)
        ref, robs = decisions(i, REF)
        targets = [o for o in rows if o['page'] == i//3 and o['sheet'] == i % 3]
        joined = join([{'id': o['symbol_id'], 'bbox': o['bbox_px'], 'character': o['text_hypothesis']} for o in obs.values()], targets)
        admitted = {d['id'] for d in cand if d['accepted'] and d['member'] != d['canonical']}
        ref_only = [d['id'] for d in ref if d['accepted'] and d['member'] != d['canonical'] and d['id'] not in admitted]
        for sid in sorted(admitted):
            items.append(('admitted', i, ('bbox', obs[sid]['bbox_px']), CAND, sid))
        oracle_to_sym = {v: k for k, v in joined.items()}
        for (s, oid) in sorted(tail_ids):
            if s == i:
                o = next(t for t in targets if t['id'] == oid)
                items.append(('tail', i, ('bbox', o['bbox']), CAND, oracle_to_sym.get(oid, oid)))
        for sid in ref_only:
            items.append(('control', i, ('bbox', robs[sid]['bbox_px']), REF, sid))
        by = {d['member']: d for d in cand}
        led = Counter()
        for d in cand:
            if not d['accepted'] or d['member'] == d['canonical']:
                continue
            a, b = joined.get(d['id']), joined.get(by[d['canonical']]['id'])
            led[classify(truth[a], truth[b]) if a and b else 'unresolved'] += 1
        census[i] = dict(led)
    controls = [x for x in items if x[0] == 'control']
    rng.shuffle(controls)
    items = [x for x in items if x[0] != 'control'] + controls[:CONTROLS]
    rng.shuffle(items)
    (P/'blind').mkdir(parents=True, exist_ok=True)
    (P/'sealed').mkdir(parents=True, exist_ok=True)
    pages = {}
    key, panels = [], []
    for n, (stratum, i, (_, bx), arm, sid) in enumerate(items, 1):
        dpi = DPIS[i//3]
        for a in ('off', arm):
            if (i, a) not in pages:
                pages[(i, a)] = Image.fromarray(render(P/f'sheet-{i}-{a}.pdf', 0, dpi, 'pdfium'))
        scan = Image.open(P/f'p2pp/page-{i//3}-{i % 3}.png').convert('L')
        bx = [int(round(v)) for v in bx]
        h = max(8, bx[3] - bx[1])
        box = (bx[0] - 3*h, bx[1] - h//2, bx[2] + 3*h, bx[3] + h//2)
        order = ['off', arm]
        rng.shuffle(order)
        tiles = [scan.crop(box)] + [pages[(i, a)].crop(box) for a in order]
        tb = (bx[0] - box[0], bx[1] - box[1], bx[2] - box[0], bx[3] - box[1])
        row_parts = []
        for scale in (1, 2):
            ts = []
            for t in tiles:
                t = t.convert('RGB')
                ImageDraw.Draw(t).rectangle(tb, outline=(220, 0, 0))
                ts.append(t.resize((t.width*scale, t.height*scale), Image.NEAREST))
            row_parts.append(ts)
        width = max(sum(t.width for t in ts) + 40*3 + 60 for ts in row_parts)
        height = sum(max(t.height for t in ts) + 18 for ts in row_parts)
        panel = Image.new('RGB', (width, height), 'white')
        dr = ImageDraw.Draw(panel)
        y = 0
        for scale, ts in zip(('100%', '200%'), row_parts):
            dr.text((2, y), f'{n} {scale}', fill='black')
            x = 60
            for lab, t in zip('SXY', ts):
                dr.text((x, y), lab, fill='black')
                panel.paste(t, (x, y + 14))
                x += t.width + 40
            y += max(t.height for t in ts) + 18
        panels.append(panel)
        key.append(dict(row=n, stratum=stratum, sheet=i, id=sid, X=order[0], Y=order[1]))
    for k in range(0, len(panels), 8):
        g = panels[k:k+8]
        sheet = Image.new('RGB', (max(p.width for p in g), sum(p.height + 10 for p in g)), (200, 200, 200))
        y = 0
        for p in g:
            sheet.paste(p, (0, y))
            y += p.height + 10
        sheet.save(P/'blind'/f'sheet-{k//8:03d}.png')
    (P/'sealed/key.json').write_text(json.dumps(key, indent=1) + '\n')
    (P/'sealed/census.json').write_text(json.dumps(census, indent=1) + '\n')
    template = [dict(row=r['row'], arm=a, distinguishable_at_100=None, distinguishable_at_200=None, grade=None, reason=None) for r in key for a in 'XY']
    (P/'blind/grades-template.json').write_text(json.dumps(template, indent=1) + '\n')
    seal = dict(key_sha256=sha(P/'sealed/key.json'), census_sha256=sha(P/'sealed/census.json'),
                rows=len(key), strata=dict(Counter(k['stratum'] for k in key)), package_seed=PACKAGE_SEED)
    (OUTDIR/'p2pp-seal.json').write_text(json.dumps(seal, indent=1) + '\n')
    print(json.dumps(seal))


def unseal():
    grades = json.loads((OUTDIR/'p2pp-grades.json').read_text())
    key = {k['row']: k for k in json.loads((P/'sealed/key.json').read_text())}
    assert sha(P/'sealed/key.json') == json.loads((OUTDIR/'p2pp-seal.json').read_text())['key_sha256']
    tally = defaultdict(Counter)
    new_material = []
    by_row = defaultdict(dict)
    for g in grades:
        k = key[g['row']]
        arm = k[g['arm']]
        by_row[g['row']][arm] = g
        tally[(k['stratum'], arm)][g['grade']] += 1
    for row, arms in by_row.items():
        k = key[row]
        non_default = [a for a in arms if a != 'off'][0]
        if arms[non_default]['grade'] == 'iii' and arms['off']['grade'] != 'iii':
            new_material.append(dict(row=row, stratum=k['stratum'], arm=non_default, sheet=k['sheet'], id=k['id'], reason=arms[non_default]['reason']))
    cand_new = [m for m in new_material if m['arm'] == CAND]
    out = dict(tally={f'{s}|{a}': dict(c) for (s, a), c in tally.items()}, new_material=new_material,
               candidate_new_material=len(cand_new), material_pass_=len(cand_new) == 0)
    (OUTDIR/'p2pp-unsealed.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=('convert', 'pristine', 'numeric', 'functional', 'economy', 'package', 'unseal'))
    {'convert': convert, 'pristine': pristine, 'numeric': numeric, 'functional': functional, 'economy': economy,
     'package': package, 'unseal': unseal}[ap.parse_args().stage]()
