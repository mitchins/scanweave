#!/usr/bin/env python3
"""Fetch pinned official source bytes. Holdout images are never decoded here."""
import concurrent.futures, hashlib, json, os, pathlib, subprocess, sys, time, urllib.error, urllib.request
B=pathlib.Path('/data/coding/scanweave/work/books01')
P=pathlib.Path(__file__).resolve().parents[1]
DATA='b7bda5fac0471d6d2237360abc799c6d13559465'
IMAGES='f57bb9e58785a3f9266c05880092ec76720450e5'
corpus=json.loads((P/'corpus.proposed.json').read_text())
pages=corpus['pages']

def get(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        for attempt in range(4):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'ScanWeave-BOOKS01/phase0'})
                with urllib.request.urlopen(req,timeout=90) as r, open(str(target)+'.part','wb') as f:
                    while chunk:=r.read(1024*1024): f.write(chunk)
                os.replace(str(target)+'.part',target); break
            except Exception:
                if attempt==3: raise
                time.sleep(2**attempt)
    return {'url':url,'path':str(target.relative_to(B)),'bytes':target.stat().st_size,'sha256':hashlib.file_digest(target.open('rb'),'sha256').hexdigest()}

def pin(repo):
    x=subprocess.check_output(['git','ls-remote',f'https://github.com/{repo}.git','HEAD'],text=True).split()[0]
    if len(x)!=40: raise ValueError(repo)
    return repo,x

def run():
    repos=sorted({p['repo'] for p in pages if p['source']=='ocr-d-quiver'})
    pins_path=P/"phase0/repo-pins.json"
    if pins_path.exists(): pins=json.loads(pins_path.read_text())
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: pins=dict(pool.map(pin,repos))
    (B/'src/repo-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    tasks=[]
    def add(url,path): tasks.append((url,B/'src'/path))
    for repo,sha in pins.items():
        base=f'https://raw.githubusercontent.com/{repo}/{sha}/'; name=repo.split('/')[1]
        for f in ('LICENSE.md','README.md','METADATA.yml'):
            add(base+f,f'quiver/{name}/{f}')
    for p in pages:
        if p['source']!='ocr-d-quiver' or p['split']=='reserve-dev-work': continue
        repo=p['repo']; name=repo.split('/')[1]; prefix=f"data/{p['work']}/"; base=f'https://raw.githubusercontent.com/{repo}/{pins[repo]}/'
        for f in (f"GT-PAGE/{p['page']}.xml",f"GT-PAGE/{p['page']}.tif",'mets.xml'):
            add(base+prefix+f,f'quiver/{name}/{prefix}{f}')
    for work in sorted({p['work'] for p in pages if p['source']=='finebooks-bhl-impact'}):
        add(f'https://archive.org/metadata/{work}',f'ia/{work}/metadata.json')
        add(f'https://archive.org/download/{work}/{work}_scandata.xml',f'ia/{work}/scandata.xml')
    for f in ('README.md','metadata.parquet'):
        add(f'https://huggingface.co/datasets/finebooks/bhl-impact-gt/resolve/{DATA}/{f}',f'finebooks/{f}')
    # Metadata.parquet supplies page-to-image paths; GT XML is fetched directly later.
    unique=list(dict.fromkeys(tasks)); results=[]; failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        fs={pool.submit(get,*t):t for t in unique}
        for i,f in enumerate(concurrent.futures.as_completed(fs),1):
            try: results.append(f.result())
            except Exception as e: failures.append({'url':fs[f][0],'error':str(e)}); print('FAIL',fs[f][0],str(e),flush=True)
            if i%20==0: print(f'{i}/{len(fs)} completed, {len(failures)} failed',flush=True)
    (B/'src/fetch-results.json').write_text(json.dumps({'pins':pins,'files':results,'failures':failures},indent=2)+'\n')
    if failures: sys.exit(1)
if __name__=='__main__': run()
