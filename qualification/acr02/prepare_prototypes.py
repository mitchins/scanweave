"""Create an explicitly named four-page prototype document, not a hidden page split."""
import hashlib
import json
from pathlib import Path

import pikepdf

ROOT = Path('qualification/acr02/local')
INDICES = [6, 16, 24, 28]
with pikepdf.open(ROOT / 'controlled-input.pdf') as source:
    pdf = pikepdf.new()
    for index in INDICES:
        pdf.pages.append(source.pages[index])
    pdf.save(ROOT / 'prototype-input.pdf', deterministic_id=True,
             object_stream_mode=pikepdf.ObjectStreamMode.generate)
(ROOT / 'prototype-membership.json').write_text(json.dumps({
    'purpose': 'Four-page prototype document; all pages converted together. Adobe anatomy remains full36page run. Real development collections are not split for conversion.',
    'controlled_indices': INDICES,
    'sha256': hashlib.sha256((ROOT / 'prototype-input.pdf').read_bytes()).hexdigest(),
}, indent=2) + '\n')
