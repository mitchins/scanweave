#!/usr/bin/env python3
import hashlib, json, os, subprocess, time
from pathlib import Path
root = Path('/data/coding/scanweave')
q = root / 'qualification'
out = q / 'acr06/local/donorfix/baseline'
env = dict(os.environ, SCANWEAVE_PDFIUM_LIBRARY=str(root / 'tools/src/pdfium/lib/libpdfium.so'), SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python', OMP_THREAD_LIMIT='1', RAYON_NUM_THREADS='4')
binary = '/tmp/scanweave-donorfix/target/release/scanweave'
results = []
for group in ('receipts', 'forms', 'historical', 'mixed', 'financial'):
    dest = out / (group + '-off.pdf')
    cmd = [binary, str(q / ('pdf_packaging/groups/' + group + '-input.pdf')), str(dest), '--dpi', '300', '--profile', 'clearscan', '--glyph-sharing', 'off']
    start = time.monotonic()
    with (out / (group + '.log')).open('w') as log:
        proc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    row = {'group': group, 'command': cmd, 'returncode': proc.returncode, 'seconds': time.monotonic() - start}
    if proc.returncode == 0:
        row['sha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
        row['reference_sha256'] = hashlib.sha256((q / ('font04/local/R2a/baseline/' + group + '-off.pdf')).read_bytes()).hexdigest()
        row['identical'] = row['sha256'] == row['reference_sha256']
    results.append(row)
    (out / 'identity.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(row), flush=True)
    if proc.returncode or not row['identical']:
        raise SystemExit('Baseline gate failed; stopping as requested')
