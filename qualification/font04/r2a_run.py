"""Serial paired/repeat R2a runs with a stop on any PDF byte change."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'qualification/font04/local/R2a'
GROUPS = ('forms','receipts','mixed','historical','financial')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(binary, directory, groups=GROUPS, include_repeat=True, include_comparison=True):
    directory.mkdir(parents=True,exist_ok=True)
    baseline = LOCAL/'baseline'
    golden = json.loads((ROOT/'qualification/font04/checkpoint-R1.json').read_text())['PDFs']
    library = ROOT/'tools/src/pdfium/lib/libpdfium.so'
    for group in groups:
        modes = [('off','off',4),('cover-2.0','cover-2.0',4)]
        if group == 'financial' and include_comparison:modes.append(('cover-1.5','cover-1.5',4))
        if include_repeat:modes.append(('cover-2.0-repeat','cover-2.0',8))
        for label,mode,threads in modes:
            output = directory/f'{group}-{label}.pdf'
            receipt = output.with_suffix('.run.json')
            expected = golden['cover-1.5']['sha256'] if mode=='cover-1.5' else digest(baseline/f'{group}-{mode}.pdf')
            if receipt.exists() and output.exists():
                previous = json.loads(receipt.read_text())
                if previous.get('returncode')==0 and previous.get('binary_sha256')==digest(binary) and digest(output)==expected:
                    print('REUSE',output,flush=True)
                    continue
                raise RuntimeError('Existing incompatible receipt; never overwrite: '+str(receipt))
            env = dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(library),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS=str(threads))
            command = [str(binary),str(ROOT/f'qualification/pdf_packaging/groups/{group}-input.pdf'),str(output),'--dpi','300','--profile','clearscan','--glyph-sharing',mode]
            started = time.monotonic()
            with output.with_suffix('.log').open('w') as log:
                result = subprocess.run(['/usr/bin/time','-v','-o',str(output.with_suffix('.time')),*command],env=env,stdout=log,stderr=subprocess.STDOUT)
            row = dict(group=group,mode=mode,label=label,threads=threads,command=command,returncode=result.returncode,wall_seconds=time.monotonic()-started,
                       binary_sha256=digest(binary),pdfium_library_sha256=digest(library),expected_sha256=expected)
            if result.returncode==0:
                row.update(sha256=digest(output),bytes=output.stat().st_size)
                row['byte_identical_to_baseline'] = row['sha256']==expected
                report = json.loads(Path(str(output)+'.json').read_text())
                sharing = report['conversion'].get('glyph_sharing')
                if sharing and sharing['pdfium'] is not None:
                    assert sharing['pdfium']['sha256']==row['pdfium_library_sha256']
                row['stage_timings'] = report['conversion']['stage_timings']
                row['sharing_stage_seconds'] = sharing['stage_seconds'] if sharing else None
            receipt.write_text(json.dumps(row,indent=2)+'\n')
            print(json.dumps(row),flush=True)
            if result.returncode or not row.get('byte_identical_to_baseline'):
                raise RuntimeError('STOP: failed run or method/output change: '+str(receipt))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('binary',type=Path)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--groups',nargs='+',choices=GROUPS,default=GROUPS)
    parser.add_argument('--no-repeat',action='store_true')
    parser.add_argument('--no-comparison',action='store_true')
    args = parser.parse_args()
    run(args.binary.resolve(),args.directory.resolve(),args.groups,not args.no_repeat,not args.no_comparison)
