"""P2'' margin calibration: independent default-vs-default scan realizations.

Generates K replicate documents with the P2 generator layout and phrases, using only FONT-01
*train* faces and fresh seeds, converts each with default ClearScan, and scores isolated
pristine error per observation with the unchanged R2c method. No P2, P2', P2'' or development
result enters the calibration.

  generate  -> local/P2pp-calibration/rep-K/ (pages + oracle)
  convert   -> rep-K/sheet-N.pdf, rep-K/sheet-N-off.pdf
  score     -> rep-K/records.json
  margins   -> qualification/font04/p2pp-margins.json
"""
import argparse
import hashlib
import json
import os
import subprocess
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

from qualification.font01 import benchmark
from qualification.font04 import r2b_generator

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'qualification/font04/local/P2pp-calibration'
OUT = ROOT / 'qualification/font04/p2pp-margins.json'
K = 6
PHRASES = tuple(json.loads((ROOT/'qualification/font04/p2-preregistration-v1.1.json').read_text())['generator']['phrases'])
DPIS = (200, 300, 600)
BINARY = ROOT / 'qualification/font04/local/R2a/resume-optimized/scanweave'


def seed(k):
    return int(hashlib.sha256(f'FONT-04 P2pp calibration replicate {k}'.encode()).hexdigest()[:8], 16)


def train_faces():
    frozen = json.loads((ROOT/'qualification/font01/fixture-manifest.json').read_text())
    faces = [f for s in frozen['split_records'] if s['split'] == 'train' for f in s['faces']]
    for f in faces:
        assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest() == f['sha256'], f['name']
    return [dict(f, split='calibration') for f in faces]


def generate():
    benchmark.PHRASES = PHRASES
    faces = train_faces()
    for k in range(K):
        root = BASE/f'rep-{k}/doc'
        if root.exists():
            continue
        manifest = r2b_generator.generate_document(root, faces, seed(k), DPIS, is_p2=True)
        assert not manifest['damage_coverage']['incomplete']
        print('generated', k, seed(k), flush=True)


def sheets(rep):
    rows = [json.loads(x) for x in (rep/'doc/observations.jsonl').read_text().splitlines()]
    return sorted({(r['page'], r['sheet']) for r in rows})


def convert():
    import pikepdf
    env = dict(os.environ, SCANWEAVE_PDFIUM_LIBRARY=str(ROOT/'tools/src/pdfium/lib/libpdfium.so'),
               SCANWEAVE_RESEARCH_PYTHON='/nonexistent', OMP_THREAD_LIMIT='1', RAYON_NUM_THREADS='4')
    for k in range(K):
        rep = BASE/f'rep-{k}'
        order = sheets(rep)
        with pikepdf.open(rep/'doc/scan.pdf') as src:
            assert len(src.pages) == len(order)
            for i in range(len(order)):
                path = rep/f'sheet-{i}.pdf'
                if not path.exists():
                    pdf = pikepdf.Pdf.new()
                    pdf.pages.append(src.pages[i])
                    pdf.save(path)
        for i, (page, _) in enumerate(order):
            out = rep/f'sheet-{i}-off.pdf'
            if out.exists():
                continue
            subprocess.run([str(BINARY), str(rep/f'sheet-{i}.pdf'), str(out), '--dpi', str(DPIS[page]),
                            '--profile', 'clearscan', '--glyph-sharing', 'off'], env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print('converted', k, i, flush=True)


def score():
    from PIL import Image, ImageChops
    from qualification.font04.metrics import measure, render
    for k in range(K):
        rep = BASE/f'rep-{k}'
        if (rep/'records.json').exists():
            continue
        rows = [json.loads(x) for x in (rep/'doc/observations.jsonl').read_text().splitlines()]
        truth = {x['id']: x for x in map(json.loads, (rep/'doc/oracle/labels.jsonl').read_text().splitlines())}
        records = []
        for i, (page, sheet) in enumerate(sheets(rep)):
            dpi = DPIS[page]
            selected = [r for r in rows if r['page'] == page and r['sheet'] == sheet]
            pristine = Image.new('L', (6*dpi, 9*dpi), 255)
            for r in selected:
                with Image.open(rep/'doc/oracle'/f"{r['id']}-pristine.png") as glyph:
                    pristine.paste(ImageChops.darker(pristine.crop(r['bbox']), glyph), r['bbox'][:2])
            reference = np.asarray(pristine)
            for engine in ('pdfium', 'poppler'):
                image = render(rep/f'sheet-{i}-off.pdf', 0, dpi, engine)
                for r in selected:
                    x, y, xx, yy = r['bbox']
                    t = truth[r['id']]
                    records.append(dict(character=t['character'], face=t['face'], dpi=dpi, severity=t['severity'],
                                        point_size=t['point_size'], renderer=engine,
                                        error=measure(1 - reference[y:yy, x:xx]/255., 1 - image[y:yy, x:xx]/255.)['error']))
        (rep/'records.json').write_text(json.dumps(records) + '\n')
        print('scored', k, flush=True)


def margins():
    reps = [json.loads((BASE/f'rep-{k}/records.json').read_text()) for k in range(K)]
    stats = defaultdict(dict)
    cells = defaultdict(lambda: defaultdict(list))
    for k, records in enumerate(reps):
        by = defaultdict(list)
        for r in records:
            by[(r['character'], r['renderer'])].append(r['error'])
            cells[(r['face'], r['character'], r['dpi'], r['severity'], r['point_size'], r['renderer'])][k].append(r['error'])
        for key, v in by.items():
            if len(v) >= 10:
                stats[key][k] = (float(np.mean(v)), float(np.quantile(v, .95)))
    result = {}
    for (character, renderer), per in stats.items():
        if len(per) < K:
            continue
        diffs = [(abs(per[a][0]-per[b][0]), abs(per[a][1]-per[b][1])) for a, b in combinations(range(K), 2)]
        result[f'{character}|{renderer}'] = dict(mean_margin=float(np.quantile([d[0] for d in diffs], .95)),
                                                 p95_margin=float(np.quantile([d[1] for d in diffs], .95)),
                                                 replicate_pairs=len(diffs))
    # Per-occurrence tail threshold: spread of default error between exchangeable occurrences of the
    # same nominal glyph (face, character, DPI, damage band, point size) drawn in different replicates.
    spread = defaultdict(list)
    for key, per in cells.items():
        values = [v for vs in per.values() for v in vs]
        if len(per) >= 2:
            spread[key[-1]].extend(abs(a - b) for a, b in combinations(values, 2))
    tail = {r: float(np.quantile(v, .99)) for r, v in spread.items()}
    OUT.write_text(json.dumps(dict(
        schema='font04-p2pp-margins-v1', replicates=K, seeds=[seed(k) for k in range(K)],
        faces='FONT-01 train faces (hash-verified against fixture-manifest.json)', phrases=list(PHRASES),
        default_binary_sha256=hashlib.sha256(BINARY.read_bytes()).hexdigest(),
        class_margin_rule='95th percentile over all replicate pairs of |stat_a - stat_b| per character class and renderer; classes need >=10 observations in every replicate',
        tail_threshold_rule='99th percentile of |error_a - error_b| between default occurrences of the same face, character, DPI, damage band and point size in different replicates, per renderer',
        class_margins=result, tail_threshold=tail), indent=1) + '\n')
    print(len(result), 'class margins; tail', tail)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=('generate', 'convert', 'score', 'margins', 'all'))
    stage = p.parse_args().stage
    for name, fn in (('generate', generate), ('convert', convert), ('score', score), ('margins', margins)):
        if stage in (name, 'all'):
            fn()
