#!/usr/bin/env python3
"""Validate internal consistency and all evidence hashes for the #33 rerun."""
import hashlib,json,pathlib
E=pathlib.Path('/data/coding/scanweave/qualification/acr06/ink33r');read=lambda n:json.loads((E/n).read_text());checks={}
p=read('provenance.json');checks['all_five_pdf_hashes']=len(p['documents'])==5 and all(x['matches_reference'] for x in p['documents'].values())
o=read('ocr-provenance.json');checks['all_32_ocr_text_and_boxes_equal']=len(o)==32 and all(x['parsed_text_boxes_equal'] for x in o)
f=read('fill-local.json');checks['32_fill_pages_and_no_flags']=len(f)==32 and not any(v['above_page_local_paper'] for r in f for v in r['visible_fills']) and not any(r['visible_object_above_local_count'] for r in f)
pair=read('paired-lines.json');checks['surviving_lines_unchanged']=sum(r['common_lines'] for r in pair)==420 and not any(r['metric_differences'] for r in pair) and sum(len(r['old_only']) for r in pair)==25 and not any(r['new_only'] for r in pair)
checks['old_mixed_reconstructed']=read('old-reconstruction-check.json')['mismatch_count']==0
p=read('panel-index.json');checks['panel_hashes']=all(hashlib.sha256(pathlib.Path(x['file']).read_bytes()).hexdigest()==x['sha256'] for x in p['sheets']);checks['60_indexed_lines']=len(p['items'])==60
chars=read('character-index.json');checks['character_hashes']=all(hashlib.sha256((E/x['file']).read_bytes()).hexdigest()==x['sha256'] and (E/x['file']).stat().st_size<1000000 for x in chars);checks['character_records']=sum(x['records'] for x in chars)==20990
checks['all_counterfactual_text_equal']=all(all(read(f'summary-{d}.json')['extraction_equal'].values()) for d in ('historical','financial','mixed','receipts','forms'))
checks['edit_validation']=set(read('edit-validation.json'))=={'historical','financial','mixed','receipts','forms'}
checks['evidence_files_under_1mb']=not any(p.stat().st_size>=1000000 for p in E.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
(E/'validation.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
if not all(checks.values()):raise SystemExit('evidence validation failed')
