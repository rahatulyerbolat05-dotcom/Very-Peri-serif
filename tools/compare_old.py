#!/usr/bin/env python3
"""Сравнение наших основ с «старой разработкой» (загруженный TTF InstrumentSerifCyr11, мы из него ничего не берём): для каждой нашей буквы
три панели: наша, старая, наложение (наша чёрная, старая красная). Запуск: python3 -I tools/compare_old.py старый.ttf ваш_составной.ttf выход.png"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageChops
OLD, OURS, OUT = sys.argv[1:4]
LET = "ПНЛТЮЬЪЫШМ"  # п н Л т ю ь ъ ы ш м
LET = ["л", "м", "н", "п", "т", "ю", "ь", "ъ", "ы", "ш", "Л"]
S = 230; k = S / 1000; PW, PH = 250, 330; COLS = 2
LAB = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; LABB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
fo = ImageFont.truetype(OURS, S); fd = ImageFont.truetype(OLD, S); fl = ImageFont.truetype(LAB, 20); fb = ImageFont.truetype(LABB, 26)
rows = (len(LET) + COLS - 1) // COLS
W = 40 + COLS * (3 * PW + 30); H = 110 + rows * (PH + 20)
im = Image.new("RGB", (W, H), "#f6f6f6"); d = ImageDraw.Draw(im)
d.text((40, 24), "Наши основы и старая разработка (наша | старая | наложение: наша чёрная, старая красная)", font=fb, fill="black")
d.text((40, 66), "Старая взята только для сравнения, ничего из неё не берётся.", font=fl, fill="#666")
for i, ch in enumerate(LET):
    r, c = divmod(i, COLS); x0 = 40 + c * (3 * PW + 30); y0 = 110 + r * (PH + 20)
    base = y0 + 250
    for p in range(3):
        px = x0 + p * PW
        d.rectangle([px, y0, px + PW - 8, y0 + PH], fill="white", outline="#ccc")
        for gy, col in ((0, "#e99"), (510, "#9bf")): d.line([(px + 8, base - gy * k), (px + PW - 16, base - gy * k)], fill=col)
    d.text((x0 + PW // 2, base), ch, font=fo, fill="black", anchor="ms")
    d.text((x0 + PW + PW // 2, base), ch, font=fd, fill="black", anchor="ms")
    lay = Image.new("L", (PW, PH), 0); la = ImageDraw.Draw(lay)
    a = Image.new("L", (PW, PH), 0); ImageDraw.Draw(a).text((PW // 2, 250), ch, font=fo, fill=255, anchor="ms")
    b = Image.new("L", (PW, PH), 0); ImageDraw.Draw(b).text((PW // 2, 250), ch, font=fd, fill=255, anchor="ms")
    ov = Image.new("RGB", (PW - 8, PH), "white")
    ov.paste((220, 40, 40), mask=b.crop((0, 0, PW - 8, PH))); ov.paste((0, 0, 0), mask=ImageChops.multiply(a, Image.new("L", (PW, PH), 140)).crop((0, 0, PW - 8, PH)))
    im.paste(ov, (x0 + 2 * PW, y0))
    d.text((x0 + 6, y0 + PH - 30), f"{ch}", font=fb, fill="#2a7")
im.save(OUT); print(OUT, im.size)
