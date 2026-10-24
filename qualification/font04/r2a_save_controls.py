"""Matched save-only controls for the explicit development corpus."""
import json
from pathlib import Path

import pikepdf

from qualification.font04.metrics import sha
from qualification.font04.r2a_audit import audit


def main():
    root = Path('qualification/font04/local/R2a')
    directory = root / 'save-controls'
    directory.mkdir(exist_ok=True)
    result = {}
    for group in ('forms', 'receipts', 'mixed', 'historical', 'financial'):
        default = root / f'baseline/{group}-off.pdf'
        candidate = root / f'baseline/{group}-cover-2.0.pdf'
        control = directory / f'{group}-save-only.pdf'
        with pikepdf.open(default) as pdf:
            pdf.save(control, deterministic_id=True,
                     object_stream_mode=pikepdf.ObjectStreamMode.generate)
        transport = audit(default, control, directory / group)
        result[group] = dict(
            default_bytes=default.stat().st_size,
            sharing_bytes=candidate.stat().st_size,
            save_only_bytes=control.stat().st_size,
            save_only_sha256=sha(control),
            sharing_saving_vs_default=default.stat().st_size-candidate.stat().st_size,
            sharing_saving_vs_save_only=control.stat().st_size-candidate.stat().st_size,
            save_only_transport=transport,
        )
    output = dict(schema='font04-R2a-save-controls-v1',
                  serialization='pikepdf deterministic_id=True, object streams generate; no content edits',
                  documents=result)
    output['totals'] = {key: sum(row[key] for row in result.values()) for key in (
        'default_bytes', 'sharing_bytes', 'save_only_bytes',
        'sharing_saving_vs_default', 'sharing_saving_vs_save_only')}
    Path('qualification/font04/r2a-save-controls.json').write_text(json.dumps(output, indent=2)+'\n')


if __name__ == '__main__':
    main()
