#!/usr/bin/env python3
"""Check qpdf, OTS, and text extraction for the three output arms."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
import pikepdf
import pypdfium2 as pdfium
from analyze import paths, HERE
from run import documents, ROOT, OUT

os.environ['LD_LIBRARY_PATH']=str(ROOT/'tools/dist/lib')+(':'+os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')
QPDF=ROOT/'tools/dist/bin/qpdf'; OTS=ROOT/'tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize'
def pdfium_text(p):
    doc=pdfium.PdfDocument(p); out=[]
    for page in doc:
        text=page.get_textpage(); out.append(text.get_text_range()); text.close();page.close()
    doc.close();return out

def poppler(p):
    return subprocess.run(['pdftotext','-enc','UTF-8',str(p),'-'],check=True,stdout=subprocess.PIPE).stdout

def check(p):
    result=subprocess.run([str(QPDF),'--check',str(p)],capture_output=True)
    fonts={}
    with pikepdf.open(p) as pdf:
        for page in pdf.pages:
            resources=page.get('/Resources',{}); fs=resources.get('/Font',{})
            for font in fs.values():
                for f in font.get('/DescendantFonts',[font]):
                    desc=f.get('/FontDescriptor',{})
                    for k in ('/FontFile','/FontFile2','/FontFile3'):
                        if k in desc:
                            data=desc[k].read_bytes();fonts[hashlib.sha256(data).hexdigest()]=data
    work=OUT/'functional';work.mkdir(parents=True,exist_ok=True)
    failed=[]
    for digest,data in fonts.items():
        pth=work/(digest+'.font');pth.write_bytes(data)
        r=subprocess.run([str(OTS),str(pth),str(pth)+'.sanitized'],capture_output=True)
        if r.returncode: failed.append(dict(hash=digest,stderr=r.stderr.decode(errors='replace')[:1000]))
    return dict(qpdf_returncode=result.returncode,qpdf_output=(result.stdout+result.stderr).decode(errors='replace')[-1500:],font_count=len(fonts),ots_failures=failed)

rows=[]
for name,_,_ in documents():
    while not (OUT/'corrected-only'/f'{name}.pdf.done').exists(): time.sleep(10)
    p=paths(name); text={a:(pdfium_text(p[a]),poppler(p[a])) for a in ('off','q3','corrected')}
    row=dict(document=name, extraction={a:dict(pdfium_equal_q3=text[a][0]==text['q3'][0],poppler_equal_q3=text[a][1]==text['q3'][1]) for a in text},checks={a:check(p[a]) for a in text})
    rows.append(row);print(name,flush=True)
(HERE/'functional.json').write_text(json.dumps(rows,indent=2)+'\n')
