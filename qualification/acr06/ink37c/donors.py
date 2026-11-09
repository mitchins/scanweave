from pathlib import Path
import json
base=Path('/data/coding/scanweave/qualification/acr06/local');rows=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 a=json.load(open(base/'ink37c'/f'lossless-{doc}.pdf.json'));b=json.load(open(base/'ink37c/detail-gate'/f'{doc}.pdf.json'))
 for i,(x,y) in enumerate(zip(a['conversion']['page_reports'],b['conversion']['page_reports'])):
  rows.append({'document':doc,'page':i+1,'reconstruction_equal':x['reconstruction']==y['reconstruction'],'semantic_owner_equal':x['semantic_owner']==y['semantic_owner'],'polarity_inverted_equal':x['polarity_inverted']==y['polarity_inverted'],'visible_occurrences_equal':x['polarity_visible_occurrences']==y['polarity_visible_occurrences']})
Path('/data/coding/scanweave/qualification/acr06/ink37c/donors.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:
 if not all(r[k] for k in ('reconstruction_equal','semantic_owner_equal','polarity_inverted_equal','visible_occurrences_equal')):print(r)
