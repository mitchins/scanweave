#!/usr/bin/env python3
"""Run CI's Python gates with the requested isolated interpreter and checkout on sys.path."""
import json,os,subprocess,sys,time
from pathlib import Path
cwd=Path('/tmp/scanweave-donorfix'); out=Path('/data/coding/scanweave/qualification/acr06/local/donorfix/checks'); out.mkdir(exist_ok=True,parents=True)
files=['qualification/test_subpixel_metric.py','qualification/test_corpus_adapter.py','qualification/validate_fixtures.py','qualification/test_tools_env.py','qualification/test_reliability_indices.py','qualification/test_high_wave1.py','qualification/test_high_wave3.py','qualification/test_font01_benchmark.py','qualification/test_font01_statistics.py','qualification/test_font01_challenger.py','qualification/test_font01_analysis.py','qualification/test_corpus_boundaries.py','qualification/test_hocr_xml_security.py','qualification/test_text_search.py','qualification/experiments/m1c_r3/test_translation.py','qualification/experiments/m1c_r3/generator.py','qualification/experiments/m1c_r3/test_diagnostic_modes.py','qualification/test_m1b_paint_fidelity.py','qualification/test_m1b_document_search.py']
commands=[(p,'file') for p in files]; commands.insert(11,('qualification.font02.test_rendered_reuse','module'))
rows=[]
for index,(name,kind) in enumerate(commands):
 code=("import sys,runpy; sys.path[:0]=['.', 'qualification', %r, '/tmp/scanweave-donorfix-torch']; sys.argv=[%r]; runpy.run_path(%r,run_name='__main__')"%(str(Path(name).parent),name,name) if kind=='file' else "import sys,runpy; sys.path[:0]=['.', 'qualification', '/tmp/scanweave-donorfix-torch']; sys.argv=['unittest',%r]; runpy.run_module('unittest',run_name='__main__')"%name)
 env=dict(os.environ, M1CR3_REPORT='work/m1c_r3/diag4/diagnostic_full.json', SCANWEAVE_PDFIUM_LIBRARY='/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so',SCANWEAVE_OTS='/tmp/scanweave-donorfix-ots/build/ots-sanitize', PYTHONPATH='/tmp/scanweave-donorfix-torch', SCANWEAVE_QPDF='/tmp/scanweave-qpdf-deb/root/usr/bin/qpdf', LD_LIBRARY_PATH='/tmp/scanweave-qpdf-deb/root/usr/lib/x86_64-linux-gnu'); start=time.monotonic(); log=out/f'python-{index:02d}.log'
 with log.open('w') as f: p=subprocess.run([sys.executable,'-I','-c',code],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append({'gate':name,'returncode':p.returncode,'seconds':time.monotonic()-start,'log':str(log)})
 (out/'python-results.json').write_text(json.dumps(rows,indent=2)+'\n'); print(name,p.returncode,flush=True)
