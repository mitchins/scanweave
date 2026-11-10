import hashlib,json,pathlib,re
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');rows=[]
for d in ('historical','receipts','financial','mixed','forms'):
 b=R/'local/ink33r'/f'{d}.pdf';c=R/'local/hvc41/trial2'/f'{d}.pdf';r={'document':d}
 for name,path,tf in [('baseline',b,R/'local/ink33r'/f'{d}.time'),('research',c,R/'local/hvc41/trial2'/f'{d}.time')]:
  t=tf.read_text();r[name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'elapsed':re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)',t).group(1),'peak_rss_kib':int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',t).group(1))}
 r['identical']=r['baseline']['sha256']==r['research']['sha256'];rows.append(r)
(R/'hvc41/results.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r['document'],r['baseline']['bytes'],r['research']['bytes'],'identical',r['identical'],'baseline',r['baseline']['elapsed'],r['baseline']['peak_rss_kib'],'research',r['research']['elapsed'],r['research']['peak_rss_kib'])
