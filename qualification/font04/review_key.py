"""Separate blinding lifecycle: create, render, then reveal only saved judgments."""
from pathlib import Path
import json
import secrets
import zlib
import pikepdf
import sys
from PIL import Image,ImageDraw,ImageFont


def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)


def create():
    request=json.load(sys.stdin);path=Path(request['destination'])
    if path.exists():
        key=json.loads(path.read_text())
        for identifier in request['ids']:
            if identifier not in key:key[identifier]=secrets.randbelow(2)
    else:key={identifier:secrets.randbelow(2)for identifier in request['ids']}
    path.write_text(json.dumps(key));path.chmod(0o600)


def render(directory):
    metadata=json.loads((directory/'panels.json').read_text());key=json.loads((directory/'sealed-key.json').read_text());pdf=pikepdf.Pdf.new();judgments=[]
    for offset in range(0,len(metadata),4):
        column_width=max(760,max(Image.open(directory/'assets'/(p['id']+'-source.png')).width*4+60 for p in metadata[offset:offset+4]))
        row_height=max(675,320+max(Image.open(directory/'assets'/(p['id']+'-source.png')).height*4 for p in metadata[offset:offset+4]))
        page=Image.new('RGB',(80+3*column_width,300+4*row_height),'white');draw=ImageDraw.Draw(page);draw.text((80,45),'FONT-04 blind review — source / U / V',font=font(42),fill='black')
        draw.text((80,108),'100% and 400% at 300 DPI physical coordinates. Record judgments before reveal.',font=font(25),fill='black')
        for slot,panel in enumerate(metadata[offset:offset+4]):
            y=220+slot*row_height;identifier=panel['id'];draw.text((80,y),identifier+'  '+panel['renderer'],font=font(30),fill='black')
            kinds=['source','candidate','current']if key[identifier]else['source','current','candidate']
            for column,(label,kind)in enumerate(zip(['Source','U','V'],kinds)):
                image=Image.open(directory/'assets'/(identifier+'-'+kind+'.png')).convert('RGB');x=80+column*column_width;draw.text((x,y+50),label,font=font(30),fill='black');draw.text((x,y+95),'100%',font=font(24),fill='black');page.paste(image,(x,y+135));draw.text((x,y+210),'400%',font=font(24),fill='black')
                enlarged=image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
                page.paste(enlarged,(x,y+250))
            judgments.append(dict(id=identifier,U=None,V=None,notes='',allowed=['material defect','minor','indistinguishable','improvement']))
        # Lossless Flate avoids JPEG artifacts in counter/stroke judgments and
        # compresses each sheet immediately instead of retaining huge bitmaps.
        w,h=page.size;image=pdf.make_stream(zlib.compress(page.tobytes()));image.Type=pikepdf.Name.XObject;image.Subtype=pikepdf.Name.Image;image.Width=w;image.Height=h;image.ColorSpace=pikepdf.Name.DeviceRGB;image.BitsPerComponent=8;image.Filter=pikepdf.Name.FlateDecode
        pw,ph=w*72/300,h*72/300;sheet=pdf.add_blank_page(page_size=(pw,ph));sheet.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image));sheet.Contents=pdf.make_stream(f'q {pw} 0 0 {ph} 0 0 cm /Im Do Q'.encode())
    pdf.save(directory/'blinded-review.pdf',deterministic_id=True,compress_streams=True)
    (directory/'judgments-template.json').write_text(json.dumps(dict(status='unreviewed',judgments=judgments),indent=2))


def reveal(directory,judgment_path):
    data=json.loads(judgment_path.read_text());key=json.loads((directory/'sealed-key.json').read_text());rows=data['judgments']
    if not rows or any(r['U']not in r['allowed']or r['V']not in r['allowed']for r in rows):raise ValueError('Refuse reveal: every U/V judgment must be saved first')
    decoded=[]
    for row in rows:
        current,candidate=('V','U')if key[row['id']]else('U','V');decoded.append(dict(id=row['id'],current=row[current],candidate=row[candidate],notes=row['notes']))
    (directory/'revealed-judgments.json').write_text(json.dumps(decoded,indent=2))


if __name__=='__main__':
    if sys.argv[1]=='create':create()
    elif sys.argv[1]=='render':render(Path(sys.argv[2]))
    elif sys.argv[1]=='reveal':reveal(Path(sys.argv[2]),Path(sys.argv[3]))
    else:raise ValueError('unknown key lifecycle action')
