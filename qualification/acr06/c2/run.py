#!/usr/bin/env python3
"""Run only the previously opened ACR-06 C2 corpus; never writes to the inputs."""
import concurrent.futures
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/data/coding/scanweave')
INPUT = ROOT / 'qualification/font04/local'
OUT = ROOT / 'qualification/acr06/local/c2'
BIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path('/tmp/c2-research-scanweave')

def documents():
    for kind, folder in [('p2', 'P2'), ('p2prime', 'P2prime'), ('p2pp', 'P2pp')]:
        for i in range(9):
            yield f'{kind}-{i}', INPUT / folder / f'sheet-{i}.pdf', (200, 300, 600)[i // 3]
    for split in ('train', 'validation', 'test'):
        for i in range(3):
            yield f'font01-{split}-{i}', INPUT / 'S1/font01' / f'{split}-{i}.pdf', (200, 300, 600)[i]
    for name in ('financial', 'mixed'):
        yield name, ROOT / 'qualification/pdf_packaging/groups' / f'{name}-input.pdf', 300

def run(job):
    name, src, dpi, mode = job
    dest = OUT / mode / f'{name}.pdf'
    dest.parent.mkdir(parents=True, exist_ok=True)
    if Path(str(dest) + '.done').exists():
        return f'{mode} {name} cached'
    env = dict(os.environ, SCANWEAVE_PDFIUM_LIBRARY=str(ROOT / 'tools/src/pdfium/lib/libpdfium.so'),
               SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python', OMP_THREAD_LIMIT='1', RAYON_NUM_THREADS='4',
               SCANWEAVE_RESEARCH_OWNERSHIP=mode, SCANWEAVE_RESEARCH_OWNERSHIP_TRACE=str(dest)+'.ownership.json')
    cmd = [str(BIN), str(src), str(dest), '--dpi', str(dpi), '--profile', 'clearscan', '--glyph-sharing', 'cover-2.0-ceiling-q3']
    with open(str(dest)+'.log', 'w') as log:
        result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'{mode} {name}: exit {result.returncode}; see {dest}.log')
    Path(str(dest)+'.done').write_text('ok\n')
    return f'{mode} {name} done'

if __name__ == '__main__':
    docs = list(documents())
    # Start the longest jobs first; timed comparisons are separate and serial.
    docs.sort(key=lambda d: (d[0] != 'financial', d[0] != 'mixed', -d[2], d[0]))
    jobs = [(name, src, dpi, mode) for name, src, dpi in docs for mode in ('trace', 'corrected-only')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(run, jobs):
            print(result, flush=True)
