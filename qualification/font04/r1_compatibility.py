"""R1 consumer checks on explicit native output paths only. Never handles P2."""
import argparse, hashlib, io, json, os, subprocess
from pathlib import Path
import pikepdf
import pypdfium2 as pdfium

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
LOCAL=BASE/'local'
DEFAULT=LOCAL/'financial-R1-rust-default.pdf'
MU=LOCAL/'mupdf-tools/usr/bin/mutool'


def run(args):
    env=dict(os.environ,LD_LIBRARY_PATH=str(LOCAL/'mupdf-tools/usr/lib/x86_64-linux-gnu')+':'+str(ROOT/'tools/dist/lib'))
    p=subprocess.run(list(map(str,args)),env=env,capture_output=True)
    if p.returncode: raise RuntimeError(f'{args[0]} returned {p.returncode}: {p.stderr.decode(errors="replace")}')
    return p.stdout


def inspect(path):
    out=LOCAL/'R1-compatibility'/path.stem
    out.mkdir(parents=True,exist_ok=True)
    result=dict(pdf=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),consumer={})
    doc=pdfium.PdfDocument(path);texts=[]
    for i,page in enumerate(doc):
        tp=page.get_textpage();texts.append(tp.get_text_range());tp.close()
        bitmap=page.render(scale=300/72);bitmap.to_pil().save(out/f'pdfium-{i+1:02}.png');bitmap.close();page.close()
    doc.close();result['pages']=len(texts);result['consumer']['PDFium']=dict(page_text=texts,pages_rendered=len(texts))
    (out/'pdfium-text.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2)+'\n')
    pop={}
    for mode,flags in [('default',[]),('layout',['-layout']),('raw',['-raw'])]:
        data=run(['pdftotext',*flags,path,'-']);(out/f'poppler-{mode}.txt').write_bytes(data);pop[mode]=dict(text_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    run(['pdftoppm','-r','300','-png',path,out/'poppler'])
    pop['pages_rendered']=len(list(out.glob('poppler-*.png')));assert pop['pages_rendered']==len(texts)
    result['consumer']['Poppler']=pop
    run([MU,'draw','-q','-r','300','-o',out/'mupdf-%02d.png',path]);data=run([MU,'draw','-q','-F','txt','-o','-',path]);(out/'mupdf.txt').write_bytes(data)
    n=len(list(out.glob('mupdf-*.png')));assert n==len(texts)
    result['consumer']['MuPDF']=dict(text_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),pages_rendered=n)
    result['qpdf']=run([ROOT/'tools/dist/bin/qpdf','--check',path]).decode()
    with pikepdf.open(path) as pdf:
        fonts={}
        for page in pdf.pages:
            for f in page.Resources.Font.values():
                if str(f.Subtype)!='/Type0':continue
                data=f.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes();fonts[hashlib.sha256(data).hexdigest()]=data
    result['OTS']=[]
    for sha,data in fonts.items():
        font=out/f'{sha}.ttf';font.write_bytes(data);text=run([ROOT/'tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',font,str(font)+'.sanitized']).decode();result['OTS'].append(dict(sha256=sha,result=text))
    (out/'consumer-results.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def compare(results):
    default=results[0];assert default['sha256']=='74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f'
    for result in results:
        result['text_equal_to_default']={
            'PDFium':result['consumer']['PDFium']['page_text']==default['consumer']['PDFium']['page_text'],
            'MuPDF':result['consumer']['MuPDF']['text_sha256']==default['consumer']['MuPDF']['text_sha256'],
            **{'Poppler_'+m:result['consumer']['Poppler'][m]['text_sha256']==default['consumer']['Poppler'][m]['text_sha256'] for m in ['default','layout','raw']}}
        result['pass']=all(result['text_equal_to_default'].values()) and all(c['pages_rendered']==default['pages'] for c in result['consumer'].values())
    return dict(schema='font04-R1-native-compatibility-v1',results=results,pass_all=all(r['pass'] for r in results),
        AdobeReader=dict(status='BLOCKED-ON-OWNER',required='Official Windows .exe or .msi installer for AdobeReader 26.00221.901; the macOS AdobeReader2600221901.dmg is not usable in Wine',wine_prefix_touched=False,display_used=None),PDFKit='Kit prepared; macOS execution deferred to R3',visual_review='Native render artifacts retained for independent review; successful rendering is not a blind visual judgment.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--default-only',action='store_true');args=parser.parse_args()
    paths=[DEFAULT] if args.default_only else [DEFAULT,LOCAL/'financial-R1-rust-cover-2.0.pdf',LOCAL/'financial-R1-rust-cover-1.5.pdf']
    if any(not p.is_file() for p in paths):raise SystemExit('Required Rust output missing; no comparison output is substituted.')
    results=[]
    for path in paths:
        cached=LOCAL/'R1-compatibility'/path.stem/'consumer-results.json'
        if cached.exists() and json.loads(cached.read_text())['sha256']==hashlib.sha256(path.read_bytes()).hexdigest():results.append(json.loads(cached.read_text()))
        else:results.append(inspect(path))
    result=compare(results);destination=BASE/('r1-default-compatibility.json' if args.default_only else 'r1-compatibility.json');destination.write_text(json.dumps(result,indent=2)+'\n');assert result['pass_all']
