"""PDF/font parsing, native PDFium search, and final artifact hashes."""
import sys,json,hashlib,subprocess,tempfile,re
from pathlib import Path
import pikepdf,pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
sys.path.insert(0,str(ROOT/'qualification'))
from tools_env import qpdf_bin,qpdf_env,ots_bin
paths=[B/str(d)/f for d in (300,600) for f in ('final.pdf','adobe.pdf')]
paths += sorted((B/'real'/'final').glob('*.pdf'))
rows=[]
for path in paths:
    check=subprocess.run([qpdf_bin(),'--check',str(path)],env=qpdf_env(),capture_output=True,text=True)
    p=pikepdf.open(path);fonts=[];seen=set()
    with tempfile.TemporaryDirectory() as tmp:
        for obj in p.objects:
            if isinstance(obj,pikepdf.Dictionary) and '/FontFile2' in obj:
                stream=obj.FontFile2
                if stream.objgen in seen:continue
                seen.add(stream.objgen);f=Path(tmp)/f'{len(fonts)}.ttf';f.write_bytes(stream.read_bytes());r=subprocess.run([ots_bin(),str(f)],capture_output=True,text=True);fonts.append({'bytes':f.stat().st_size,'ots_status':r.returncode,'ots_log':r.stdout+r.stderr})
    doc=pdfium.PdfDocument(str(path));searches=[]
    for pi,page in enumerate(doc):
        t=page.get_textpage();text=t.get_text_range();tokens=re.findall(r'[A-Za-z0-9]{3,}',text)
        token=tokens[0] if tokens else next((c for c in text if c.isalnum()),None)
        if token:
            search=t.search(token);searches.append({'page':pi,'token':token,'found':search.get_next() is not None})
    rows.append({'pdf':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'qpdf_status':check.returncode,'qpdf_log':check.stdout+check.stderr,'pages':len(p.pages),'fonts':fonts,'pdfium_native_search':searches})
    print(path.name,check.returncode,len(fonts),all(f['ots_status']==0 for f in fonts),flush=True)
(B/'validity.json').write_text(json.dumps(rows,indent=2)+'\n')
