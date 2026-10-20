"""Bind final delivered artifacts to code, tools and original decoded samples."""
import hashlib,json,subprocess,sys,platform
from pathlib import Path
import pikepdf,pypdfium2,PIL,numpy,fontTools
from PIL import Image
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(c):
 r=subprocess.run(c,capture_output=True,text=True);return (r.stdout+r.stderr).strip()
def file(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
result={'starting_head':'c20a8a91c1109c31bbf7cfdc5ff1b562f5f05986','implementation_head':'08431a7','exact_head_before_evidence_commit':command(['git','rev-parse','HEAD']),'unrelated_material':'Untracked sandbox, prior competitor/experimental research and user root mission files preserved. Prior tracked donor evidence restored after inherited regression reproduction. No sealed holdout access.','tools':{'rust':command(['rustc','--version']),'cargo':command(['cargo','--version']),'python':sys.version,'numpy':numpy.__version__,'pillow':PIL.__version__,'pikepdf':pikepdf.__version__,'pdfium':str(pypdfium2.PDFIUM_INFO),'fonttools':fontTools.__version__,'poppler':command(['pdftoppm','-v']),'tesseract':command(['tesseract','--version']),'wine':command(['wine','--version']),'adobe':'Acrobat XI Pro11.0.20 Paper Capture; English(US), ClearScan, Downsample To600dpi; actual reduced backgrounds150dpi'},'documents':{},'artifacts':[]}
for dpi in (300,600):
 base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input';m=json.loads((base/'document.json').read_text());sources={s['source_id']:s for s in m['sources']};pdf=pikepdf.open(B/str(dpi)/'source.pdf');checks=[]
 for i,page in enumerate(m['pages']):
  image=base/sources[page['source_id']]['asset_path'];src=Image.open(image).convert('L');p=pdf.pages[i];ims=list(p.Resources.XObject.values());decoded=pikepdf.PdfImage(ims[0]).as_pil_image().convert('L');checks.append({'page':i,'source':file(image),'sample_sha256':hashlib.sha256(src.tobytes()).hexdigest(),'decoded_samples_equal':src.size==decoded.size and src.tobytes()==decoded.tobytes(),'pixels':src.size,'media_box':list(map(float,p.MediaBox)),'geometry_matches_dpi':abs(float(p.MediaBox[2])-src.width*72/dpi)<1e-8 and abs(float(p.MediaBox[3])-src.height*72/dpi)<1e-8})
 assert len(checks)==8 and all(x['decoded_samples_equal'] and x['geometry_matches_dpi'] for x in checks)
 result['documents'][str(dpi)]={'manifest':file(base/'document.json'),'pages':checks}
 for name in ('source.pdf','searchable-raster.pdf','adobe.pdf','previous.pdf','clearscan.pdf'):result['artifacts'].append(file(B/str(dpi)/name))
 for name in ('adobe.pdf','previous.pdf','final.pdf'):result['artifacts'].append(file(B/f'three{dpi}'/name))
for p in sorted((B/'real/product').glob('*.pdf')):result['artifacts'].append(file(p))
for p in sorted((B/'real').glob('*.png')):
 if '.ocr-crop' not in p.name:result['artifacts'].append(file(p))
result['font_sources']=[]
for fp in sorted(set(json.loads(p.read_text())['font'] for p in (ROOT/'qualification/experiments/m1g/fixture/dpi300/oracle').glob('*.truth.json'))):
 p=Path(fp);result['font_sources'].append({'path':fp,'sha256':sha(p)})
result['determinism']={'evidence':(B/'determinism.txt').read_text(),'command':(B/'300/determinism-time.txt').read_text().splitlines()[0],'repeat_bytes_equal':True,'note':'Repeat artifact was temporary; durable hash and exact command retained. Final PDF is committed.'}
(B/'run-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print('verified matched exact source samples:',sum(len(d['pages']) for d in result['documents'].values()))
