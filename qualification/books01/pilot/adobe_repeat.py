#!/usr/bin/env python3
"""Inspect only the two pre-existing Adobe output batches, without Acrobat."""
import hashlib,json,pathlib,subprocess
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6'];out={}
for id in ids:
 key=id.split('/')[-1];paths=[B/'runs/adobe'/(key+'.adobe.pdf'),B/'runs/adobe-engb-superseded'/(key+'.adobe.pdf')];
 if not all(x.exists() for x in paths):out[id]={'status':'missing repeat'};continue
 texts=[subprocess.run(['/usr/bin/pdftotext',str(x),'-'],capture_output=True) for x in paths];out[id]={'status':'ok','bytes':[x.stat().st_size for x in paths],'byte_size_difference':paths[0].stat().st_size-paths[1].stat().st_size,'poppler_text_equal':texts[0].returncode==texts[1].returncode==0 and texts[0].stdout==texts[1].stdout,'text_sha256':[hashlib.sha256(x.stdout).hexdigest() for x in texts]}
(P/'pilot/results/adobe-repeat.json').write_text(json.dumps(out,indent=2)+'\n')
isolation={}
for name in ['adobe','adobe-engb-superseded']:
 p=B/'runs'/name/'offline-exec.log';events=[json.loads(x) for x in p.read_text().splitlines()];isolation[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'denied_internet_socket_events':sum(e.get('event')=='deny' for e in events)}
(P/'pilot/results/adobe-isolation.json').write_text(json.dumps(isolation,indent=2)+'\n')
