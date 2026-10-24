"""Complete-page source-relative fidelity crops for every visible corpus draw.

This complements isolated owned-source scores, whose safe-source denominator is
smaller. Contextual scores include raster, neighbours and paper in every arm.
"""
import json
from pathlib import Path
import sys
import numpy as np

from qualification.font04.metrics import render, measure, sha
from qualification.font04.prime_metrics import analytic
from qualification.font04.r2a_metrics import summaries


def main(source, default, candidate, snapshot, destination):
    rows = json.loads(snapshot.read_text())['rows']
    geometry = json.loads(Path(str(default)+'.json').read_text())['pages']
    decisions = json.loads(Path(str(candidate)+'.json').read_text())['conversion']['glyph_sharing']['decisions']
    accepted = {(r['page'], r['id']) for r in decisions if r['accepted']}
    records, floors = [], []
    destination.mkdir(parents=True, exist_ok=True)
    for pi, g in enumerate(geometry):
        images = {}
        for engine in ('analytic', 'pdfium', 'poppler'):
            images[engine] = {}
            for arm, path in [('source', source), ('default', default), ('candidate', candidate)]:
                images[engine][arm] = 1-(analytic(path, pi) if engine == 'analytic' else render(path, pi, 300, engine)).astype(float)/255
        for i, row in enumerate(rows):
            if row['page'] != pi:
                continue
            x, y, xx, yy = row['bbox']
            sx, sy = g['width_pt']/g['raster_width']*300/72, g['height_pt']/g['raster_height']*300/72
            x, y = max(0, int(x*sx)-4), max(0, int(y*sy)-4)
            xx = min(min(a.shape[1] for arms in images.values() for a in arms.values()), int(np.ceil(xx*sx))+4)
            yy = min(min(a.shape[0] for arms in images.values() for a in arms.values()), int(np.ceil(yy*sy))+4)
            arrays = {engine: {arm: pixels[y:yy,x:xx] for arm,pixels in arms.items()} for engine,arms in images.items()}
            for engine, arms in arrays.items():
                records.append(dict(draw=i, page=pi, occurrence=row['occurrence'], character=row['character'], metric=engine, substituted=(pi,row['id']) in accepted,
                                    default=measure(arms['source'], arms['default']), candidate=measure(arms['source'], arms['candidate'])))
                floors.append(dict(draw=i, metric=engine, substituted=(pi,row['id']) in accepted,
                                   analytic_reference=measure(arrays['analytic']['default'],arms['default']),
                                   alternate_renderer_reference=measure(arrays['poppler' if engine == 'analytic' else 'analytic']['default'],arms['default'])))
        print(candidate.name, 'complete-context page', pi+1, len(geometry), flush=True)
    result = dict(source_sha256=sha(source), default_sha256=sha(default), candidate_sha256=sha(candidate), snapshot_sha256=sha(snapshot),
                  visible_draws=len(rows), substituted=len(accepted), unscored_draws=[],
                  measurement='Complete original pages, source-relative native placement crops padded 4px; every visible draw. Includes raster/paper/neighbour context. Analytic=4x grayscale box average. Alternate renderer is Poppler for analytic and analytic for the other engines.',
                  summary=summaries(records,floors), records=records, floors=floors)
    assert sum(r['metric']=='analytic' for r in records)==len(rows)
    (destination/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    (destination/'summary.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('records','floors')},indent=2)+'\n')


if __name__ == '__main__':
    main(*map(Path,sys.argv[1:]))
