#!/usr/bin/env python3
"""Check fetched page bytes and write a local, explicitly unfrozen inventory."""
import hashlib, json, pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
corpus=json.loads((P/'corpus.proposed.json').read_text()); pages=corpus['pages']
assert not ({p['work'] for p in pages if p['split']=='dev'} & {p['work'] for p in pages if p['split']=='holdout'})
fetch=json.loads((B/'src/fetch-results.json').read_text()); assert not fetch['failures']
files=fetch['files']+json.loads((B/'src/finebooks/fetch-results.json').read_text())
lookup={x['path']:x for x in files}
inventory={}
for p in pages:
    if p['split']=='reserve-dev-work': continue
    if p['source']=='ocr-d-quiver':
        prefix='src/quiver/'+p['repo'].split('/')[1]+'/data/'+p['work']+'/GT-PAGE/'+p['page']
        paths=[prefix+'.tif',prefix+'.xml']
    else:
        prefix='src/finebooks/pages/'+p['work']+'/'+str(p['page'])+'/'
        paths=[prefix+'image.webp',prefix+'gt.xml']
    records=[]
    for path in paths:
        record=lookup[path]; file=B/path
        with file.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        assert digest==record['sha256'] and file.stat().st_size==record['bytes'] and record['bytes']>0
        records.append(record)
    inventory[p['id']]={'split':p['split'],'files':records}
(B/'inventory.unfrozen.json').write_text(json.dumps({'status':'INCOMPLETE; NOT A CORPUS FREEZE','book_disjoint':True,'pages':inventory},indent=2)+'\n')
print('verified',len(inventory),'pages; holdout bytes only')
