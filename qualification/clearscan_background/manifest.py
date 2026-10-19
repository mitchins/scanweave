"""Bind runtime source, unchanged scan inputs, oracles and measured outputs."""
import json,hashlib,subprocess,sys
from pathlib import Path
import numpy,PIL,pikepdf,pypdfium2
B=Path(__file__).resolve().parent;R=B.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)}
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
inputs=[];oracles=[];outputs=[]
for dpi in [300,600]:
 fix=R/f'qualification/experiments/m1g/fixture/dpi{dpi}'
 inputs.extend(row(p) for p in (fix/'input').iterdir() if p.is_file());oracles.extend(row(p) for p in (fix/'oracle').iterdir() if p.is_file())
 for arm in ['previous','final','adobe']:outputs.append(row(B/str(dpi)/(arm+'.pdf')))
 for name in ['final.json','final/metrics.json','final/audit.json','final/stages/stage-errors.json']:
  outputs.append(row(B/str(dpi)/name))
 for arm,old in [('previous','final'),('adobe','adobe')]:assert sha(B/str(dpi)/(arm+'.pdf'))==sha(R/f'qualification/clearscan_contours/{dpi}/{old}.pdf')
for name in ['cord-02','history-01']:
 inputs.extend(row(R/'qualification/clearscan_competitive/real'/(name+s)) for s in ['.png','.regions.hocr']);outputs.append(row(B/'real/final'/(name+'.pdf')))
result={'starting_head':json.loads((B/'starting-state.json').read_text())['head'],'requested_start':'ac977ff8f60ce965f64353cff0affb818e4d2a01','implementation_head':git('rev-parse','HEAD'),'implementation_commits':[git('rev-parse',c) for c in ['a79dc87','ca9a5e8','732ce82','5042c03']],'source_sha256':{str(p.relative_to(R)):sha(p) for p in (R/'crates/scanweave-io/src').glob('*.rs')},'converter_inputs':inputs,'evaluator_only_oracles':oracles,'outputs':outputs,'tools':{'python':sys.version,'numpy':numpy.__version__,'pillow':PIL.__version__,'pikepdf':pikepdf.__version__,'pdfium':str(pypdfium2.PDFIUM_INFO),'poppler':subprocess.run(['pdftoppm','-v'],capture_output=True,text=True).stderr.splitlines()[0]},'determinism_300':{'equal':(B/'300/repeat.pdf').exists() and (B/'300/repeat.pdf').read_bytes()==(B/'300/final.pdf').read_bytes()},'oracle_source_replay':'pixel-identical assertion in oracle.py; same random draws and original degradation, text absent only in evaluator counterfactual'}
(B/'run-manifest.json').write_text(json.dumps(result,indent=2))
