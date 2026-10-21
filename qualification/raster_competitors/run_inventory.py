"""Audit the frozen development corpus only; never search other corpora."""
import csv
import json
from pathlib import Path
from inspect_pdf import digest, inspect

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PACK = ROOT/'qualification/pdf_packaging'
TONAL = ROOT/'qualification/tonal_raster'


def main():
    groups = json.loads((PACK/'groups.json').read_text())
    manifests = [(PACK/'run-manifest.json', 'artifacts'), (TONAL/'run-manifest.json', 'files')]
    checks = []
    for manifest, key in manifests:
        for item in json.loads(manifest.read_text())[key]:
            path = ROOT/item['path']
            if not path.exists():
                if path.suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff'):
                    raise FileNotFoundError('Required frozen artifact missing: '+str(path))
                checks.append({'path': item['path'], 'status': 'MISSING_OPTIONAL_TOOL_OR_LOG'})
                continue
            actual = digest(path.read_bytes())
            if actual != item['sha256'] and path.suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff'):
                raise ValueError('Frozen artifact mismatch: '+str(path))
            checks.append({'path': item['path'], 'status': 'MATCH' if actual == item['sha256'] else 'MUTABLE_TOOL_CHANGED', 'expected_sha256': item['sha256'], 'sha256': actual})
    (BASE/'provenance.json').write_text(json.dumps(checks, indent=2)+'\n')
    documents = []
    accounting = []
    for collection, group in groups.items():
        for arm in ('input', 'adobe', 'ocrmypdf1', 'ocrmypdf3', 'archive', 'scanweave'):
            path = (TONAL/'collections'/f'{collection}.pdf' if arm == 'scanweave'
                    else PACK/'groups'/f'{collection}-{arm}.pdf')
            print(collection, arm, flush=True)
            record = inspect(path)
            assert len(record['pages']) == len(group['members'])
            record.update(collection=collection, arm=arm, members=group['members'])
            documents.append(record)
            accounting.append({'collection': collection, 'arm': arm, 'pdf_bytes':record['pdf_bytes'],
                               **record['encoded_stream_bytes'],
                               'serialized_residual_bytes':record['serialized_residual_bytes']})
    (BASE/'object-inventory.json').write_text(json.dumps(documents, separators=(',', ':'))+'\n')
    with (BASE/'gap-accounting.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(accounting[0]))
        writer.writeheader()
        writer.writerows(accounting)


if __name__ == '__main__':
    main()
