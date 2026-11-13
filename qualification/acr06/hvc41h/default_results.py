"""Record complete-document byte identity and no-OCR evidence for default replay."""
import pathlib,json,hashlib,re
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41h';O=L/'default';E=R/'hvc41h';rows=[]
for doc in ['historical','receipts','financial','mixed','forms']:
 b=R/'local/ink33r'/f'{doc}.pdf';p=O/f'{doc}.pdf';status=(O/f'{doc}.status').read_text().strip();log=(O/f'{doc}.log').read_text();tim=(O/f'{doc}.time').read_text();sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest();wall=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(.+)',tim);rss=re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',tim);side=json.loads((R/'local/ink33r'/f'{doc}.pdf.json').read_text());rows.append({'document':doc,'pages':len(side['pages']),'status':status,'baseline_bytes':b.stat().st_size,'replay_bytes':p.stat().st_size,'baseline_sha256':sha(b),'replay_sha256':sha(p),'tesseract_stub_not_invoked':'Tesseract stub not invoked' in log,'wall_time':wall.group(1) if wall else None,'peak_rss_kib':int(rss.group(1)) if rss else None})
if not all(x['status']=='IDENTICAL' and x['baseline_sha256']==x['replay_sha256'] and x['tesseract_stub_not_invoked'] for x in rows):raise SystemExit('default replay verification failed')
if (L/'ocr-invoked').exists() or (L/'outer-ocr-invoked').exists() or (L/'forbidden-ocr-invoked').exists():raise SystemExit('OCR stub marker found')
(E/'default-replay.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
