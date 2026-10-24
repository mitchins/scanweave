"""All-visible-draw R2a measurements at original page geometry.

Each isolated page has one draw, preserving page rounding and preventing source
ownership overlap. Analytic coverage is the established grayscale 4x box average;
direct embedded-outline coverage supplies an independent renderer floor.
"""
import io
import json
import math
import multiprocessing
import os
from pathlib import Path
import sys

import numpy as np
import pikepdf
import pypdfium2 as pdfium
from fontTools.ttLib import TTFont

from qualification.font04.metrics import inspect, measure, sha
from qualification.font04.planner import local_source
from qualification.font04.prime_metrics import direct
from qualification.font04.r1_class_metrics import crop_render

CONTEXT = None


def load_snapshot(path):
    snapshot = json.loads(path.read_text())
    native = path.with_name('native-bindings.json')
    if native.exists():
        bindings = {(r['page'], r['occurrence']): r for r in json.loads(native.read_text())}
        for row in snapshot['rows']:
            row['_native_binding'] = bindings[row['page'], row['occurrence']]
    return snapshot


def bind(rows, inventory, geometry):
    """Bind by native f32 placement origin and label; require a bijection.

    Text-span emission can reorder occurrences. The union can also select a
    differently scaled program from an invisible owner, so pre-union scale is
    not authoritative. Origins plus labels must identify exactly one draw.
    The complete emitted matrices are independently equal in both arms.
    """
    result = []
    used = set()
    union_shapes = {}
    for row in rows:
        union_shapes.setdefault(row['shape_key'],row)
    for row in rows:
        g = geometry[row['page']]
        a, d = g['width_pt']/g['raster_width'], g['height_pt']/g['raster_height']
        x, y, xx, yy = row['bbox']
        f = np.float32
        shape = union_shapes[row['shape_key']]
        sx = f(f((xx-x)*a)*f(2048)/f(max(1, shape['ink_span'][0])))
        sy = f(f((yy-y)*d)*f(2048)/f(max(1, shape['ink_span'][1])))
        tx = f(f(a*x)-f(f(shape['anchor'][0])*sx)/f(2048))
        ty = f(f(g['height_pt']-d*yy)-f(f(shape['anchor'][1])*sy)/f(2048))
        expected = [sx, 0, 0, sy, tx, ty]
        native = row.get('_native_binding')
        matches = [(i, draw) for i, draw in enumerate(inventory['draws']) if i not in used and draw['page'] == row['page'] and draw['character'] == row['character'] and (
            draw['cid'] == native['cid'] and np.allclose(draw['matrix'], native['matrix'], rtol=1e-6, atol=1e-4)
            if native else np.allclose(draw['matrix'][4:], expected[4:], rtol=1e-6, atol=1e-4))]
        assert len(matches) == 1, ('ambiguous native placement', row['index'], len(matches), expected)
        i, draw = matches[0]
        used.add(i)
        result.append(draw)
    assert len(used) == len(rows) == len(inventory['draws'])
    return result


def isolate(default, candidate, snapshot, directory):
    rows = snapshot['rows']
    geometry = json.loads(Path(str(default)+'.json').read_text())['pages']
    inventory = [inspect(path) for path in (default, candidate)]
    bindings = [bind(rows, inv, geometry) for inv in inventory]
    assert len(rows) == len(inventory[0]['draws']) == len(inventory[1]['draws'])
    for row, old, new in zip(rows, *bindings):
        assert row['character'] == old['character'] == new['character']
        assert (old['page'], old['cid'], old['matrix']) == (new['page'], new['cid'], new['matrix'])
    for name, path, draws in [('default', default, bindings[0]), ('candidate', candidate, bindings[1]), ('source', default, None)]:
        with pikepdf.open(path) as original:
            pdf = pikepdf.Pdf.new()
            for i, row in enumerate(rows):
                pdf.pages.append(original.pages[row['page']])
                page = pdf.pages[-1]
                if draws is not None:
                    draw = draws[i]
                    commands = 'BT 0 Tr 0 g '+draw['font']+' 1 Tf '+' '.join(map(str, draw['matrix']))+f" Tm <{draw['cid']:04x}> Tj ET\n"
                else:
                    commands = ''
                    source = row['source']
                    if source is not None:
                        try:
                            coverage = local_source(source, row['paper'])
                        except ValueError as exc:
                            row['unscored_reason'] = str(exc)
                        else:
                            pixels = np.rint((1-coverage)*255).astype('uint8')
                            h, w = pixels.shape
                            g = geometry[row['page']]
                            sx, sy = g['width_pt']/g['raster_width'], g['height_pt']/g['raster_height']
                            x, y = source['bbox'][:2]
                            image = pdf.make_stream(pixels.tobytes())
                            image.Type = pikepdf.Name.XObject
                            image.Subtype = pikepdf.Name.Image
                            image.Width, image.Height = w, h
                            image.ColorSpace = pikepdf.Name.DeviceGray
                            image.BitsPerComponent = 8
                            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image))
                            commands = f'q {w*sx:.12f} 0 0 {h*sy:.12f} {(x-2)*sx:.12f} {g["height_pt"]-(y-2+h)*sy:.12f} cm /I Do Q\n'
                    else:
                        row['unscored_reason'] = 'no_safe_owned_source'
                page.Contents = pdf.make_stream(commands.encode())
            pdf.save(directory/f'isolated-{name}.pdf', deterministic_id=True)
    return bindings


def init_worker(directory, rows, bindings, accepted, default, candidate):
    global CONTEXT
    directory = Path(directory)
    docs = {name: pdfium.PdfDocument(directory/f'isolated-{name}.pdf') for name in ('source', 'default', 'candidate')}
    fonts = {}
    for name, path in [('default', default), ('candidate', candidate)]:
        with pikepdf.open(path) as pdf:
            fonts[name] = TTFont(io.BytesIO(next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()))
    CONTEXT = directory, rows, bindings, accepted, docs, fonts


def score(i):
    directory, rows, bindings, accepted, docs, fonts = CONTEXT
    row = rows[i]
    if 'unscored_reason' in row:
        return [], []
    x, y, xx, yy = map(int, row['source']['bbox'])
    bounds = [max(0, x-4), max(0, y-4), min(math.ceil(row['page_width']*300/72), xx+4), min(math.ceil(row['page_height']*300/72), yy+4)]
    arrays = {}
    records = []
    for engine in ('analytic', 'pdfium', 'poppler'):
        arrays[engine] = {name: crop_render(directory/f'isolated-{name}.pdf', doc, i, bounds, engine) for name, doc in docs.items()}
    arrays['direct'] = {name: direct(fonts[name], bindings[k][i], bounds, row['page_height']) for k, name in enumerate(('default', 'candidate'))}
    arrays['direct']['source'] = arrays['analytic']['source']
    for engine, values in arrays.items():
        records.append(dict(draw=i, page=row['page'], occurrence=row['occurrence'], character=row['character'], metric=engine, substituted=i in accepted,
                            default=measure(values['source'], values['default']), candidate=measure(values['source'], values['candidate'])))
    floors = [dict(draw=i, metric=engine, substituted=i in accepted, analytic_reference=measure(arrays['analytic']['default'], arrays[engine]['default']),
                   direct_reference=measure(arrays['direct']['default'], arrays[engine]['default'])) for engine in ('analytic', 'pdfium', 'poppler')]
    return records, floors


def distribution(rows, value, lower_is_worse=False):
    ordered = sorted(rows, key=value, reverse=not lower_is_worse)
    values = [value(row) for row in rows]
    return dict(n=len(rows), mean=float(np.mean(values)) if values else None, p95=float(np.quantile(values, .95)) if values else None,
                worst10=[dict(draw=row['draw'], value=value(row)) for row in ordered[:10]])


def summaries(records, floors):
    result = {}
    for metric in ('analytic', 'direct', 'pdfium', 'poppler'):
        result[metric] = {}
        for subset in ('all', 'substituted'):
            selected = [r for r in records if r['metric'] == metric and (subset == 'all' or r['substituted'])]
            item = {arm: {key: distribution(selected, lambda r, a=arm, k=key: abs(r[a][k]) if k == 'area_bias' else r[a][k], lower_is_worse=key=='iou') for key in ('error', 'iou', 'contour_distance', 'area_bias')} for arm in ('default', 'candidate')}
            item['error_delta'] = distribution(selected, lambda r: r['candidate']['error']-r['default']['error'])
            selected_floors = [r for r in floors if r['metric'] == metric and (subset == 'all' or r['substituted'])]
            references = sorted({k for r in selected_floors for k in r if k.endswith('_reference')})
            item['floor'] = {reference: distribution(selected_floors, lambda r, ref=reference: r[ref]['error']) for reference in references}
            result[metric][subset] = item
    return result


def main(default, candidate, source, directory):
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = load_snapshot(source)
    bindings = isolate(default, candidate, snapshot, directory)
    rows = snapshot['rows']
    report = json.loads(Path(str(candidate)+'.json').read_text())['conversion']['glyph_sharing']
    by_occurrence = {(r['page'], r['occurrence']): i for i, r in enumerate(rows)}
    accepted = {by_occurrence[d['page'], next(r['occurrence'] for r in rows if r['page'] == d['page'] and r['id'] == d['id'])] for d in report['decisions'] if d['accepted']}
    records, floors = [], []
    with multiprocessing.get_context('spawn').Pool(int(os.environ.get('FONT04_METRIC_WORKERS', '8')), initializer=init_worker,
            initargs=(str(directory), rows, bindings, accepted, str(default), str(candidate))) as pool:
        for i, (rr, ff) in enumerate(pool.imap(score, range(len(rows)), chunksize=4)):
            records.extend(rr)
            floors.extend(ff)
            if i % 100 == 0:
                print(candidate.name, i, len(rows), flush=True)
    result = dict(default_sha256=sha(default), candidate_sha256=sha(candidate), source_sha256=sha(source), visible_draws=len(rows), substituted=len(accepted),
                  unscored_draws=[dict(draw=i, page=r['page'], occurrence=r['occurrence'], reason=r['unscored_reason']) for i, r in enumerate(rows) if 'unscored_reason' in r],
                  summary=summaries(records, floors), records=records, floors=floors)
    (directory/'metrics.json').write_text(json.dumps(result, indent=2)+'\n')
    (directory/'summary.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('records', 'floors')}, indent=2)+'\n')


if __name__ == '__main__':
    main(*map(Path, sys.argv[1:]))
