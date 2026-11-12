"""Add neutral renderer-difference flags without making a glyph decision."""
import pathlib,json
p=pathlib.Path('/data/coding/scanweave/qualification/acr06/hvc41e/review-input.json');rows=json.loads(p.read_text())
for row in rows:
 row['flags']['renderer_pixels_outside_owned']=any(v['outside_owned_pixels']>0 for v in row['renderer_differences'].values())
 row['flags']['renderer_pixels_outside_two_pixel_envelope']=any(v['outside_two_pixel_envelope_pixels']>0 for v in row['renderer_differences'].values())
p.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
