from pathlib import Path
import json,subprocess,os,time,difflib
B=Path(__file__).resolve().parent;R=B.parents[1];rows=[];known=json.load(open(R/'qualification/pdf_packaging/cord-known-numeric-search.json'))
for name in ['cord-00','cord-05','history-02','history-03']:
 report=json.load(open(B/'baseline'/f'{name}.pdf.json'));psm=report['pages'][0]['selected_psm'];queries=next((x['queries'] for x in known if x['id']==name and x['arm']=='scanweave'),[])
 for renderer in ['pdfium','poppler']:
  texts={}
  for arm in ['baseline','q98','q100']:
   inp=B/'renders'/arm/f'{name}-{renderer}.png';out=B/'ocr'/f'{name}-{renderer}-{arm}';out.parent.mkdir(exist_ok=True);t=time.monotonic();cmd=['tesseract',str(inp),str(out),'-l','eng','--dpi','300','--psm',str(psm),'txt','tsv'];p=subprocess.run(cmd,env=dict(os.environ,OMP_THREAD_LIMIT='1'),capture_output=True,timeout=300);assert p.returncode==0;text=out.with_suffix('.txt').read_text();texts[arm]=text
   rows.append({'id':name,'renderer':renderer,'arm':arm,'command':cmd,'seconds':time.monotonic()-t,'text':text,'baseline_sequence_similarity':difflib.SequenceMatcher(None,texts['baseline'],text,autojunk=False).ratio(),'numeric_queries':[{'text':q['text'],'found':q['text'] in text} for q in queries]});(B/'rendered-ocr.json').write_text(json.dumps(rows,indent=2));print(name,renderer,arm,len(text),[q['text'] for q in rows[-1]['numeric_queries'] if q['found']],flush=True)
