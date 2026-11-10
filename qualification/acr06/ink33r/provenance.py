#!/usr/bin/env python3
"""Hash all frozen corpus inputs, corrected PDFs and prior baseline."""
import hashlib,json,pathlib
R=pathlib.Path('/data/coding/scanweave/qualification');E=R/'acr06/ink33r';O=R/'acr06/local/ink33r';P=R/'pdf_packaging/groups'; out={'main_commit':'ab7dfba96561595e7c587d8033954ed1ec235a20','build':'cargo build --release --locked -p scanweave-cli','conversion':'--dpi 300 --profile clearscan --glyph-sharing off','documents':{}}
expected=json.loads((R/'acr06/ink37c/cprime/bytes.json').read_text())['documents'];ex={a['document']:a['sha256'][3] for a in expected}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for d in ('historical','financial','mixed','receipts','forms'):
 p=O/f'{d}.pdf';old=R/('acr06/local/ink33/forms-main.pdf' if d=='forms' else f'acr06/local/bg150/baseline/{d}.pdf');h=digest(p);out['documents'][d]={'corrected_sha256':h,'reference_cprime_sha256':ex[d],'matches_reference':h==ex[d],'old_main_sha256':digest(old),'source_sha256':digest(P/f'{d}-input.pdf'),'adobe_sha256':digest(P/f'{d}-adobe.pdf'),'corrected_size':p.stat().st_size}
(E/'provenance.json').write_text(json.dumps(out,indent=2)+'\n')
if not all(x['matches_reference'] for x in out['documents'].values()):raise SystemExit('candidate hash mismatch')
