#!/usr/bin/env python3
"""Stack a source-pixel crop from each arm. Usage: detail.py <aligned dir> <page> x0 y0 x1 y1 <out.png> [zoom]"""
import sys
from PIL import Image, ImageDraw
d, page, x0, y0, x1, y1, out = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7]), sys.argv[7]
z = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
arms = ('source', 'scanweave', 'adobe', 'camscanner')
cr = [Image.open(f'{d}/{page}-{a}.png').crop((x0, y0, x1, y1)) for a in arms]
w, h = round((x1-x0)*z), round((y1-y0)*z)
sheet = Image.new('L', (w + 110, (h + 6) * 4), 255); dr = ImageDraw.Draw(sheet)
for k, (c, a) in enumerate(zip(cr, arms)):
    sheet.paste(c.resize((w, h), Image.LANCZOS if z < 1 else Image.NEAREST), (110, k*(h+6))); dr.text((4, k*(h+6) + h//2), a, fill=0)
sheet.save(out)
