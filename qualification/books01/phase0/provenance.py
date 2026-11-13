#!/usr/bin/env python3
"""Collect short, source-attributed licence and image-rights evidence."""
import hashlib, json, pathlib, re, xml.etree.ElementTree as ET
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
pages=json.loads((P/'corpus.proposed.json').read_text())['pages']
pins=json.loads((B/'src/repo-pins.json').read_text())
def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def local(t): return t.rsplit('}',1)[-1]
repos={}; works={}; ia={}
for repo,sha in pins.items():
    d=B/'src/quiver'/repo.split('/')[1]; entries={}
    for name in ['LICENSE.md','README.md','METADATA.yml']:
        s=(d/name).read_text();
        if name=='LICENSE.md': quote=s.splitlines()[0]
        elif name=='README.md':
            m=re.search(r'<dt id="License">.*?</dt>\s*<dd>(.*?)</dd>',s,re.S); quote=m.group(0) if m else None
        else:
            m=re.search(r'^license:\s*\n(?:[ \t]+.*\n)*',s,re.M); quote=m.group(0).strip() if m else None
        entries[name]={'url':f'https://raw.githubusercontent.com/{repo}/{sha}/{name}','sha256':digest(d/name),'quote':quote}
    repos[repo]={'commit':sha,'files':entries,'conservative_interpretation':'CC-BY-SA-4.0'}
for p in pages:
    if p['source']!='ocr-d-quiver': continue
    key=p['repo']+'/'+p['work']
    if key in works: continue
    repo=p['repo']; sha=pins[repo]; path=B/'src/quiver'/repo.split('/')[1]/'data'/p['work']/'mets.xml'
    root=ET.parse(path).getroot(); selected=[]
    for e in root.iter():
        name=local(e.tag)
        if name in {'accessCondition','physicalLocation','shelfLocator','owner','ownerSiteURL','licenseDocumentationIdentifierValue','extent','identifier','languageTerm'}:
            text=' '.join(''.join(e.itertext()).split())
            if text: selected.append({'element':name,'text':text,'attributes':{local(k):v for k,v in e.attrib.items()}})
    works[key]={'url':f'https://raw.githubusercontent.com/{repo}/{sha}/data/{p["work"]}/mets.xml','sha256':digest(path),'statements':selected}
for work in sorted({p['work'] for p in pages if p['source']=='finebooks-bhl-impact'}):
    d=B/'src/ia'/work; meta=json.loads((d/'metadata.json').read_text())['metadata']
    keys=[k for k in meta if any(t in k.lower() for t in ['right','license','licence','copyright','ppi','collection','sponsor','contributor'])]
    root=ET.parse(d/'scandata.xml').getroot()
    ia[work]={'metadata_url':f'https://archive.org/metadata/{work}','metadata_sha256':digest(d/'metadata.json'),'fields':{k:meta[k] for k in keys},'scandata_url':f'https://archive.org/download/{work}/{work}_scandata.xml','scandata_sha256':digest(d/'scandata.xml'),'scandata_book_dpi':root.findtext('./bookData/dpi'),'scandata_rights_fields':[{'element':local(e.tag),'text':' '.join(''.join(e.itertext()).split())} for e in root.iter() if any(k in local(e.tag).lower() for k in ['right','license','licence','copyright']) and ''.join(e.itertext()).strip()]}
out={'schema':'books01-licences/1','quiver_repositories':repos,'quiver_works':works,'finebooks':{'dataset_revision':'b7bda5fac0471d6d2237360abc799c6d13559465','image_revision':'f57bb9e58785a3f9266c05880092ec76720450e5','dataset_readme_url':'https://huggingface.co/datasets/finebooks/bhl-impact-gt/resolve/b7bda5fac0471d6d2237360abc799c6d13559465/README.md','dataset_readme_sha256':digest(B/'src/finebooks/README.md'),'ia_volumes':ia}}
(P/'provenance').mkdir(exist_ok=True); (P/'provenance/licences.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
