"""Separate-process blind export. Public filenames contain no arm or side identity."""
from pathlib import Path
import json,os,secrets,shutil,sys,zlib
import pikepdf
from PIL import Image,ImageDraw
from qualification.font04.review_key import font
from qualification.font04.metrics import sha

def main(staging,directory,keypath):
    assert not directory.exists() and not keypath.exists(), 'Never overwrite a sealed review'
    directory.mkdir(mode=0o755,parents=True);assets=directory/'assets';assets.mkdir();keypath.parent.mkdir(mode=0o700,parents=True,exist_ok=True);metadata=json.loads((staging/'panels.json').read_text());secrets.SystemRandom().shuffle(metadata);key={};panels=[]
    for p in metadata:
        token='panel-'+secrets.token_hex(10);flip=secrets.randbelow(2);key[token]=dict(metadata=p,candidate='U' if flip else 'V',current='V' if flip else 'U');panels.append(dict(id=token,renderer=p['renderer']))
        for target,kind in [('source','source'),('U','candidate' if flip else 'current'),('V','current' if flip else 'candidate')]:shutil.copyfile(staging/'assets'/(p['asset']+'-'+kind+'.png'),assets/(token+'-'+target+'.png'))
    keypath.write_text(json.dumps(key));keypath.chmod(0o600);pdf=pikepdf.Pdf.new();judgments=[]
    for offset in range(0,len(panels),4):
        batch=panels[offset:offset+4];sizes=[Image.open(assets/(p['id']+'-source.png')).size for p in batch];cw=max(760,max(w*4+60 for w,h in sizes));rh=max(675,320+max(h*4 for w,h in sizes));sheet=Image.new('RGB',(80+3*cw,300+len(batch)*rh),'white');draw=ImageDraw.Draw(sheet);draw.text((80,45),'FONT-04 B2-prime blind review: Source / U / V',font=font(40),fill='black');draw.text((80,108),'100% and 400%; save all judgments before requesting the separate key.',font=font(25),fill='black')
        for slot,p in enumerate(batch):
            y=220+slot*rh;token=p['id'];draw.text((80,y),token+' '+p['renderer'],font=font(26),fill='black')
            for column,label in enumerate(['source','U','V']):
                image=Image.open(assets/(token+'-'+label+'.png')).convert('RGB');x=80+column*cw;draw.text((x,y+50),label.title(),font=font(30),fill='black');draw.text((x,y+95),'100%',font=font(24),fill='black');sheet.paste(image,(x,y+135));draw.text((x,y+210),'400%',font=font(24),fill='black');sheet.paste(image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST),(x,y+250))
            judgments.append(dict(id=token,U=None,V=None,notes='',allowed=['material defect','minor','indistinguishable','improvement']))
        w,h=sheet.size;im=pdf.make_stream(zlib.compress(sheet.tobytes()));im.Type=pikepdf.Name.XObject;im.Subtype=pikepdf.Name.Image;im.Width=w;im.Height=h;im.ColorSpace=pikepdf.Name.DeviceRGB;im.BitsPerComponent=8;im.Filter=pikepdf.Name.FlateDecode;pw,ph=w*72/300,h*72/300;page=pdf.add_blank_page(page_size=(pw,ph));page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=im));page.Contents=pdf.make_stream(f'q {pw} 0 0 {ph} 0 0 cm /Im Do Q'.encode())
        if offset%200==0:print('sealed review panels',offset,len(panels),flush=True)
    pdf.save(directory/'blinded-review.pdf',deterministic_id=True);(directory/'panels.json').write_text(json.dumps(panels,indent=2)+'\n');(directory/'judgments-template.json').write_text(json.dumps(dict(status='reviewer-pending',judgments=judgments),indent=2)+'\n')
    receipt=dict(review_sha256=sha(directory/'blinded-review.pdf'),key_sha256=sha(keypath),key_path=str(keypath),panels=len(panels),judgments_sha256=sha(directory/'judgments-template.json'),status='sealed; reviewer pending')
    (directory/'seal-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Sealed',len(panels),'panels; key written separately; no key readback',flush=True)

def reveal(directory,keypath,judgments):
    # This branch is only for the independent reviewer after saving judgments.
    data=json.loads(judgments.read_text());rows=data['judgments'];public=json.loads((directory/'panels.json').read_text());ids={p['id'] for p in public};allowed={'material defect','minor','indistinguishable','improvement'}
    assert len(rows)==len(ids) and {r['id'] for r in rows}==ids, 'Missing/duplicate judgments'
    assert all(r.get('U') in allowed and r.get('V') in allowed for r in rows), 'Save every U/V judgment before reveal'
    receipt=json.loads((directory/'seal-receipt.json').read_text());assert sha(keypath)==receipt['key_sha256'];key=json.loads(keypath.read_text());decoded=[]
    for r in rows:
        k=key[r['id']];decoded.append(dict(id=r['id'],current=r[k['current']],candidate=r[k['candidate']],notes=r.get('notes',''),metadata=k['metadata']))
    (directory/'revealed-judgments.json').write_text(json.dumps(dict(judgments_sha256=sha(judgments),decoded=decoded),indent=2)+'\n')

if __name__=='__main__':
    if sys.argv[1]=='reveal':reveal(*map(Path,sys.argv[2:]))
    else:main(*map(Path,sys.argv[1:]))
