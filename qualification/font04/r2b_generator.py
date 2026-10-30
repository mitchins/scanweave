"""Guarded FONT-04 generator and geometry-only precheck."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image
from qualification.font01 import benchmark

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'qualification/font04'
P2 = BASE / 'local/P2'
PREREG = BASE / 'p2-preregistration.json'
AMENDED = BASE / 'p2-preregistration-v1.1.json'
EXPECTED = 'a4f9ccd3a7e51d719946be80f7cc9a297de7ca22285e8755e5e26e415e7db466'
AMENDED_HASH = 'a62929aaa36c5384cfc5254fc32af57246e680d2c20549eb612c9b5009b833cf'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def line_observations(root, page, faces, line, page_number, dpi, rng, damage_rng,
                      assignment, severity_plan, geometry_rows=None, is_p2=False):
    """Mixed within-line context; source face is absent from public records."""
    primary, phrase_index = assignment
    text = benchmark.PHRASES[phrase_index]
    point_size = (10, 12, 15)[(line + page_number) % 3]
    x = 24 * dpi / 72
    baseline = (32 + 18 * (line % 32)) * dpi / 72
    public_rows, truth_rows = [], []
    for index, character in enumerate(text):
        face_index = benchmark.assigned_face(primary, phrase_index, index, len(faces))
        face = faces[face_index]
        source, metrics = benchmark.render_glyph(face['path'], character, point_size, dpi)
        if character.isspace():
            x += metrics['advance']
            continue
        pristine, transform = benchmark.geometry(source, rng)
        severity = severity_plan[(page_number, line, index)]
        scan, damage = benchmark.degrade(pristine, severity, damage_rng)
        origin = (round(x + metrics['bearing'][0]), round(baseline + metrics['bearing'][1]))
        box = (*origin, origin[0]+scan.width, origin[1]+scan.height)
        if not (0 <= box[0] and 0 <= box[1] and box[2] <= 6*dpi and box[3] <= 9*dpi):
            raise ValueError(f"Out-of-bounds glyph: dpi={dpi}, line={line}, bbox={box}")
        if page is not None:
            page.paste(benchmark.ImageChops.darker(page.crop(box), scan), origin)
        opaque = benchmark.digest(f"{face['split']}:{page_number}:{line}:{index}".encode())[:24]
        public = {'id': opaque, 'character': character, 'dpi': dpi,
                  'page': page_number, 'bbox': [*origin, origin[0]+scan.width, origin[1]+scan.height]}
        truth = {'font_sha256': face['sha256'], 'face': face['name'], 'family': face['family'],
                 'character': character,
                 'split': face['split'], 'document': face['split'], 'line': line,
                 'word': sum(c.isspace() for c in text[:index]), 'point_size': point_size,
                 'baseline': baseline, 'nominal_height_px': point_size*dpi/72,
                 'severity': severity, 'transform': transform, 'metrics': metrics,
                 'master_id': benchmark.digest((face['sha256'] + ':' + character).encode())}
        if is_p2:
            public['sheet'] = line // 32
            truth['sheet'] = line // 32
        if geometry_rows is not None:
            geometry_rows.append({'id': opaque, 'dpi': dpi, 'sheet': line // 32, 'line': line, 'face': face['name'], 'phrase': text, 'bbox': list(box)})
        else:
            benchmark.save_observation(root, scan, pristine, damage, public, truth)
        public_rows.append(public)
        truth_rows.append(truth)
        x += metrics['advance'] + float(rng.uniform(-.1, .3)) * dpi / 72
    return public_rows, truth_rows


def generate_document(root, faces, seed, dpis=benchmark.DPIS, geometry_only=False, is_p2=False):
    if not geometry_only:
        root.mkdir(parents=True, exist_ok=False)
        (root / 'images').mkdir()
        (root / 'oracle').mkdir()
    rng = np.random.default_rng(seed)
    damage_rng = np.random.default_rng(seed + 47000)
    schedules = [benchmark.page_schedule(len(faces), np.random.default_rng(seed + 17000 + i)) for i in range(len(dpis))]
    severity_plan = benchmark.plan_damage(len(faces), schedules, seed + 31000)
    public, truth, pages, geometry_rows = [], [], [], []
    for page_number, dpi in enumerate(dpis):
        schedule = schedules[page_number]
        for sheet in range((len(schedule) + 31) // 32):
            page = None if geometry_only else Image.new('L', (6*dpi, 9*dpi), 255)
            for line in range(sheet*32, min((sheet+1)*32, len(schedule))):
                observations, labels = line_observations(root, page, faces, line, page_number, dpi, rng, damage_rng, schedule[line], severity_plan, geometry_rows if geometry_only else None, is_p2)
                public.extend(observations)
                truth.extend(labels)
            if not geometry_only:
                for row in public:
                    if row['page'] == page_number and (not is_p2 or row['sheet'] == sheet):
                        image_path = root / row['image']
                        page.crop(row['bbox']).save(image_path)
                        row['image_sha256'] = benchmark.digest(image_path.read_bytes())
                name = f'page-{page_number}-{sheet}.png' if is_p2 else f'page-{page_number}.png'
                path = root / name
                page.save(path, dpi=(dpi, dpi))
                pages.append({'path': path.name, 'dpi': dpi, 'sha256': benchmark.digest(path.read_bytes())})
    if geometry_only:
        return geometry_rows
    benchmark.write_jsonl(root / 'observations.jsonl', public)
    benchmark.write_jsonl(root / 'oracle' / 'labels.jsonl', truth)
    benchmark.write_scan_pdf(root, pages)
    import platform, pikepdf
    from PIL import __version__ as pillow_version
    manifest = {'schema': benchmark.SCHEMA, 'seed': seed, 'faces': faces, 'pages': pages,
                'observations': len(public), 'dpi': list(dpis), 'oracle_not_for_inference': True,
                'tools': {'python': platform.python_version(), 'numpy': np.__version__, 'pillow': pillow_version, 'pikepdf': pikepdf.__version__},
                'damage_coverage': benchmark.damage_coverage(truth)}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def geometry_report(rows, faces, dpis):
    sheets = {}
    for dpi in dpis:
        for sheet in sorted({r['sheet'] for r in rows if r['dpi'] == dpi}):
            subset = [r for r in rows if r['dpi'] == dpi and r['sheet'] == sheet]
            boxes = [r['bbox'] for r in subset]
            sheets[f'{dpi}/{sheet}'] = {'dpi': dpi, 'sheet': sheet, 'size': [6*dpi, 9*dpi],
                'observations': len(subset), 'lines': len({r['line'] for r in subset}),
                'bbox_extents': [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)], 'out_of_bounds': 0}
    expected = len(faces) * sum(sum(not c.isspace() for c in phrase) for phrase in benchmark.PHRASES) * len(dpis)
    return {'expected_observations': expected, 'actual_observations': len(rows),
            'per_dpi': dict(Counter(str(r['dpi']) for r in rows)), 'per_sheet': sheets,
            'per_face': dict(Counter(r['face'] for r in rows)), 'per_phrase': dict(Counter(r['phrase'] for r in rows)),
            'out_of_bounds': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('font01', 'p2'), required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--verify-manifest', type=Path)
    parser.add_argument('--geometry-only', type=Path, metavar='OUT.json')
    args = parser.parse_args()
    if args.split == 'font01':
        if args.binary is not None:
            parser.error('--binary is only for P2')
        if args.geometry_only:
            if args.out is not None or args.verify_manifest is None:
                parser.error('FONT-01 geometry requires --verify-manifest and no --out')
            faces = benchmark.font_manifest(benchmark.installed_faces())
            benchmark.split_isolation(faces)
            frozen = json.loads(args.verify_manifest.read_text())
            benchmark.verify_frozen_assets(faces, frozen)
            results = {}
            for number, split in enumerate(('train', 'validation', 'test')):
                selected = [f for f in faces if f['split'] == split]
                rows = generate_document(None, selected, 10301 + number, geometry_only=True)
                reference = ROOT / 'qualification/font01/local/corpus-font01-v1' / split / 'observations.jsonl'
                expected = {r['id']: r['bbox'] for r in map(json.loads, reference.read_text().splitlines())}
                actual = {r['id']: r['bbox'] for r in rows}
                if actual != expected:
                    raise ValueError('FONT-01 geometry mismatch: ' + split)
                results[split] = {'observations': len(rows), 'bbox_mismatches': 0}
            args.geometry_only.write_text(json.dumps(results, indent=2) + '\n')
            return
        if args.out is None:
            parser.error('--out required')
        benchmark.generate_document = generate_document
        sys.argv = [sys.argv[0], '--out', str(args.out)]
        if args.verify_manifest:
            sys.argv += ['--verify-manifest', str(args.verify_manifest)]
        benchmark.main()
        return
    if args.binary is None or args.verify_manifest is not None:
        parser.error('P2 requires --binary and does not accept --verify-manifest')
    output = args.out if args.out is not None else P2 / 'p2'
    if output.resolve() != (P2 / 'p2').resolve():
        parser.error('P2 output must be qualification/font04/local/P2/p2')
    if sha(PREREG) != EXPECTED or sha(AMENDED) != AMENDED_HASH:
        raise ValueError('preregistration hash mismatch')
    registration = json.loads(AMENDED.read_text())
    freeze = json.loads((BASE / 'method-freeze.json').read_text())
    if (freeze.get('p2_preregistration_sha256') != EXPECTED or freeze.get('p2_preregistration_amended_sha256') != AMENDED_HASH or freeze.get('p2_preregistration_amendment', {}).get('path') != 'qualification/font04/p2-preregistration-v1.1.json'):
        raise ValueError('method freeze does not reference both preregistrations')
    for face in registration['faces']:
        if sha(Path(face['path'])) != face['sha256']:
            raise ValueError('face hash mismatch: ' + face['name'])
    binary_hash = sha(args.binary)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if output.exists():
        raise FileExistsError(output)
    lock = P2 / 'OPENED'
    if lock.exists():
        raise FileExistsError(lock)
    benchmark.PHRASES = tuple(registration['generator']['phrases'])
    faces = [dict(face, split='p2') for face in registration['faces']]
    seed, dpis = registration['generator']['seed'], tuple(registration['generator']['dpis'])
    if args.geometry_only:
        if args.geometry_only.exists():
            raise FileExistsError(args.geometry_only)
        rows = generate_document(None, faces, seed, dpis, geometry_only=True, is_p2=True)
        report = geometry_report(rows, faces, dpis)
        if report['actual_observations'] != report['expected_observations']:
            raise ValueError('observation count mismatch')
        args.geometry_only.write_text(json.dumps(report, indent=2) + '\n')
        return
    P2.mkdir(parents=True, exist_ok=True)
    receipt = {'timestamp': datetime.now(timezone.utc).isoformat(), 'git_head': head, 'product_binary_sha256': binary_hash, 'argv': sys.argv}
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, 'w') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    manifest = generate_document(output, faces, seed, dpis, is_p2=True)
    if manifest['damage_coverage']['incomplete']:
        raise ValueError('Incomplete clean/damaged coverage')


if __name__ == '__main__':
    main()
