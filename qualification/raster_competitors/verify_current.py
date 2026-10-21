"""Run current ordinary converter into scratch; never overwrite frozen outputs."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent


def main():
    out=BASE/'local/current';out.mkdir(parents=True,exist_ok=True)
    groups=json.loads((ROOT/'qualification/pdf_packaging/groups.json').read_text())
    binary_sha256=hashlib.sha256((ROOT/'target/release/scanweave').read_bytes()).hexdigest()
    receipt=BASE/'current-verification.json'
    results=json.loads(receipt.read_text()) if receipt.exists() else []
    for name,group in groups.items():
        destination=out/(name+'.pdf')
        command=[str(ROOT/'target/release/scanweave'),str(ROOT/group['input']),str(destination)]
        frozen=ROOT/'qualification/tonal_raster/collections'/destination.name
        input_sha256=hashlib.sha256((ROOT/group['input']).read_bytes()).hexdigest()
        if destination.exists() and any(r['collection']==name and r['byte_identical'] and r.get('binary_sha256')==binary_sha256 and r.get('input_sha256')==input_sha256 for r in results):
            if hashlib.sha256(destination.read_bytes()).hexdigest()==hashlib.sha256(frozen.read_bytes()).hexdigest():
                continue
        start=time.monotonic()
        with (out/(name+'.log')).open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if result.returncode:
            raise RuntimeError(name+' current conversion failed')
        actual=hashlib.sha256(destination.read_bytes()).hexdigest()
        frozen=ROOT/'qualification/tonal_raster/collections'/destination.name
        expected=hashlib.sha256(frozen.read_bytes()).hexdigest()
        results=[r for r in results if r['collection']!=name]
        results.append({'collection':name,'command':command,'seconds':time.monotonic()-start,
                        'current_sha256':actual,'frozen_sha256':expected,'byte_identical':actual==expected,
                        'bytes':destination.stat().st_size,'binary_sha256':binary_sha256,'input_sha256':input_sha256})
        (BASE/'current-verification.json').write_text(json.dumps(results,indent=2)+'\n')
        print(name,results[-1],flush=True)
        if actual!=expected:
            raise RuntimeError('Current converter differs; do not silently call frozen output current')


if __name__=='__main__':
    main()
