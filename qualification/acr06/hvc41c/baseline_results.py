import json,pathlib,hashlib,re
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41c/default';B=R/'local/ink33r';out=[]
for doc in ('historical','receipts','financial','mixed','forms'):
 a=B/f'{doc}.pdf';b=L/f'{doc}.pdf';t=(L/f'{doc}.time').read_text();log=(L/f'{doc}.log').read_text();ha=hashlib.sha256(a.read_bytes()).hexdigest();hb=hashlib.sha256(b.read_bytes()).hexdigest();q=json.loads((B/f'{doc}.pdf.json').read_text());out.append({'document':doc,'pages':len(q['pages']),'baseline_bytes':a.stat().st_size,'locked_replay_bytes':b.stat().st_size,'baseline_sha256':ha,'locked_replay_sha256':hb,'byte_identical':ha==hb,'tesseract_stub_not_invoked':'Tesseract stub not invoked' in log,'wall_time':re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)',t).group(1),'peak_rss_kib':int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',t).group(1))})
assert all(r['byte_identical'] and r['tesseract_stub_not_invoked'] for r in out)
(R/'hvc41c/baseline-results.json').write_text(json.dumps(out,indent=2)+'\n');print('pages',sum(x['pages'] for x in out),'all byte-identical and stub unused')
