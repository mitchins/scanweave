from pathlib import Path
import json
root=Path('/data/coding/scanweave/qualification/acr06/ink37')
rows=json.load((root/'report-comparison.json').open()); pdf={(x['document'],x['page']):x for x in json.load((root/'main-pdf-audit.json').open())}; mask={(x['document'],x['page']):x for x in json.load((root/'main-mask-index.json').open())}; pix={(x['document'],x['page'],x['engine']):x['changed_pixels'] for x in json.load((root/'pixel-diffs.json').open())}; ssim={(x['document'],x['page']):x for x in json.load((root/'source-ssim.json').open())}; sem={(x['document'],x['page']):x for x in json.load((root/'semantic-checks.json').open()) if 'pdfium_identical' in x}
lines=['| Page | Corner paper RGB / L | Foreground ink RGB / L | Prototype raster fallback | Foreground pixels (unchanged) | Vector mask pixels main → prototype | Changed pixels PDFium / Poppler / MuPDF | SSIM main → prototype | Text identical PDFium / Poppler |','|---|---|---|---|---:|---:|---:|---:|---|']
for x in rows:
 key=(x['document'],x['page']); p=pdf[key]; m=mask[key]; z=ssim[key]; q=sem[key]; v=x['main_coverage']['text_ink_px_vector']; w=x['candidate_coverage']['text_ink_px_vector']; diffs='/'.join(str(pix[(key[0],key[1],e)]) for e in ('pdfium','poppler','mupdf'))
 f=lambda v:'n/a' if v is None else f'{v:.4f}'
 lines.append(f"| {key[0]} {key[1]} | {p['paper_rgb']} / {p['paper_luminance']:.1f} | {p['text_fill_rgb']} / {p['text_luminance']:.1f} | {x['fallback']} | {m['pixel_count']} | {v} → {w} | {diffs} | {f(z['main'])} → {f(z['candidate'])} | {q['pdfium_identical']} / {q['poppler_identical']} |")
(root/'prototype-per-page.md').write_text('\n'.join(lines)+'\n')
