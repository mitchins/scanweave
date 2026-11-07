#!/usr/bin/env python3
"""Apply the CP3 page-stream accounting to every completed arm."""
import importlib.util,json
from pathlib import Path
q=Path('/data/coding/scanweave/qualification'); e=q/'acr06/bg150'; root=q/'acr06/local/bg150'
spec=importlib.util.spec_from_file_location('cp3_bytes',q/'acr06/cp3/bytes.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
groups=['financial','forms','historical','mixed','receipts']; docs=groups+['single','competitive300','competitive600','fresh1','fresh2','freshtruth1','freshtruth2']; result={}
for name in docs:
 paths={'default':root/'baseline'/f'{name}.pdf','candidate':root/'candidate'/f'{name}.pdf'}
 if name in groups: paths.update(adobe=q/f'pdf_packaging/groups/{name}-adobe.pdf',archive=q/f'pdf_packaging/groups/{name}-archive.pdf',unguarded=root/'unguarded'/f'{name}.pdf')
 result[name]={}
 for arm,path in paths.items():
  result[name][arm]=mod.analyse(path)
  print(name,arm,flush=True)
 (e/'bytes.json').write_text(json.dumps(result,indent=2)+'\n')
