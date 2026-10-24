"""Separate-process blind export. Public filenames contain no arm or side identity."""
from pathlib import Path
import json,os,secrets,shutil,sys,zlib
import pikepdf
from PIL import Image,ImageDraw
from qualification.font04.review_key import font
from qualification.font04.metrics import sha

def render_sheet(task):
    assets,batch=task;judgments=[]
    sizes=[Image.open(assets/(p['id']+'-A.png')).size for p in batch];cw=max(760,max(w*4+60 for w,h in sizes));rh=max(675,320+max(h*4 for w,h in sizes));sheet=Image.new('RGB',(80+3*cw,300+len(batch)*rh),'white');draw=ImageDraw.Draw(sheet);draw.text((80,45),'FONT-04 R2a blind review: A / B / C',font=font(40),fill='black');draw.text((80,108),'100% and 400%; save all judgments before requesting the separate key.',font=font(25),fill='black')
    for slot,p in enumerate(batch):
        y=220+slot*rh;token=p['id'];draw.text((80,y),token+' '+p['renderer'],font=font(26),fill='black')
        for column,label in enumerate(['A','B','C']):
            image=Image.open(assets/(token+'-'+label+'.png')).convert('RGB');x=80+column*cw;draw.text((x,y+50),label.title(),font=font(30),fill='black');draw.text((x,y+95),'100%',font=font(24),fill='black');sheet.paste(image,(x,y+135));draw.text((x,y+210),'400%',font=font(24),fill='black');sheet.paste(image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST),(x,y+250))
        judgments.append(dict(id=token,A=None,B=None,C=None,notes='',allowed=['material defect','minor','indistinguishable','improvement']))
    w,h=sheet.size;return w,h,zlib.compress(sheet.tobytes()),judgments


def main(staging,directory,keypath):
    assert not directory.exists() and not keypath.exists(), 'Never overwrite a sealed review'
    # Real corpus exports must pass pixel checks before any public package/key
    # is created. Small synthetic sealer smoke tests have no selection manifest.
    if (staging/'selection.json').exists():
        from qualification.font04.r2a_package_checks import validate
        validation = validate(staging, Path(__file__).resolve().parent/'local/R2a/export')
        assert validation['pass_all'], 'Review pixel invariants failed; see pixel-validation.json'
    directory.mkdir(mode=0o755,parents=True);assets=directory/'assets';assets.mkdir();keypath.parent.mkdir(mode=0o700,parents=True,exist_ok=True);metadata=json.loads((staging/'panels.json').read_text());secrets.SystemRandom().shuffle(metadata);key={};panels=[]
    for p in metadata:
        token='panel-'+secrets.token_hex(10)
        roles=['source','current','candidate'];secrets.SystemRandom().shuffle(roles)
        assignment=dict(zip(['A','B','C'],roles))
        key[token]=dict(metadata=p,**{role:label for label,role in assignment.items()})
        panels.append(dict(id=token,renderer=p['renderer']))
        for target,kind in assignment.items():
            shutil.copyfile(staging/'assets'/(p['asset']+'-'+kind+'.png'),assets/(token+'-'+target+'.png'))
    shutil.copyfile(staging/'README.md',directory/'README.md')
    keypath.write_text(json.dumps(key));keypath.chmod(0o600);pdf=pikepdf.Pdf.new();judgments=[]
    import multiprocessing
    tasks=[(assets,panels[offset:offset+4]) for offset in range(0,len(panels),4)]
    with multiprocessing.get_context('spawn').Pool(8) as pool:
        for page_index,(w,h,compressed,rows) in enumerate(pool.imap(render_sheet,tasks,chunksize=2)):
            judgments.extend(rows);im=pdf.make_stream(compressed);im.Type=pikepdf.Name.XObject;im.Subtype=pikepdf.Name.Image;im.Width=w;im.Height=h;im.ColorSpace=pikepdf.Name.DeviceRGB;im.BitsPerComponent=8;im.Filter=pikepdf.Name.FlateDecode;pw,ph=w*72/300,h*72/300;page=pdf.add_blank_page(page_size=(pw,ph));page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=im));page.Contents=pdf.make_stream(f'q {pw} 0 0 {ph} 0 0 cm /Im Do Q'.encode())
            if page_index%50==0:print('sealed review panels',page_index*4,len(panels),flush=True)
    pdf.save(directory/'blinded-review.pdf',deterministic_id=True);(directory/'panels.json').write_text(json.dumps(panels,indent=2)+'\n');(directory/'judgments-template.json').write_text(json.dumps(dict(status='reviewer-pending',judgments=judgments),indent=2)+'\n')
    receipt=dict(review_sha256=sha(directory/'blinded-review.pdf'),key_sha256=sha(keypath),key_path=str(keypath),panels=len(panels),readme_sha256=sha(directory/'README.md'),judgments_sha256=sha(directory/'judgments-template.json'),status='sealed; reviewer pending')
    (directory/'seal-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Sealed',len(panels),'panels; key written separately; no key readback',flush=True)

def reveal(directory,keypath,judgments):
    # This branch is only for the independent reviewer after saving judgments.
    data=json.loads(judgments.read_text());rows=data['judgments'];public=json.loads((directory/'panels.json').read_text());ids={p['id'] for p in public};allowed={'material defect','minor','indistinguishable','improvement'}
    assert len(rows)==len(ids) and {r['id'] for r in rows}==ids, 'Missing/duplicate judgments'
    assert all(all(r.get(label) in allowed for label in ('A','B','C')) for r in rows), 'Save every A/B/C judgment before reveal'
    receipt=json.loads((directory/'seal-receipt.json').read_text());assert sha(keypath)==receipt['key_sha256'];key=json.loads(keypath.read_text());decoded=[]
    for r in rows:
        k=key[r['id']];decoded.append(dict(id=r['id'],source=r[k['source']],current=r[k['current']],candidate=r[k['candidate']],notes=r.get('notes',''),metadata=k['metadata']))
    (directory/'revealed-judgments.json').write_text(json.dumps(dict(judgments_sha256=sha(judgments),decoded=decoded),indent=2)+'\n')

if __name__=='__main__':
    if sys.argv[1]=='reveal':reveal(*map(Path,sys.argv[2:]))
    else:main(*map(Path,sys.argv[1:]))
