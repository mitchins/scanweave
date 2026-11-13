#!/usr/bin/env python3
"""Fetch selected FineBooks WebP and GT bytes from immutable HF revisions.

The parquet metadata is read without decoding its image objects. Holdout files
are saved and hashed only, never passed to an image decoder or GT parser.
"""
import concurrent.futures, hashlib, json, os, pathlib, time, urllib.request
import pyarrow.parquet as pq
B=pathlib.Path('/data/coding/scanweave/work/books01')
P=pathlib.Path(__file__).resolve().parents[1]
D='b7bda5fac0471d6d2237360abc799c6d13559465'; I='f57bb9e58785a3f9266c05880092ec76720450e5'
base='https://huggingface.co/datasets/finebooks/bhl-impact-gt/resolve/'
pages=[p for p in json.loads((P/'corpus.proposed.json').read_text())['pages'] if p['source']=='finebooks-bhl-impact']
rows=pq.read_table(B/'src/finebooks/metadata.parquet',columns=['PageID','BarCode','file_name','xml_path']).to_pylist()
by={(str(r['PageID']),r['BarCode']):r for r in rows}
def fetch(item):
    url,path=item; path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        for n in range(4):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'ScanWeave-BOOKS01/phase0'})
                with urllib.request.urlopen(req,timeout=120) as resp,open(str(path)+'.part','wb') as out:
                    while chunk:=resp.read(1024*1024): out.write(chunk)
                os.replace(str(path)+'.part',path); break
            except Exception:
                if n==3: raise
                time.sleep(2**n)
    with path.open('rb') as f: h=hashlib.file_digest(f,'sha256').hexdigest()
    return {'url':url,'path':str(path.relative_to(B)),'bytes':path.stat().st_size,'sha256':h}
tasks=[]; mappings={}
for p in pages:
    r=by[(str(p['page']),p['work'])]; image=r['file_name']; xml=r['xml_path']
    mappings[p['id']]={'image_path':image,'xml_path':xml}
    for rev,source,target in [(I,image,'image.webp'),(D,xml,'gt.xml')]:
        tasks.append((base+rev+'/'+source,B/'src/finebooks/pages'/p['work']/str(p['page'])/target))
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(fetch,tasks))
(B/'src/finebooks/page-mappings.json').write_text(json.dumps(mappings,indent=2)+'\n')
(B/'src/finebooks/fetch-results.json').write_text(json.dumps(results,indent=2)+'\n')
