"""Bind converter-only inputs, independent oracles, frozen outputs and tools."""
import json,hashlib,subprocess,sys,platform
from pathlib import Path
import numpy,PIL,pikepdf,pypdfium2
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
rows=[]
for dpi in [300,600]:
 fix=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}';bundle=json.loads((fix/'input/document.json').read_text());inputs=[]
 for p in sorted((fix/'input').glob('*')):
  if p.is_file():inputs.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
 oracles=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in sorted((fix/'oracle').glob('*')) if p.is_file()]
 arms=[]
 for a in ['adobe','previous','final']:
  p=B/str(dpi)/(a+'.pdf');metrics=json.loads((B/str(dpi)/a/'metrics.json').read_text());assert sha(p)==metrics['sha256'];arms.append({'arm':a,'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p),'pages':len(pikepdf.open(p).pages)})
 for a,old in [('adobe',ROOT/f'qualification/clearscan_competitive/{dpi}/adobe.pdf'),('previous',ROOT/f'qualification/clearscan_typography/{dpi}/final.pdf')]:assert sha(B/str(dpi)/(a+'.pdf'))==sha(old)
 rows.append({'dpi':dpi,'normal_converter_command':['target/release/scanweave-cli','build','--bundle',str((fix/'input/document.json').relative_to(ROOT)),'--profile','clearscan','--output',str((B/str(dpi)/'final.pdf').relative_to(ROOT)),'--report',str((B/str(dpi)/'final.json').relative_to(ROOT))],'converter_inputs':inputs,'evaluator_only_oracles':oracles,'arms':arms})
sources={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'crates/scanweave-io/src').glob('*.rs')};result={'starting_head':'4bff4821b1e409fe632536ba4bd2166795dee284','implementation_head':git('rev-parse','HEAD'),'implementation_commits':[git('rev-parse','89b6078'),git('rev-parse','da9a2d8'),git('rev-parse','ac977ff')],'source_sha256':sources,'tools':{'python':sys.version,'numpy':numpy.__version__,'pillow':PIL.__version__,'pikepdf':pikepdf.__version__,'pdfium':str(pypdfium2.PDFIUM_INFO),'poppler':subprocess.run(['pdftoppm','-v'],text=True,capture_output=True).stderr.splitlines()[0],'rustc':subprocess.check_output(['rustc','--version'],text=True).strip()},'frozen_adobe_run_manifest':{'path':'qualification/clearscan_competitive/run-manifest.json','sha256':sha(ROOT/'qualification/clearscan_competitive/run-manifest.json')},'documents':rows,'determinism_300':{'equal':(B/'300/final.pdf').read_bytes()==(B/'300/repeat.pdf').read_bytes(),'sha256':sha(B/'300/repeat.pdf')},'no_pristine_inference_dependency':True}
(B/'run-manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
