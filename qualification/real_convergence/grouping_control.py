import json,re,io,hashlib,subprocess,collections
from pathlib import Path
import pikepdf,pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;old=B/'controls/forms-before-grouping.pdf';new=B/'collections/forms.pdf';source=B.parent/'pdf_packaging/groups/forms-input.pdf';sha=lambda b:hashlib.sha256(b).hexdigest()
a=pikepdf.open(old);b=pikepdf.open(new)
def resource_hashes(q):
 return sorted(sha(o.read_raw_bytes()) for o in q.objects if isinstance(o,pikepdf.Stream) and (o.get('/Subtype')==pikepdf.Name.Image or '/Length1' in o))
assert resource_hashes(a)==resource_hashes(b)
extraction=[]
for flag in ['-raw','-layout']:
 x=subprocess.check_output(['pdftotext',flag,str(old),'-']);y=subprocess.check_output(['pdftotext',flag,str(new),'-']);extraction.append({'renderer':'poppler','mode':flag,'identical':x==y,'old_sha256':sha(x),'new_sha256':sha(y)})
x=[p.get_textpage().get_text_range() for p in pdfium.PdfDocument(str(old))];y=[p.get_textpage().get_text_range() for p in pdfium.PdfDocument(str(new))];extraction.append({'renderer':'pdfium','identical':x==y,'old_sha256':sha('\n'.join(x).encode()),'new_sha256':sha('\n'.join(y).encode())})
def draws(q,index):
 mode=0;matrix=[];out=[]
 for operands,op in pikepdf.parse_content_stream(q.pages[index]):
  op=str(op)
  if op=='Tr':mode=int(operands[0])
  if op=='Tm':matrix=tuple(map(float,operands))
  if op=='Tj' and mode!=3:out.append((int.from_bytes(bytes(operands[0]),'big'),matrix))
 return out
before=draws(a,0);after=draws(b,0);extra=list((collections.Counter(after)-collections.Counter(before)).elements());assert len(extra)==5
font=b.pages[0].Resources.Font.F1;maps=font.DescendantFonts[0].CIDToGIDMap.read_bytes();program=font.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes();tt=TTFont(io.BytesIO(program));upem=tt['head'].unitsPerEm;cm=font.ToUnicode.read_bytes().decode();unicode={int(cid,16):bytes.fromhex(text).decode('utf-16-be') for cid,text in re.findall(r'<([0-9A-Fa-f]{4})> <([0-9A-Fa-f]+)>',cm) if len(text)%4==0}
rows=[];items=[]
for cid,mat in extra:
 gid=int.from_bytes(maps[cid*2:cid*2+2],'big');glyph=tt['glyf'][tt.getGlyphOrder()[gid]];sx,_,_,sy,tx,ty=mat;x0=tx+glyph.xMin*sx/upem;x1=tx+glyph.xMax*sx/upem;y0=ty+glyph.yMin*sy/upem;y1=ty+glyph.yMax*sy/upem;items.append({'cid':cid,'gid':gid,'unicode':unicode.get(cid),'bbox_pt':[x0,y0,x1,y1]});cols=[]
 for name,path in [('Source',source),('Before',old),('Fixed',new)]:
  pg=pdfium.PdfDocument(str(path))[0];w,h=pg.get_size();crop=(max(0,x0-4),max(0,y0-4),max(0,w-x1-4),max(0,h-y1-4));im=pg.render(scale=600/72,crop=crop).to_pil().convert('RGB');canvas=Image.new('RGB',(220,190),'white');im.thumbnail((215,165));canvas.paste(im,(0,20));ImageDraw.Draw(canvas).text((3,3),name+' '+str(unicode.get(cid)),fill='black');cols.append(canvas)
 row=Image.new('RGB',(660,190),'white')
 for i,im in enumerate(cols):row.paste(im,(220*i,0))
 rows.append(row)
sheet=Image.new('RGB',(660,190*len(rows)),'white')
for i,row in enumerate(rows):sheet.paste(row,(0,190*i))
sheet.save(B/'comparisons/restored-form-digits.png');record={'old_pdf_bytes':old.stat().st_size,'new_pdf_bytes':new.stat().st_size,'first_page_before_draws':len(before),'first_page_after_draws':len(after),'added':items,'font_and_image_streams_unchanged':True,'extraction':extraction};(B/'grouping-control.json').write_text(json.dumps(record,indent=2));print(record)
