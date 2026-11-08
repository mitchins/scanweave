import sys,json,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
for name in sys.argv[1:]:
 root=Path(name); files=sorted(root.glob('*.ttf')); print(name,'fonts',len(files))
 for f in files:
  t=TTFont(f);print(f.name, {tag:hashlib.sha256(t.getTableData(tag)).hexdigest() for tag in t.keys() if tag!='GlyphOrder'})
  h=t['head']; print('head bounds',h.xMin,h.yMin,h.xMax,h.yMax)
