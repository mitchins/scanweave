import json,sys,re
from pathlib import Path
root=Path(sys.argv[1]);name=sys.argv[2];a,b=[json.load(open(root/f'{name}-{x}-1.pdf.json')) for x in ('main','candidate')]
for i,(x,y) in enumerate(zip(a['pages'],b['pages'])):
 normal=lambda s:re.sub(r'/tmp/\.tmp[^/]+/','/tmp/TEMP/',s)
 if normal(x['hocr'])!=normal(y['hocr']): print('FAIL',name,i);sys.exit(1)
print('PASS',name,len(a['pages']))
