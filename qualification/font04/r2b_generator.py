"""Guarded FONT-04 P2 entry point and FONT-01 identity reproduction wrapper."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from qualification.font01 import benchmark

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'qualification/font04'
P2 = BASE / 'local/P2'
PREREG = BASE / 'p2-preregistration.json'
EXPECTED = 'a4f9ccd3a7e51d719946be80f7cc9a297de7ca22285e8755e5e26e415e7db466'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('font01', 'p2'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--verify-manifest', type=Path)
    args = parser.parse_args()
    if args.split == 'font01':
        if args.binary is not None:
            parser.error('--binary is only for P2')
        sys.argv = [sys.argv[0], '--out', str(args.out)]
        if args.verify_manifest:
            sys.argv += ['--verify-manifest', str(args.verify_manifest)]
        benchmark.main()
        return
    if args.binary is None or args.verify_manifest is not None:
        parser.error('P2 requires --binary and does not accept --verify-manifest')
    if args.out.resolve() != (P2 / 'p2').resolve():
        parser.error('P2 output must be qualification/font04/local/P2/p2')
    if sha(PREREG) != EXPECTED:
        raise ValueError('preregistration hash mismatch')
    registration = json.loads(PREREG.read_text())
    if json.loads((BASE / 'method-freeze.json').read_text()).get('p2_preregistration_sha256') != EXPECTED:
        raise ValueError('method freeze does not reference preregistration')
    for face in registration['faces']:
        if sha(Path(face['path'])) != face['sha256']:
            raise ValueError('face hash mismatch: ' + face['name'])
    binary_hash = sha(args.binary)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if args.out.exists():
        raise FileExistsError(args.out)
    P2.mkdir(parents=True, exist_ok=True)
    lock = P2 / 'OPENED'
    receipt = {'timestamp': datetime.now(timezone.utc).isoformat(), 'git_head': head,
               'product_binary_sha256': binary_hash, 'argv': sys.argv}
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, 'w') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    benchmark.PHRASES = tuple(registration['generator']['phrases'])
    faces = [dict(face, split='p2') for face in registration['faces']]
    manifest = benchmark.generate_document(args.out, faces, registration['generator']['seed'],
                                           tuple(registration['generator']['dpis']))
    if manifest['damage_coverage']['incomplete']:
        raise ValueError('Incomplete clean/damaged coverage')


if __name__ == '__main__':
    main()
