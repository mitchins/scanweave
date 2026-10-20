"""Count actual paint, resources and native searches on the two fixed candidates."""
import json,io,hashlib,subprocess,re
from pathlib import Path
import pikepdf,numpy as np,pypdfium2 as pdfium
from fontTools.ttLib import TTFont
B=Path(__file__).resolve().parent;R=B.parents[1];rows=[]
for name in ['a','b']:
 path=B/f'{name}.pdf';q=pikepdf.open(path);draws=0;used=set();raster=0;fontbytes=0;content=0;image_resources=0
 for o in q.objects:
  if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name.Image:
   raster+=len(o.read_raw_bytes());image_resources+=1
  if isinstance(o,pikepdf.Dictionary) and '/FontFile2' in o:fontbytes+=len(o.FontFile2.read_raw_bytes())
 for pg in q.pages:
  font=None;mode=0
  for operands,operator in pikepdf.parse_content_stream(pg):
   op=str(operator)
   if op=='Tf':font=pg.Resources.Font.get(str(operands[0]))
   elif op=='Tr':mode=int(operands[0])
   elif op in ['Tj','TJ'] and mode!=3 and font is not None:
    desc=font.DescendantFonts[0];mp=desc.CIDToGIDMap.read_bytes();fid=desc.FontDescriptor.FontFile2.objgen;items=[operands[0]] if op=='Tj' else [x for x in operands[0] if isinstance(x,pikepdf.String)]
    for s in items:
     data=bytes(s)
     for i in range(0,len(data)-1,2):cid=int.from_bytes(data[i:i+2],'big');gid=int.from_bytes(mp[cid*2:cid*2+2],'big');draws+=1;used.add((fid,gid))
  streams=pg.Contents if isinstance(pg.Contents,pikepdf.Array) else [pg.Contents];content+=sum(len(s.read_raw_bytes()) for s in streams)
 report=json.loads(Path(str(path)+'.json').read_text());pr=report['conversion']['page_reports'][0]
 old=R/'qualification/real_convergence/outputs/history-02.pdf';txt={}
 for renderer in ['poppler','pdfium']:
  def get(p):return subprocess.check_output(['pdftotext','-raw',str(p),'-']).decode() if renderer=='poppler' else pdfium.PdfDocument(str(p))[0].get_textpage().get_text_range()
  t=get(path);before=get(old);txt[renderer]={'equal_to_published':t==before,'sha256':hashlib.sha256(t.encode()).hexdigest(),'nonspace_characters':len(''.join(t.split()))}
 rows.append({'arm':name,'bytes':path.stat().st_size,'raster_bytes':raster,'image_resources':image_resources,'font_bytes':fontbytes,'content_bytes':content,'overhead_bytes':path.stat().st_size-raster-fontbytes-content,'actual_glyph_draws':draws,'unique_painted_gids':len(used),'visible_owner_records':sum(o['owner'].startswith('visible') for o in pr['occurrences']),'observations':len(pr['reconstruction']['observations']),'ocr_chars':pr['supplied_chars'],'ink_suppressed_pixels':pr['raster_ink_pixels_suppressed'],'antialias_suppressed_pixels':pr['antialias_fringe_pixels_suppressed'],'text':txt,'stage_timings':report['conversion']['stage_timings'],'page_timings':pr['stage_timings_ms']})
(B/'audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
