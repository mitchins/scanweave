import hashlib,json,pathlib
R=pathlib.Path('/data/coding/scanweave/qualification'); A=R/'acr06'; prior=json.loads((A/'ink33r/provenance.json').read_text());rows=[]
for d,v in prior['documents'].items():
 for kind,path,key in [('baseline',A/'local/ink33r'/f'{d}.pdf','corrected_sha256'),('source',R/'pdf_packaging/groups'/f'{d}-input.pdf','source_sha256'),('adobe',R/'pdf_packaging/groups'/f'{d}-adobe.pdf','adobe_sha256')]:
  actual=hashlib.sha256(path.read_bytes()).hexdigest(); expected=v[key];rows.append({'document':d,'kind':kind,'path':str(path),'sha256':actual,'expected_sha256':expected,'matches':actual==expected})
assert all(x['matches'] for x in rows)
(A/'hvc41/provenance.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows),'hashes matched')
