import concurrent.futures, hashlib, json, os, subprocess
from pathlib import Path
root=Path('/data/coding/scanweave'); out=root/'qualification/acr06/local/c2/identity';out.mkdir(parents=True, exist_ok=True)
env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(root/'tools/src/pdfium/lib/libpdfium.so'),OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python');env.pop('SCANWEAVE_RESEARCH_OWNERSHIP',None);env.pop('SCANWEAVE_RESEARCH_OWNERSHIP_TRACE',None)
def run(arg):
 i,arm=arg; d=(200,300,600)[i//3]; src=root/f'qualification/font04/local/P2pp/sheet-{i}.pdf'; dest=out/f'{arm}-{i}.pdf'
 with open(str(dest)+'.log','w') as log: subprocess.run([f'/tmp/c2-{arm}-scanweave',str(src),str(dest),'--dpi',str(d),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=log,stderr=log,check=True)
 return str(dest)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: print(list(pool.map(run,[(i,a) for i in (0,3,6) for a in ('main','research')])),flush=True)
result={str(i):{a:hashlib.sha256((out/f'{a}-{i}.pdf').read_bytes()).hexdigest() for a in ('main','research')} for i in (0,3,6)}
(out/'hashes.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
