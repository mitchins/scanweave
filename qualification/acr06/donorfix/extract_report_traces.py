#!/usr/bin/env python3
"""Extract report-only geometry for the issue's examples; page indexes are zero-based."""
import json
from pathlib import Path
base = Path('/data/coding/scanweave/qualification/acr06/local/donorfix/baseline')
targets = {'single': {0: ['w000053', 'w000102', 'w000130', 'w000175', 'w000180']}, 'forms': {1: ['w000471']}, 'historical': {1: ['w000070', 'w000106']}, 'financial': {8: ['w000005']}}
result = []
for doc, pages in targets.items():
    path = base / ('single.pdf.json' if doc == 'single' else doc + '-off.pdf.json')
    if not path.exists():
        continue
    report = json.loads(path.read_text())
    for page, prefixes in pages.items():
        rec = report['conversion']['page_reports'][page]['reconstruction']
        observations = {o['symbol_id']: o for o in rec['observations']}
        geometry = {g['prototype_id']: g for g in rec['canonical_geometry']}
        prototypes = {p['prototype_id']: p for p in rec['prototypes']}
        for o in rec['occurrences']:
            if not any(o['symbol_id'].startswith(p) for p in prefixes):
                continue
            g = geometry.get(o.get('prototype_id'), {})
            result.append({'document': doc, 'page_index': page, 'observation': observations.get(o['symbol_id']), 'occurrence': o, 'prototype': prototypes.get(o.get('prototype_id')), 'donor_geometry': {k:g.get(k) for k in ('witness_symbol_id','witness_bbox_px','width','height','anchor_bbox_fu','ink_span_fu')}})
Path('/data/coding/scanweave/qualification/acr06/donorfix/report-traces.json').write_text(json.dumps(result, indent=2)+'\n')
