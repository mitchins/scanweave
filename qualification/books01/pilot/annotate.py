#!/usr/bin/env python3
"""Carry source type and accepted DPI confidence into each result row."""
import json,pathlib
P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot/results';lock=json.loads((P/'sources.lock.json').read_text())['pages']
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
for name in ['runs.json','path-equivalence.json','adobe-repeat.json','alignment.json']:
 p=Q/name;x=json.loads(p.read_text())
 for id,v in x.items():
  if id in lock:
   v['dpi_confidence']=lock[id]['dpi_evidence']['confidence'];v['source_type']=lock[id]['source_type']
   for row in v.get('rows',{}).values():row['dpi_confidence']=v['dpi_confidence'];row['source_type']=v['source_type']
 write(p,x)
p=Q/'frozen-ocr-index.json';x=json.loads(p.read_text())
for id,v in x['pages'].items():v['dpi_confidence']=lock[id]['dpi_evidence']['confidence'];v['source_type']=lock[id]['source_type']
write(p,x)
for name in ['search-layout.json','extraction-diagnostics.json']:
 p=Q/name;x=json.loads(p.read_text())
 for id,rows in x.items():
  for row in rows.values():row['dpi_confidence']=lock[id]['dpi_evidence']['confidence'];row['source_type']=lock[id]['source_type']
 write(p,x)
for name in ['render-costs.json','visual.json']:
 p=Q/name;x=json.loads(p.read_text())
 for id,rows in x.items():
  for row in rows.values():
   for res in row.values():
    for v in res.values():v['dpi_confidence']=lock[id]['dpi_evidence']['confidence'];v['source_type']=lock[id]['source_type']
 write(p,x)
