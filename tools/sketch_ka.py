#!/usr/bin/env python3
"""к (U+043A) и ka-cy.short (кончик верхней ветви укорочен) по docs/glyphs/ka.md: ка это латинская k оригинала без выносного элемента + флажок ı.
Запуск: python3 -I tools/sketch_ka.py (после tools/fetch_reference.sh)"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import ka_sign
from PIL import Image, ImageDraw, ImageFont
ref = Ref(); os.makedirs("data/ka", exist_ok=True); os.makedirs("build/ka", exist_ok=True)
out = {}
for key, sh, cp, gname in (("ka", False, 0x43A, "ka-cy"), ("ka_short", True, 0xE003, "ka-cy.short")):
    p = ka_sign(ref, short=sh); adv = round(p.bounds[2] + 11)
    write_svg(p, adv, f"data/ka/{key}.svg"); write_glif(p, gname, adv, cp, f"data/ka/{key}.glif")
    install(ref.ttf, p, adv, 0x43A, f"build/ka/{key}.ttf")                    # для показа на основной кодовой точке
    nodes = sum(1 for _ in p.segments); out[key] = {"adv": adv, "bounds": [round(v, 1) for v in p.bounds], "contours": len(list(p.contours)), "segments": nodes}
json.dump(out, open("data/ka/meta.json", "w"), ensure_ascii=False, indent=1)
lab = ImageFont.truetype(LABEL_BOLD, 22); S = 700; sc = S / 1000; W, H = 640, 860
im = Image.new("RGB", (W * 2, H), "white"); d = ImageDraw.Draw(im)
for i, (key, l) in enumerate((("ka", "к"), ("ka_short", "ka-cy.short (перед буквой с головкой слева вверху)"))):
    f = ImageFont.truetype(f"build/ka/{key}.ttf", S); b = 470
    for gy, c in ((0, "#e99"), (510, "#9bf")): d.line([(i * W + 10, b - gy * sc), (i * W + W - 10, b - gy * sc)], fill=c)
    d.text((i * W + 60, b), "к", font=f, fill="black", anchor="ls"); d.text((i * W + 10, 10), l, font=lab, fill="#444")
    f2 = ImageFont.truetype(f"build/ka/{key}.ttf", 130)
    for j, s in enumerate(("кnк", "кHкp", "кккк")): d.text((i * W + 30, 540 + j * 100), s, font=f2, fill="black")
im.save("docs/img/ka_ka_short.png")
tips = Image.new("RGB", (540 * 3, 340), "white")
for i, (p_, ch, l) in enumerate(((ref.ttf, "k", "оригинал k"), ("build/ka/ka.ttf", "к", "наша к"), ("build/ka/ka_short.ttf", "к", "наша short"))):
    f = ImageFont.truetype(p_, 1400); k = 1.4; t = Image.new("RGB", (520, 340), "white")
    ImageDraw.Draw(t).text((-230 * k, 30 + 516 * k), ch, font=f, fill="black", anchor="ls"); tips.paste(t, (i * 540, 0)); ImageDraw.Draw(tips).text((i * 540 + 8, 306), l, font=lab, fill="#e55")
tips.save("docs/img/ka_tip_zoom.png"); print(out)
