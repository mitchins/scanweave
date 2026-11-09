from pathlib import Path
from collections import Counter
import json, re, subprocess
import pypdfium2 as pdfium
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37')
paths=[root/'polarity37/historical-main.pdf',root/'gate37/historical-candidate.pdf']
pdfs=[pdfium.PdfDocument(p) for p in paths]
rows=[]
for i in range(5):
    row={'page':i+1}
    for engine in ('pdfium','poppler'):
        texts=[]
        for pdf,path in zip(pdfs,paths):
            if engine=='pdfium':
                pg=pdf[i]; tp=pg.get_textpage(); text=tp.get_text_range(); tp.close(); pg.close()
            else:
                text=subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(path),'-'],capture_output=True,check=True).stdout.decode()
            texts.append(text)
        toks=[re.findall(r'[^\W_]+',t,re.UNICODE) for t in texts]
        lost=Counter(toks[0])-Counter(toks[1]); added=Counter(toks[1])-Counter(toks[0])
        row[engine]={'identical':texts[0]==texts[1],'main_words':len(toks[0]),'candidate_words':len(toks[1]),'lost':dict(lost),'added':dict(added)}
    rows.append(row)
for p in pdfs:p.close()
out=Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/baseline-semantics-probe.json');out.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
for row in rows:
 print(row['page'],[(e,row[e]['identical'],row[e]['main_words'],row[e]['candidate_words'],sum(row[e]['lost'].values()),sum(row[e]['added'].values())) for e in ('pdfium','poppler')])
