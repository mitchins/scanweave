import pathlib,subprocess,tempfile,json,collections,re,sys
import pypdfium2 as pdfium
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');rows=[]
for d in ('historical','receipts'):
 paths=[R/'local/ink33r'/f'{d}.pdf',R/'local/hvc41/trial2'/f'{d}.pdf'];docs=[pdfium.PdfDocument(p) for p in paths]
 for i in range(len(docs[0])):
  for engine in ('pdfium','poppler'):
   texts=[]
   for path,doc in zip(paths,docs):
    if engine=='pdfium':
     page=doc[i];tp=page.get_textpage();text=tp.get_text_range();tp.close();page.close()
    else:text=subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(path),'-'],check=True,stdout=subprocess.PIPE).stdout.decode('utf8')
    texts.append(text)
   a,b=[collections.Counter(re.findall(r'\S+',s)) for s in texts];rows.append({'document':d,'page':i+1,'engine':engine,'identical':texts[0]==texts[1],'baseline_word_tokens':sum(a.values()),'research_word_tokens':sum(b.values()),'baseline_only_token_count':sum((a-b).values()),'research_only_token_count':sum((b-a).values()),'baseline_only_examples':(a-b).most_common(10),'research_only_examples':(b-a).most_common(10),'note':'Whitespace tokenization is sensitive to ordering and joined/split words; differences are not a definitive missing-word count.'})
 for d0 in docs:d0.close()
(R/'hvc41/semantics.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
print([(x['document'],x['page'],x['engine'],x['baseline_only_token_count'],x['research_only_token_count']) for x in rows if not x['identical']])
