#!/usr/bin/env python3
import hashlib,json,pathlib,sys,importlib.metadata,subprocess
R=pathlib.Path('/data/coding/scanweave'); E=R/'qualification/acr06/ink33'; O=R/'qualification/acr06/local/ink33'; B=R/'qualification/acr06/local/bg150/baseline'; P=R/'qualification/pdf_packaging/groups'; G=['historical','financial','mixed','receipts','forms']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'main_commit':'9655fccc1b9e2ce479dd95d06b5f48ea2bfc0e6d','dpi':300,'profile':'clearscan','glyph_sharing':'off','files':{},'packages':{x:importlib.metadata.version(x) for x in ['pikepdf','pypdfium2','numpy','scipy','scikit-image','Pillow']}}
for g in G:
 out['files'][g]={}
 for name,path in [('source',P/f'{g}-input.pdf'),('adobe',P/f'{g}-adobe.pdf'),('archive_reference',P/f'{g}-archive.pdf'),('old_baseline',B/f'{g}.pdf'),('fresh_main',O/f'{g}-main.pdf')]+[(f'cf-{m}',O/f'{g}-cf-{m}.pdf') for m in 'abc']:
  out['files'][g][name]={'path':str(path),'sha256':digest(path)}
 out['files'][g]['selected_scanweave']=out['files'][g]['fresh_main' if g=='forms' else 'old_baseline']
(E/'provenance.json').write_text(json.dumps(out,indent=2)+'\n')
