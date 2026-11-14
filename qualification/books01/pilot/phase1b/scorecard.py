#!/usr/bin/env python3
"""Join geometry, native/aligned fidelity, OCR and search without source text."""
import json,pathlib
P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';R=Q/'results';base=R/'phase1b';f=json.loads((base/'fidelity.json').read_text())['pages'];o=json.loads((base/'line-ocr.json').read_text())['pages'];s=json.loads((R/'search-layout.json').read_text());out={}
for id,rows in f.items():
 entry={'gt_type':o[id]['gt_type'],'gt_lines':o[id]['gt_lines'],'known_gt_characters':o[id]['known_gt_characters'],'frozen_hocr_line_metrics':o[id]['frozen_hocr'],'rows':{}}
 for row,renderers in rows.items():
  q=o[id]['rows'][row];old=s[id][row]['search'];entry['rows'][row]={'adobe_label':q['adobe_label'],'dpi_confidence':q['dpi_confidence'],'source_type':q['source_type'],'visual_by_renderer_and_dpi':renderers,'ocr':q,'original_search':{'positive_hits':old['positive_hits'],'positive_count':old['positive_count'],'false_hits':old['false_hits'],'control_count':old['control_count']}}
 out[id]=entry
(base/'scorecard.json').write_text(json.dumps({'note':'Native and aligned scores shown separately; no local/elastic warps. Provisional defect assessments are not human adjudications.','pages':out},indent=2)+'\n')
