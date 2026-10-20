"""Independent pikepdf/QPDF factorial controls on frozen b2ec997 outputs."""
import pikepdf,json,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent;rows=[]
for dpi in [300,600]:
 src=B.parent/'clearscan_background'/str(dpi)/'final.pdf';d=B/str(dpi);d.mkdir(exist_ok=True)
 for name,streams,objects in [('uncompressed',False,False),('streams',True,False),('objects',False,True),('combined',True,True)]:
  p=pikepdf.open(src);out=d/(name+'.pdf');p.save(out,compress_streams=streams,object_stream_mode=pikepdf.ObjectStreamMode.generate if objects else pikepdf.ObjectStreamMode.disable,recompress_flate=False,deterministic_id=True)
  rows.append({'dpi':dpi,'arm':name,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
(B/'serialization-ablation.json').write_text(json.dumps(rows,indent=2));print(rows)
