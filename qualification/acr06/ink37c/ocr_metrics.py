from pathlib import Path
import difflib,hashlib,json,re
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37c/ocr');rows=[]
for item in ('historical-02','historical-05','receipts-04'):
 data={arm:(root/f'{item}-{arm}.txt').read_text() for arm in ('source','lossless','compact')};words={k:re.findall(r'[^\W_]+',v.lower()) for k,v in data.items()}
 rows.append({'page':item,'word_count':{k:len(v) for k,v in words.items()},'source_to_lossless_ratio':difflib.SequenceMatcher(None,words['source'],words['lossless'],autojunk=False).ratio(),'source_to_compact_ratio':difflib.SequenceMatcher(None,words['source'],words['compact'],autojunk=False).ratio(),'sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in data.items()}})
Path('/data/coding/scanweave/qualification/acr06/ink37c/ocr.json').write_text(json.dumps(rows,indent=2)+'\n')
for x in rows:print(x)
