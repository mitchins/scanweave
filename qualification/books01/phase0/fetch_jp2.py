#!/usr/bin/env python3
"""Map dev access indices through scandata and fetch individual IA tar members."""
import concurrent.futures, hashlib, json, os, pathlib, re, time, urllib.request, xml.etree.ElementTree as ET
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
pages=[p for p in json.loads((P/'corpus.proposed.json').read_text())['pages'] if p['source']=='finebooks-bhl-impact' and p['split']=='dev']
maps=json.loads((B/'src/finebooks/page-mappings.json').read_text())
def fetch(p):
    work=p['work']; access=int(re.search(r'_(\d+)_full\.webp$',maps[p['id']]['image_path']).group(1))
    root=ET.parse(B/'src/ia'/work/'scandata.xml').getroot()
    leaves=[int(e.attrib['leafNum']) for e in root.findall('./pageData/page') if e.findtext('addToAccessFormats')=='true']
    leaf=leaves[access-1]; member=f'{work}_orig_jp2/{work}_orig_{leaf:04d}.jp2'
    url=f'https://archive.org/download/{work}/{work}_orig_jp2.tar/{member}'
    target=B/'src/ia'/work/f'{p["page"]}.jp2'
    if not target.exists() or target.stat().st_size == 0:
        for n in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ScanWeave-BOOKS01/phase0'}),timeout=120) as r,open(str(target)+'.part','wb') as f:
                    while chunk:=r.read(1024*1024): f.write(chunk)
                if os.path.getsize(str(target)+'.part')==0: raise ValueError('empty archive member')
                os.replace(str(target)+'.part',target); break
            except Exception:
                if n==3: raise
                time.sleep(2**n)
    with target.open('rb') as f: h=hashlib.file_digest(f,'sha256').hexdigest()
    return p['id'],{'access_index':access,'leaf':leaf,'url':url,'sha256':h,'bytes':target.stat().st_size,'path':str(target.relative_to(B))}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: result=dict(ex.map(fetch,pages))
(B/'src/ia/dev-jp2.json').write_text(json.dumps(result,indent=2)+'\n')
