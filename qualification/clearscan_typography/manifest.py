"""Hash-bound inputs, frozen competitor reference, final product and tests."""
from pathlib import Path
import hashlib,json,subprocess,sys,platform
import numpy,PIL,pikepdf,pypdfium2,fontTools
from PIL import Image

DOCUMENT_JSON = 'document.json'

B=Path(__file__).resolve().parent;ROOT=B.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def cmd(xs):return subprocess.check_output(xs,cwd=ROOT,text=True,stderr=subprocess.STDOUT).strip()
old=json.loads((ROOT/'qualification/clearscan_competitive/run-manifest.json').read_text());reference=[];inputs=[]
for dpi in [300,600]:
 path=ROOT/f'qualification/clearscan_competitive/{dpi}/adobe.pdf';expected=next(x for x in old['artifacts'] if x['path']==str(path.relative_to(ROOT)))['sha256'];copy=B/str(dpi)/'adobe.pdf';assert sha(path)==sha(copy)==expected
 reference.append({'dpi':dpi,'frozen_sha256':expected,'verified_original':rec(path),'verified_copy':rec(copy)})
 base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input';m=json.loads((base/DOCUMENT_JSON).read_text());sources={s['source_id']:s for s in m['sources']};pages=[]
 assert sha(base/DOCUMENT_JSON)==old['documents'][str(dpi)]['manifest']['sha256']
 for page_index,page in enumerate(m['pages']):
  p=base/sources[page['source_id']]['asset_path'];im=Image.open(p).convert('RGB');frozen=old['documents'][str(dpi)]['pages'][page_index];assert sha(p)==frozen['source']['sha256'];assert hashlib.sha256(im.convert('L').tobytes()).hexdigest()==frozen['sample_sha256'];samples=numpy.asarray(im);assert numpy.all(samples[:,:,0]==samples[:,:,1]) and numpy.all(samples[:,:,1]==samples[:,:,2]);pages.append({'image':rec(p),'decoded_rgb_sha256':hashlib.sha256(im.tobytes()).hexdigest(),'frozen_luma_sha256':frozen['sample_sha256'],'every_pixel_rgb_equal':True,'pixels':list(im.size),'ocr':rec(base/page['ocr_page_path']),'page_manifest':page})
 inputs.append({'dpi':dpi,'manifest':rec(base/DOCUMENT_JSON),'last_fixture_commit':cmd(['git','log','-1','--format=%H','--',str(base.relative_to(ROOT))]),'pages':pages})
artifacts=[rec(p) for dpi in [300,600] for p in [B/str(dpi)/'final.pdf',B/str(dpi)/'final.json',B/str(dpi)/'final/metrics.json']]
artifacts += [rec(p) for p in sorted((B/'real/final').glob('*.pdf'))]
code=[rec(ROOT/f) for f in cmd(['git','ls-files','crates/scanweave-io/src']).splitlines() if f.endswith('.rs')]
real=[]
for p in sorted((ROOT/'qualification/clearscan_competitive/real').glob('*.regions.hocr')):
 image=p.with_name(p.name.replace('.regions.hocr','.png'));real.append({'image':rec(image),'ocr':rec(p)})
commands=[]
for dpi in [300,600]:
 output=B/str(dpi)/('owner-em.pdf' if dpi==300 else 'final.pdf');commands.append(['target/release/scanweave-cli','build','--bundle',f'qualification/experiments/m1g/fixture/dpi{dpi}/input/document.json','--profile','clearscan','--output',str(output.relative_to(ROOT)),'--report',str(output.with_suffix('.json').relative_to(ROOT))])
manifest={'starting_head':'903580f4911ce0ca15377781b70f2acedc960a99','implementation_head':cmd(['git','rev-parse','HEAD']),'relationship_to_08431a7':'ancestor, verified at start','tracked_worktree':cmd(['git','status','--porcelain','--untracked-files=no']),'code':code,'cli_sha256':sha(ROOT/'target/release/scanweave-cli'),'cargo_lock':rec(ROOT/'Cargo.lock'),'fixture_inputs':inputs,'frozen_reference':reference,'reference_engine':old['tools']['adobe'],'reference_wine':old['tools']['wine'],'frozen_reference_manifest':rec(ROOT/'qualification/clearscan_competitive/run-manifest.json'),'real_inputs':real,'real_attribution':'qualification/clearscan_competitive/real/ATTRIBUTION.md','converter_commands':commands,'300_artifact_copy':'owner-em.pdf/json copied byte-exact to final.pdf/json; ordinary repeat.pdf verifies same output with final code','measurement_commands':'qualification/clearscan_typography/README.md and run.py','artifacts':artifacts,'tools':{'rust':cmd(['rustc','--version']),'cargo':cmd(['cargo','--version']),'python':sys.version,'numpy':numpy.__version__,'pillow':PIL.__version__,'pikepdf':pikepdf.__version__,'pdfium':pypdfium2.PDFIUM_INFO.version,'fonttools':fontTools.__version__,'poppler':cmd(['pdftoppm','-v'])},'determinism':(B/'determinism.txt').read_text(),'scope':'Normal ClearScan path; evaluator-only pristine references; no sealed holdout. Unrelated files preserved.'}
(B/'run-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print('Frozen Adobe hashes and 16 source pages verified; implementation',manifest['implementation_head'])
