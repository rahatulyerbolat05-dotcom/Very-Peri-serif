#!/usr/bin/env python3
"""Лист «лучшие из старой разработки» (загруженный TTF InstrumentSerifCyr11) для букв, которых у нас ещё нет. Только для просмотра, ничего не берётся.
Запуск: python3 -I tools/old_best.py старый.ttf выход.png"""
import sys, json
from PIL import Image, ImageDraw, ImageFont
OLD, OUT = sys.argv[1:3]
SEL = "БИЖШЩЦЧЯЫЭКУХЧЦ"  # заглавные
SEL = list("БИЖЧЯШЩЦЭЫЮ") + list("кижцчвауф")
S = 170; k = S / 1000; CW, CH = 200, 235; COLS = 10; PAD = 30
LAB = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; LABB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f = ImageFont.truetype(OLD, S); fl = ImageFont.truetype(LAB, 17); fb = ImageFont.truetype(LABB, 26)
rows = (len(SEL) + COLS - 1) // COLS
im = Image.new("RGB", (PAD * 2 + COLS * CW, 110 + rows * CH + 40), "#f6f6f6"); d = ImageDraw.Draw(im)
d.text((PAD, 24), "Старая разработка: кандидаты, которых у нас ещё нет (только просмотр, ничего не берётся)", font=fb, fill="black")
for i, ch in enumerate(SEL):
    r, c = divmod(i, COLS); x0 = PAD + c * CW; y0 = 90 + r * CH
    d.rectangle([x0 + 6, y0 + 6, x0 + CW - 6, y0 + CH - 6], fill="white", outline="#ccc")
    b = y0 + 150
    for gy, col in ((0, "#e99"), (510, "#9bf")): d.line([(x0 + 14, b - gy * k), (x0 + CW - 14, b - gy * k)], fill=col)
    d.text((x0 + CW // 2, b), ch, font=f, fill="black", anchor="ms")
im.save(OUT); print(OUT, im.size)
