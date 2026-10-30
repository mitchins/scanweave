"""Resume the single opened P2 conversion; never regenerate its inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import pikepdf

ROOT = Path(__file__).resolve().parents[2]
P2 = ROOT / 'qualification/font04/local/P2'
BINARY = ROOT / 'qualification/font04/local/R2a/resume-optimized/scanweave'
LIBRARY = ROOT / 'tools/src/pdfium/lib/libpdfium.so'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    assert (P2/'OPENED').exists()
    env = dict(os.environ, SCANWEAVE_PDFIUM_LIBRARY=str(LIBRARY), SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python', OMP_THREAD_LIMIT='1', RAYON_NUM_THREADS='4')
    with pikepdf.open(P2/'p2/scan.pdf') as src:
        assert len(src.pages) == 9
        for i in range(9):
            path = P2/f'sheet-{i}.pdf'
            if not path.exists():
                pdf = pikepdf.Pdf.new(); pdf.pages.append(src.pages[i]); pdf.save(path)
    for i in range(9):
        dpi = (200, 300, 600)[i//3]
        for label, mode in [('off','off'), ('cover-2.0','cover-2.0'), ('cover-2.0-repeat','cover-2.0')]:
            output = P2/f'sheet-{i}-{label}.pdf'; receipt = output.with_suffix('.run.json')
            if receipt.exists():
                row = json.loads(receipt.read_text()); assert row['returncode'] == 0 and digest(output) == row['sha256'] and row['binary_sha256'] == digest(BINARY); continue
            assert not output.exists(), f'Interrupted output requires manual review: {output}'
            command = [str(BINARY),str(P2/f'sheet-{i}.pdf'),str(output),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing',mode]
            started = time.monotonic()
            with output.with_suffix('.log').open('w') as log:
                result = subprocess.run(['/usr/bin/time','-v','-o',str(output.with_suffix('.time')),*command],env=env,stdout=log,stderr=subprocess.STDOUT)
            row = dict(sheet=i,dpi=dpi,label=label,command=command,returncode=result.returncode,wall_seconds=time.monotonic()-started,binary_sha256=digest(BINARY),pdfium_sha256=digest(LIBRARY))
            if result.returncode == 0: row.update(sha256=digest(output),bytes=output.stat().st_size)
            receipt.write_text(json.dumps(row,indent=2)+'\n'); print(json.dumps(row),flush=True)
            if result.returncode: raise RuntimeError('Conversion failed')
            if label.endswith('repeat') and row['sha256'] != digest(P2/f'sheet-{i}-cover-2.0.pdf'): raise RuntimeError('STOP: deterministic repeat differs')
if __name__ == '__main__': main()
