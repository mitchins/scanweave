"""Deterministic mixed-face scan fixtures with a separate oracle namespace.

Run as ``python -m qualification.font01.benchmark --out ...``. Font programs
remain operator-installed; generated scans and training data stay out of Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import zlib

import numpy as np
import pikepdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, __version__ as pillow_version

SCHEMA = "scanweave-font01-v1"
PHRASES = ("expires", "Term expires 1921; $106.08!",
           "constant use were after", "Body TEXT 0O1Il 38.06, 1921.")
DPIS = (200, 300, 600)


def installed_faces():
    """Explicit family-disjoint manifest; no discovery-order dependence."""
    base = Path('/usr/share/fonts')
    groups = {
        'train': [('dejavu', 'DejaVuSerif', ['','-Bold']),
                  ('dejavu', 'DejaVuSans', ['','-Bold']),
                  ('dejavu', 'DejaVuSansMono', ['','-Oblique']),
                  ('freefont', 'FreeSerif', ['', 'Italic'])],
        'validation': [('urw-base35', 'C059', ['-Roman','-Bold','-Italic']),
                       ('urw-base35', 'NimbusMonoPS', ['-Regular','-Bold','-Italic']),
                       ('urw-base35', 'Z003', ['-MediumItalic'])],
        'test': [('liberation', 'LiberationSerif', ['-Regular','-Bold','-Italic','-BoldItalic']),
                 ('liberation', 'LiberationSans', ['-Regular','-Italic']),
                 ('liberation', 'LiberationMono', ['-Regular','-Italic'])],
    }
    faces = []
    for split, families in groups.items():
        for directory, family, styles in families:
            extension = '.otf' if directory == 'urw-base35' else '.ttf'
            category = 'opentype' if extension == '.otf' else 'truetype'
            for style in styles:
                faces.append({'split': split, 'family': family,
                              'name': family + style,
                              'path': str(base / category / directory / (family + style + extension))})
    return faces


def font_manifest(faces):
    """Bind local assets and their notices; fail explicitly on missing files."""
    packages = {'dejavu': ('fonts-dejavu-core', 'Bitstream-Vera'),
                'freefont': ('fonts-freefont-ttf', 'GPL-3+ with Font Exception'),
                'urw-base35': ('fonts-urw-base35', 'AGPL-3 with Font Exception'),
                'liberation': ('fonts-liberation', 'OFL-1.1')}
    result = []
    for face in faces:
        path = Path(face['path'])
        font_bytes = path.read_bytes()
        package, licence = packages[path.parent.name]
        notice = Path('/usr/share/doc') / package / 'copyright'
        result.append(dict(face, sha256=digest(font_bytes), licence=licence,
                           notice=str(notice), notice_sha256=digest(notice.read_bytes())))
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render_glyph(font_path, character, point_size, dpi):
    """Render at 4x source samples; retain baseline bearings and nominal advance."""
    supersample = 4
    size = round(point_size * dpi / 72 * supersample)
    font = ImageFont.truetype(str(font_path), size)
    bounds = font.getbbox(character, anchor='ls')
    padding = 4 * supersample
    width = max(1, bounds[2] - bounds[0]) + 2 * padding
    height = max(1, bounds[3] - bounds[1]) + 2 * padding
    image = Image.new('L', (width, height), 255)
    ImageDraw.Draw(image).text((padding - bounds[0], padding - bounds[1]), character,
                              font=font, anchor='ls', fill=0)
    target = (max(1, round(width / supersample)), max(1, round(height / supersample)))
    image = image.resize(target, Image.Resampling.LANCZOS)
    return image, {'bearing': [bounds[0] / supersample - 4, bounds[1] / supersample - 4],
                   'advance': font.getlength(character) / supersample}


def geometry(image, rng):
    """Bounded affine source perturbation, not elastic typeface deformation."""
    angle = float(rng.uniform(-1.5, 1.5))
    scale = float(rng.uniform(.96, 1.04))
    aspect = float(rng.uniform(.97, 1.03))
    shear = float(rng.uniform(-.025, .025))
    dx, dy = (float(v) for v in rng.uniform(-.45, .45, 2))
    # Pillow uses inverse mapping. Store the actual inverse matrix explicitly.
    matrix = (1 / (scale * aspect), shear, dx, 0., aspect / scale, dy)
    result = image.transform(image.size, Image.Transform.AFFINE, matrix,
                             Image.Resampling.BICUBIC, fillcolor=255)
    result = result.rotate(angle, Image.Resampling.BICUBIC, expand=False, fillcolor=255)
    return result, {'angle_degrees': angle, 'inverse_affine': list(matrix)}


def structured_loss(ink, severity, rng):
    """Contiguous removal intersects actual ink; not independent pixel dropout."""
    damaged = ink.copy()
    if severity < 2:
        return damaged
    ys, xs = np.nonzero(ink > .2)
    if not len(ys):
        return damaged
    chosen = int(rng.integers(len(ys)))
    y, x = int(ys[chosen]), int(xs[chosen])
    radius = max(1, round(min(ink.shape) * (.035, .035, .04, .09, .18)[severity]))
    damaged[max(0, y-radius):y+radius+1, max(0, x-radius):x+radius+1] = 0
    return damaged


def degrade(pristine, severity, rng):
    """Return grayscale scan plus evaluator-only changed-ink mask."""
    if severity not in range(5):
        raise ValueError('severity must be D0 through D4')
    if severity == 0:
        return pristine.copy(), Image.new('L', pristine.size, 0)
    ink = 1 - np.asarray(pristine, dtype=np.float64) / 255
    coverage = structured_loss(ink, severity, rng)
    if severity:
        coverage *= rng.uniform(.82, 1.) if severity < 2 else rng.uniform(.48, .9)
    if severity >= 2:
        gradient = np.linspace(.7, 1., ink.shape[1])[None, :]
        coverage *= gradient
    field = np.clip(255 * (1 - coverage), 0, 255).astype(np.uint8)
    impression = Image.fromarray(field)
    if severity == 2 and rng.uniform() < .25:
        impression = impression.filter(ImageFilter.MinFilter(3))
    blur = (0., .22, .35, .45, .55)[severity]
    scan = np.asarray(impression.filter(ImageFilter.GaussianBlur(blur)), dtype=float)
    noise = rng.normal(0, (0., .7, 1.1, 1.5, 2.)[severity], scan.shape)
    scan = Image.fromarray(np.clip(scan + noise, 0, 255).astype(np.uint8))
    damage = Image.fromarray(np.uint8((ink - coverage > .05) * 255))
    return scan, damage


def split_isolation(faces):
    """A family or physical font asset cannot straddle learning partitions."""
    owners = {}
    for face in faces:
        for identity in (face['family'], face.get('sha256', face['path'])):
            previous = owners.setdefault(identity, face['split'])
            if previous != face['split']:
                raise ValueError('Font family or asset crosses splits: ' + identity)


def save_observation(root, scan, pristine, damage, public, truth):
    identifier = public['id']
    scan.save(root / 'images' / (identifier + '.png'))
    pristine.save(root / 'oracle' / (identifier + '-pristine.png'))
    damage.save(root / 'oracle' / (identifier + '-damage.png'))
    public['image'] = 'images/' + identifier + '.png'
    public['image_sha256'] = digest((root / public['image']).read_bytes())
    truth['id'] = identifier


def line_observations(root, page, faces, line, page_number, dpi, rng, assignment, severity_plan):
    """Mixed within-line context; source face is absent from public records."""
    primary, phrase_index = assignment
    text = PHRASES[phrase_index]
    point_size = (10, 12, 15)[(line + page_number) % 3]
    x = 24 * dpi / 72
    baseline = (32 + 18 * line) * dpi / 72
    public_rows, truth_rows = [], []
    for index, character in enumerate(text):
        face_index = assigned_face(primary, phrase_index, index, len(faces))
        face = faces[face_index]
        source, metrics = render_glyph(face['path'], character, point_size, dpi)
        if character.isspace():
            x += metrics['advance']
            continue
        pristine, transform = geometry(source, rng)
        severity = severity_plan[(page_number, line, index)]
        scan, damage = degrade(pristine, severity, rng)
        origin = (round(x + metrics['bearing'][0]), round(baseline + metrics['bearing'][1]))
        box = (*origin, origin[0]+scan.width, origin[1]+scan.height)
        page.paste(ImageChops.darker(page.crop(box), scan), origin)
        opaque = digest(f"{face['split']}:{page_number}:{line}:{index}".encode())[:24]
        public = {'id': opaque, 'character': character, 'dpi': dpi,
                  'page': page_number, 'bbox': [*origin, origin[0]+scan.width, origin[1]+scan.height],
                  'baseline': baseline, 'nominal_height_px': point_size*dpi/72}
        truth = {'font_sha256': face['sha256'], 'face': face['name'], 'family': face['family'],
                 'character': character,
                 'split': face['split'], 'document': face['split'], 'line': line,
                 'word': sum(c.isspace() for c in text[:index]), 'point_size': point_size,
                 'severity': severity, 'transform': transform, 'metrics': metrics,
                 'master_id': digest((face['sha256'] + ':' + character).encode())}
        save_observation(root, scan, pristine, damage, public, truth)
        public_rows.append(public)
        truth_rows.append(truth)
        x += metrics['advance'] + float(rng.uniform(-.1, .3)) * dpi / 72
    return public_rows, truth_rows


def generate_document(root, faces, seed, dpis=DPIS):
    """One family-disjoint document with distant-page scan-condition changes."""
    root.mkdir(parents=True, exist_ok=False)
    (root / 'images').mkdir()
    (root / 'oracle').mkdir()
    rng = np.random.default_rng(seed)
    schedules = [page_schedule(len(faces), np.random.default_rng(seed + 17000 + i))
                 for i in range(len(dpis))]
    severity_plan = plan_damage(len(faces), schedules, seed + 31000)
    public, truth, pages = [], [], []
    for page_number, dpi in enumerate(dpis):
        page = Image.new('L', (6*dpi, 9*dpi), 255)
        for line, assignment in enumerate(schedules[page_number]):
            observations, labels = line_observations(root, page, faces, line, page_number, dpi, rng,
                                                    assignment, severity_plan)
            public.extend(observations)
            truth.extend(labels)
        # Inference sees crops of the actual composed scan, including neighbors.
        # Isolated authoring glyphs remain evaluator-only pristine oracles.
        for row in observations_on_page(public, page_number):
            image_path = root / row['image']
            page.crop(row['bbox']).save(image_path)
            row['image_sha256'] = digest(image_path.read_bytes())
        path = root / f'page-{page_number}.png'
        page.save(path, dpi=(dpi, dpi))
        pages.append({'path': path.name, 'dpi': dpi, 'sha256': digest(path.read_bytes())})
    write_jsonl(root / 'observations.jsonl', public)
    write_jsonl(root / 'oracle' / 'labels.jsonl', truth)
    write_scan_pdf(root, pages)
    manifest = {'schema': SCHEMA, 'seed': seed, 'faces': faces, 'pages': pages,
                'observations': len(public), 'dpi': list(dpis), 'oracle_not_for_inference': True,
                'tools': {'python': platform.python_version(), 'numpy': np.__version__,
                          'pillow': pillow_version, 'pikepdf': pikepdf.__version__},
                'damage_coverage': damage_coverage(truth)}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def write_scan_pdf(root, pages):
    """Lossless image-only fixture; six-by-nine-inch geometry at every DPI."""
    with pikepdf.new() as pdf:
        for source in pages:
            with Image.open(root / source['path']) as image:
                resource = pdf.make_stream(zlib.compress(image.tobytes()))
                resource.update(pikepdf.Dictionary(Type=pikepdf.Name.XObject,
                                Subtype=pikepdf.Name.Image, Width=image.width,
                                Height=image.height, BitsPerComponent=8,
                                ColorSpace=pikepdf.Name.DeviceGray, Filter=pikepdf.Name.FlateDecode))
            page = pdf.add_blank_page(page_size=(432, 648))
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=resource))
            page.Contents = pdf.make_stream(b'q 432 0 0 648 0 0 cm /Im0 Do Q\n')
        pdf.save(root / 'scan.pdf', deterministic_id=True)


def observations_on_page(rows, page_number):
    return (row for row in rows if row['page'] == page_number)


def page_schedule(face_count, rng):
    """Shuffle individual lines on every page; no fixed face-to-position label."""
    schedule = [(face, phrase) for face in range(face_count) for phrase in range(len(PHRASES))]
    rng.shuffle(schedule)
    return schedule


def assigned_face(primary, phrase_index, index, face_count):
    return (primary + index % 2) % face_count if phrase_index == 3 else primary


def plan_damage(face_count, schedules, seed):
    """Allocate then shuffle per-identity bands independently of geometry and DPI."""
    positions = {}
    for page, schedule in enumerate(schedules):
        for line, (primary, phrase_index) in enumerate(schedule):
            for index, character in enumerate(PHRASES[phrase_index]):
                if not character.isspace():
                    face = assigned_face(primary, phrase_index, index, face_count)
                    positions.setdefault((face, character), []).append((page, line, index))
    rng = np.random.default_rng(seed)
    plan = {}
    for locations in positions.values():
        count = len(locations)
        bands = np.arange(count) % 5
        if 1 < count < 5:
            bands[1:] = rng.choice(np.arange(1, 5), size=count-1, replace=False)
        rng.shuffle(bands)
        plan.update((location, int(band)) for location, band in zip(locations, bands))
    return plan


def damage_coverage(labels):
    """Every face-character must have clean and independently damaged witnesses."""
    bands = {}
    for row in labels:
        bands.setdefault((row['font_sha256'], row['character']), set()).add(row['severity'])
    incomplete = [list(key) for key, values in bands.items() if 0 not in values or len(values) < 2]
    return {'face_characters': len(bands), 'incomplete': sorted(incomplete)}


def document_record(manifest_path):
    root = manifest_path.parent
    data = json.loads(manifest_path.read_text())
    return {'split': root.name, 'manifest_sha256': digest(manifest_path.read_bytes()),
            'observations': data['observations'], 'faces': data['faces'], 'pages': data['pages'],
            'tools': data['tools'], 'scan_pdf_sha256': digest((root / 'scan.pdf').read_bytes()),
            'labels_sha256': digest((root / 'oracle' / 'labels.jsonl').read_bytes()),
            'public_records_sha256': digest((root / 'observations.jsonl').read_bytes())}


def verify_frozen_assets(faces, frozen):
    expected = {face['name']: (face['sha256'], face['notice_sha256'])
                for row in frozen['split_records'] for face in row['faces']}
    actual = {face['name']: (face['sha256'], face['notice_sha256']) for face in faces}
    if expected != actual:
        raise ValueError('Frozen font or licence-notice identity mismatch; do not replace evidence')


def verify_frozen_document(manifest_path, expected):
    if document_record(manifest_path) != expected:
        raise ValueError('Frozen document mismatch: ' + str(manifest_path))


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=10301)
    parser.add_argument('--verify-manifest', type=Path,
                        help='Strict frozen reproduction: verify fonts, notices, tools and all output hashes')
    args = parser.parse_args()
    faces = font_manifest(installed_faces())
    split_isolation(faces)
    frozen = json.loads(args.verify_manifest.read_text()) if args.verify_manifest else None
    if frozen:
        verify_frozen_assets(faces, frozen)
    args.out.mkdir(parents=True, exist_ok=False)
    for number, split in enumerate(('train', 'validation', 'test')):
        selected = [face for face in faces if face['split'] == split]
        manifest = generate_document(args.out / split, selected, args.seed + number)
        if manifest['damage_coverage']['incomplete']:
            raise ValueError('Incomplete clean/damaged coverage for face-character witnesses')
        if frozen:
            expected = next(row for row in frozen['split_records'] if row['split'] == split)
            verify_frozen_document(args.out / split / 'manifest.json', expected)


if __name__ == '__main__':
    main()
