import pathlib,json,pikepdf,collections,hashlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');out=[]
for mode in ('interior','border'):
 files=[R/'local/ink33r/historical.pdf',R/'local/hvc41b'/mode/'historical.pdf'];docs=[pikepdf.open(p) for p in files]
 for i in range(5):
  datas=[]
  for pdf in docs:
   p=pdf.pages[i];actual=[];shows=0;modes=collections.Counter();fontmap={}
   for ins in pikepdf.parse_content_stream(p):
    op=str(ins.operator);a=ins.operands
    if op=='BDC' and len(a)>1:
     try:
      if '/ActualText' in a[1]:actual.append(str(a[1]['/ActualText']))
     except (TypeError,ValueError):pass
    if op in ('Tj','TJ',"'",'"'):shows+=1
    if op=='Tr':modes[str(a[0])]+=1
   for k,f in p.Resources.get('/Font',{}).items():
    try:fontmap[str(k)]=hashlib.sha256(f['/ToUnicode'].read_bytes()).hexdigest() if '/ToUnicode' in f else None
    except Exception:fontmap[str(k)]='unreadable'
   datas.append({'actualtext':actual,'actualtext_count':len(actual),'text_shows':shows,'render_modes':dict(modes),'to_unicode_sha256':fontmap})
  a,b=[collections.Counter(x['actualtext']) for x in datas];out.append({'mode':mode,'page':i+1,'baseline':{k:v for k,v in datas[0].items() if k!='actualtext'},'probe':{k:v for k,v in datas[1].items() if k!='actualtext'},'actualtext_sequence_equal':datas[0]['actualtext']==datas[1]['actualtext'],'actualtext_baseline_only':sum((a-b).values()),'actualtext_probe_only':sum((b-a).values()),'baseline_only_examples':(a-b).most_common(5),'probe_only_examples':(b-a).most_common(5)})
 for d in docs:d.close()
(R/'hvc41b/semantic-structure.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print([(x['mode'],x['page'],x['actualtext_baseline_only'],x['actualtext_probe_only'],x['baseline']['text_shows'],x['probe']['text_shows']) for x in out])
