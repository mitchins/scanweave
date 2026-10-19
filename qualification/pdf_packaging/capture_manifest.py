import json,subprocess,hashlib,importlib.metadata,os
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[1]
def command(args):
 p=subprocess.run(args,capture_output=True,text=True);return {'command':args,'status':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[R/'target/release/scanweave',R/'adobe-acrobat-sandbox/clearscan.sh']+list((B/'300').glob('final.pdf'))+list((B/'600').glob('final.pdf'))
files+=list((B/'groups').glob('*.pdf'))+list((B/'real').glob('adobe-*.pdf'))
files+=list((B/'real/input').glob('*.pdf'))+list((B/'real').glob('*/*.pdf'))
manifest={'implementation_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'baseline':'b2ec997e5cce5923da2ad050fc289a5e731d7dce','commands':[command(a) for a in [['rustc','--version'],['pdftoppm','-v'],['pdfinfo','-v'],['tesseract','--version'],['tesseract','--list-langs'],['wine','--version']]],'python_packages':{n:importlib.metadata.version(n) for n in ['pikepdf','pypdfium2','ocrmypdf','archive-pdf-tools','Pillow','numpy']},'artifacts':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(files)) if p.exists()]}
(B/'run-manifest.json').write_text(json.dumps(manifest,indent=2))
