#!/usr/bin/env python3
"""M1-A fixture generation: development fixtures for the one-page pipeline.

Each fixture: a 300-dpi-equivalent scan PNG + real Tesseract 5.5 hOCR (char boxes)
+ normalized OCR JSON produced by the actual import path (`m0-font-pdf hocr2json`).

Fixtures
  p11_touching   words whose characters rasterize as ONE component (rn, fi, ll, ss, digits)
  p12_disconnected dotted i/j, combining accents, kana with dakuten
  p13_nontext     text crossed by a rule, adjacent stamp and barcode (fallback cases)
  p14_noisy       skew + blur + noise + coloured paper, decorative P052 paragraph
  p15_decorative  URW Gothic (Comic Sans substitute; Comic Sans is operator-provided, never packaged)
  p16_statement   Nimbus Sans Mono amount table with light rules; financial tokens

NOTE: fixtures provide source-side ground truth only; the converter sees only the
scan + supplied OCR (never the original font/outline).
"""
import json
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "qualification", "fixtures", "probe")
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DEJAVU_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
IPA = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
P052 = "/usr/share/fonts/opentype/urw-base35/P052-Roman.otf"
URW_GOTHIC = "/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf"
NIMBUS_MONO = "/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Regular.otf"
DPI = 300.0
PT = 72.0 / DPI


def draw_word(draw, x, y, font, text, squeeze=0, fill=(20, 20, 20)):
    """Draw text char-by-char with optional negative advance (touching)."""
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bb = draw.textbbox((x, y), ch, font=font)
        x += (bb[2] - bb[0]) - squeeze
    return x


def pixel_hash(w, h, rgb):
    header = f"SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n".encode()
    import hashlib
    return hashlib.sha256(header + rgb).hexdigest()


def save_page(name, img, lang="eng"):
    d = os.path.join(FIX, name)
    os.makedirs(d, exist_ok=True)
    png = os.path.join(d, f"{name}.png")
    img.save(png)
    return d, png


def tesseract_and_normalize(d, png, name):
    stem = os.path.join(d, "tess")
    env = dict(
        os.environ,
        LD_LIBRARY_PATH=os.path.join(ROOT, "tools", "ext", "lib"),
        TESSDATA_PREFIX=os.path.join(ROOT, "tools", "ext", "share", "tessdata"),
    )
    subprocess.run(
        [os.path.join(ROOT, "tools", "ext", "bin", "tesseract"), png, stem,
         "-c", "hocr_char_boxes=1", "-l", "eng", "hocr"],
        capture_output=True, check=True, env=env,
    )
    hocr = stem + ".hocr"
    subprocess.run(
        [os.path.join(ROOT, "target", "debug", "m0-font-pdf"), "hocr2json",
         "--hocr", hocr, "--png", png, "--dpi", "300",
         "--out", os.path.join(d, f"{name}.ocr.json")],
        capture_output=True, check=True,
    )
    return json.load(open(os.path.join(d, f"{name}.ocr.json")))


def p11_touching():
    img = Image.new("RGB", (640, 300), (250, 249, 246))
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(DEJAVU, 64)
    draw_word(draw, 40, 30, f, "mini", squeeze=6)
    draw_word(draw, 40, 110, f, "glass", squeeze=5)
    draw_word(draw, 40, 190, f, "68", squeeze=12)
    draw_word(draw, 300, 30, f, "shift", squeeze=4)
    draw_word(draw, 300, 190, f, "fi", squeeze=2)
    d, png = save_page("p11_touching", img)
    return tesseract_and_normalize(d, png, "p11_touching")


def p12_disconnected():
    img = Image.new("RGB", (640, 300), (252, 251, 248))
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(DEJAVU, 72)
    draw_word(draw, 40, 30, f, "ij", squeeze=0)
    draw_word(draw, 40, 130, f, "!", squeeze=2)
    draw_word(draw, 160, 130, f, ":", squeeze=2)
    # combining accent: e then U+0301 manually offset → disconnected mark
    draw.text((300, 30), "e", font=f, fill=(20, 20, 20))
    draw.text((300 + 38, 2), "\u0301", font=f, fill=(20, 20, 20))
    fj = ImageFont.truetype(IPA, 72)
    draw_word(draw, 40, 210, fj, "ガパ")
    d, png = save_page("p12_disconnected", img)
    return tesseract_and_normalize(d, png, "p12_disconnected")


def p13_nontext():
    img = Image.new("RGB", (640, 360), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(DEJAVU_R, 44)
    fm = ImageFont.truetype(NIMBUS_MONO, 40)
    y = 30
    for i, line in enumerate(["Amount due 1,234.56", "Balance -42.00", "Ref INV-2026-0042"]):
        draw.text((40, y), line, font=fm if "Inv" in line or "Am" in line else f, fill=(20, 20, 20))
        y += 70
    # barcode-like bars next to the amount
    random.seed(20261014)
    bx = 470
    for _ in range(28):
        w = random.choice([2, 3, 5])
        draw.rectangle([bx, 30, bx + w, 110], fill=(20, 20, 20))
        bx += w + random.choice([2, 3, 4])
    # a stamp: rotated text block
    stamp = Image.new("RGB", (200, 100), (0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.text((8, 8), "PAID", font=ImageFont.truetype(DEJAVU, 56), fill=(255, 255, 255))
    stamp = stamp.rotate(18, expand=True, fillcolor=(0, 0, 0))
    img.paste(stamp, (420, 180))
    # a horizontal rule crossing the second text line
    draw.rectangle([20, 112, 620, 118], fill=(30, 30, 30))
    d, png = save_page("p13_nontext", img)
    return tesseract_and_normalize(d, png, "p13_nontext")


def p14_noisy():
    img = Image.new("RGB", (640, 320), (238, 231, 215))
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(P052, 50)
    draw_word(draw, 40, 30, f, "balance")
    draw_word(draw, 40, 100, f, "receipt")
    draw_word(draw, 40, 170, f, "1,234.56")
    draw_word(draw, 40, 235, f, "total due")
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    # skew
    img = img.transform(img.size, Image.Transform.AFFINE, (1, -0.08, 40, 0, 1, 0), fillcolor=(238, 231, 215))
    # uneven ink: sparse dark speckle
    random.seed(4242)
    px = img.load()
    for _ in range(2400):
        x, y = random.randint(0, 639), random.randint(0, 319)
        v = random.randint(20, 120)
        px[x, y] = (v, v, v)
    d, png = save_page("p14_noisy", img)
    return tesseract_and_normalize(d, png, "p14_noisy")


def p15_decorative():
    img = Image.new("RGB", (640, 320), (248, 247, 242))
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(URW_GOTHIC, 72)
    draw_word(draw, 40, 20, f, "Total")
    draw_word(draw, 40, 110, f, "42.00")
    draw_word(draw, 360, 20, f, "cafe")
    draw_word(draw, 360, 110, f, "menu")
    d, png = save_page("p15_decorative", img)
    return tesseract_and_normalize(d, png, "p15_decorative")


def p16_statement():
    img = Image.new("RGB", (640, 400), (253, 253, 252))
    draw = ImageDraw.Draw(img)
    fm = ImageFont.truetype(NIMBUS_MONO, 34)
    rows = [("Item", "Amount"), ("Coffee", "3.50"), ("Scone", "2.40"),
            ("Total", "5.90"), ("Tax", "0.48"), ("Due", "6.38")]
    y = 40
    for i, (k, v) in enumerate(rows):
        draw.text((40, y), k, font=fm, fill=(20, 20, 20))
        draw.text((400, y), v, font=fm, fill=(20, 20, 20))
        if i == 0 or i == 3:
            draw.rectangle([30, y + 42, 610, y + 44], fill=(150, 150, 150))  # light rule
        y += 60
    d, png = save_page("p16_statement", img)
    return tesseract_and_normalize(d, png, "p16_statement")


def main():
    for gen in (p11_touching, p12_disconnected, p13_nontext, p14_noisy,
                p15_decorative, p16_statement):
        ocr = gen()
        chars = sum(len(s["text"]) for s in ocr["spans"])
        print(f"{ocr['page_id']}: {len(ocr['spans'])} spans, {chars} chars")


if __name__ == "__main__":
    main()
