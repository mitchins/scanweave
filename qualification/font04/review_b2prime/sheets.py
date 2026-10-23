import json
from pathlib import Path
from PIL import Image, ImageDraw
S = Path(__file__).parent; A = Path('qualification/font04/local/B2prime-blind-review/assets')
ids = json.load(open(S/'order.json')); out = S/'sheets'; out.mkdir(exist_ok=True)
CW, CH, PER = 860, 230, 16
def cell(i, pid):
    ims = [Image.open(A/f'{pid}-{t}.png').convert('L') for t in ('source', 'U', 'V')]
    w, h = ims[0].size; s = max(1, min(int(200/h), int(260/w)))
    c = Image.new('L', (CW, CH), 255); d = ImageDraw.Draw(c); d.text((4, 4), f'#{i}', fill=0)
    x = 40
    for lab, im in zip(('S', 'U', 'V'), ims):
        im = im.resize((w*s, h*s), Image.NEAREST); c.paste(im, (x, 20)); d.text((x, 4), lab, fill=0); d.rectangle([x-1, 19, x+w*s, 20+h*s], outline=128); x += w*s + 16
    return c
for sh in range(0, len(ids), PER):
    page = Image.new('L', (CW*2, CH*PER//2), 255)
    for j, pid in enumerate(ids[sh:sh+PER]):
        page.paste(cell(sh+j, pid), ((j % 2)*CW, (j//2)*CH))
    page.save(out/f'sheet{sh//PER:02d}.png')
print(len(ids), 'panels', (len(ids)+PER-1)//PER, 'sheets')
