import json
from pathlib import Path
import pikepdf
root=Path('/data/coding/scanweave/qualification/acr06')
rows=[]
for path in sorted((root/'local/ink37/control-main').glob('*.pdf')):
    with pikepdf.open(path) as pdf:
        for pg in pdf.pages:
            rgb=[]; tr=0; fills=[]
            for ins in pikepdf.parse_content_stream(pg):
                op=str(ins.operator); a=ins.operands
                if op=='rg': rgb=[round(float(v)*255) for v in a]
                elif op=='Tr': tr=int(a[0])
                elif op in ('Tj','TJ') and tr in (0,2,4,6): fills.append(rgb)
            rows.append({'name':path.stem,'visible_shows':len(fills),'visible_fills':list({tuple(x) for x in fills})})
(root/'ink37/control-main-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
