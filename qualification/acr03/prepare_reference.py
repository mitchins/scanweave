"""Export exact read-only research helpers; never merge a research branch."""
import hashlib
import json
import subprocess
from pathlib import Path

REVISIONS = (
    ('38cc218f8f1e50e56679fd12d5d72c1d4a44a697', 'qualification/acr02',
     Path('qualification/acr03/local/reference/qualification/acr02'),
     ('anatomy.py', 'fixtures.py', 'prepare_prototypes.py')),
    ('ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e', 'qualification/raster_competitors',
     Path('qualification/residual_resolution/local/qualification/raster_competitors'),
     ('inspect_pdf.py', 'render_compare.py')),
)


def main():
    rows=[]
    for revision, directory, destination, files in REVISIONS:
        destination.mkdir(parents=True, exist_ok=True)
        for name in files:
            data=subprocess.run(['git','show',f'{revision}:{directory}/{name}'],check=True,capture_output=True).stdout
            path=destination/name
            path.write_bytes(data)
            rows.append({'revision':revision,'path':str(path),'sha256':hashlib.sha256(data).hexdigest()})
    Path('qualification/acr03/local/reference-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':main()
