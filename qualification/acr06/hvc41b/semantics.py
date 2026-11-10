import json,pathlib,collections,subprocess,re
import pypdfium2 as pdfium
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';L=R/'local/hvc41b';B=R/'local/ink33r';out=[]
for mode in ('interior','border'):
 src=B/'historical.pdf';dst=L/mode/'historical.pdf';reports=[json.loads((B/'historical.pdf.json').read_text()),json.loads((L/mode/'historical.pdf.json').read_text())];docs=[pdfium.PdfDocument(str(src)),pdfium.PdfDocument(str(dst))]
 for i in range(len(docs[0])):
  for engine in ('pdfium','poppler'):
   texts=[]
   for path,doc in zip((src,dst),docs):
    if engine=='poppler':txt=subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(path),'-'],stdout=subprocess.PIPE,check=True).stdout.decode('utf8')
    else:
     page=doc[i];tp=page.get_textpage();txt=tp.get_text_range();tp.close();page.close()
    texts.append(txt)
   a,b=[collections.Counter(re.findall(r'\S+',t)) for t in texts];out.append({'mode':mode,'page':i+1,'engine':engine,'identical':texts[0]==texts[1],'frozen_hocr_identical':reports[0]['pages'][i]['hocr_sha256']==reports[1]['pages'][i]['hocr_sha256'],'baseline_only_token_count':sum((a-b).values()),'probe_only_token_count':sum((b-a).values()),'baseline_only_examples':(a-b).most_common(8),'probe_only_examples':(b-a).most_common(8),'note':'Whitespace tokenization is sensitive to joining, splitting and ordering; not a definitive lost-word count.'})
 for d in docs:d.close()
(E/'semantics-probes.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print([(x['mode'],x['page'],x['engine'],x['baseline_only_token_count'],x['probe_only_token_count']) for x in out if not x['identical']])
