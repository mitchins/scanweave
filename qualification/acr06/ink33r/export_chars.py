#!/usr/bin/env python3
"""Copy the full per-character measurement chunks to evidence with hashes."""
from pathlib import Path
import json,hashlib,shutil
r=Path('/data/coding/scanweave/qualification/acr06');src=r/'local/ink33r/raw-chars';dest=r/'ink33r/characters';dest.mkdir(exist_ok=True);rows=[]
for p in sorted(src.glob('*.json')):
 q=dest/p.name;shutil.copyfile(p,q);rows.append({'file':'characters/'+p.name,'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'records':len(json.loads(q.read_text()))})
(r/'ink33r/character-index.json').write_text(json.dumps(rows,indent=2)+'\n')
