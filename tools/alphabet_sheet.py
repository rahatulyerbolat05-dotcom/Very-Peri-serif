#!/usr/bin/env python3
"""Сводная страница «азбука»: все 66 букв русского ядра в алфавитном порядке (прописные и строчные), готовые из data/alphabet.json рисуются
основами из репозитория (GLIF), остальные серым пунктиром. Видно, что сделано и что осталось.
Запуск: python3 -I tools/alphabet_sheet.py [выход.png] (после tools/fetch_reference.sh)"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import pathops
from pathops import Path
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from sketchlib import Ref, install, LABEL, LABEL_BOLD
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/img/alphabet_status.png"
CFG = json.load(open("data/alphabet.json", encoding="utf-8"))
UP = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"; LOW = UP.lower()
DONE = CFG["done"]; LAT = set(CFG["latin_donor"])
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

def load(path):
    class G: pass
    g = G(); g.width = 0; p = Path()
    readGlyphFromString(open(path, encoding="utf-8").read(), g, PointToSegmentPen(p.getPen())); return p, g.width

ref = Ref(); os.makedirs("build/alphabet", exist_ok=True)
cur = ref.ttf; n = 0
for ch, (path, label) in DONE.items():
    p, w = load(path); out = f"build/alphabet/step{n}.ttf"; install(cur, p, w, ord(ch), out); cur = out; n += 1
font_path = cur
S = 150                                          # размер глифа, px на em
k = S / 1000
CW, CH = 190, 215                                # ячейка
COLS = 11; PAD = 40; HEAD = 190
rows_blocks = [("ПРОПИСНЫЕ", UP), ("строчные", LOW)]
W = PAD * 2 + COLS * CW
H = HEAD + sum(60 + 3 * CH for _ in rows_blocks) + 70
im = Image.new("RGB", (W, H), "#f6f6f6"); d = ImageDraw.Draw(im)
f_title = ImageFont.truetype(LABEL_BOLD, 40); f_sub = ImageFont.truetype(LABEL, 24); f_small = ImageFont.truetype(LABEL, 18)
f_block = ImageFont.truetype(LABEL_BOLD, 26); f_mine = ImageFont.truetype(font_path, S); f_ph = ImageFont.truetype(SERIF, int(S * 0.78))
done_up = sum(1 for c in UP if c in DONE); done_low = sum(1 for c in LOW if c in DONE); total = len(UP) + len(LOW)
nd = done_up + done_low
d.text((PAD, 30), "Very Peri Serif: русское ядро (66 букв)", font=f_title, fill="black")
d.text((PAD, 86), f"сделано {nd} из {total}, осталось {total - nd}: прописных {done_up}/33, строчных {done_low}/33", font=f_sub, fill="#333")
bar_x, bar_y, bar_w = PAD, 128, W - 2 * PAD
d.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 14], outline="#999", fill="white"); d.rectangle([bar_x, bar_y, bar_x + int(bar_w * nd / total), bar_y + 14], fill="#2a7")
d.rectangle([PAD, 156, PAD + 22, 178], fill="#fff", outline="#2a7", width=3); d.text((PAD + 32, 156), "сделана (основа из репозитория)", font=f_small, fill="#333")
d.rectangle([PAD + 440, 156, PAD + 462, 178], fill="#fff", outline="#bbb"); d.text((PAD + 472, 156), "не сделана", font=f_small, fill="#333")
d.text((PAD + 640, 156), "лат. = есть латинский двойник (проще всего)", font=f_small, fill="#888")
y = HEAD
for title, letters in rows_blocks:
    d.text((PAD, y + 14), title, font=f_block, fill="black"); y += 60
    for i, ch in enumerate(letters):
        r, c = divmod(i, COLS); x0 = PAD + c * CW; y0 = y + r * CH
        ok = ch in DONE
        d.rectangle([x0 + 6, y0 + 6, x0 + CW - 6, y0 + CH - 6], fill="white", outline="#2a7" if ok else "#ccc", width=3 if ok else 1)
        base = y0 + 125
        for gy, col in ((0, "#e99"), (510, "#9bf")):
            yy = base - gy * k; d.line([(x0 + 14, yy), (x0 + CW - 14, yy)], fill=col, width=1)
        if ok:
            d.text((x0 + CW // 2, base), ch, font=f_mine, fill="black", anchor="ms")
            d.text((x0 + CW // 2, y0 + CH - 30), DONE[ch][1], font=f_small, fill="#2a7", anchor="ms")
        else:
            d.text((x0 + CW // 2, base), ch, font=f_ph, fill="#c8c8c8", anchor="ms")
            if ch in LAT: d.text((x0 + CW // 2, y0 + CH - 30), "лат.", font=f_small, fill="#aaa", anchor="ms")
    y += 3 * CH
d.text((PAD, H - 50), "Источник: data/alphabet.json (основы), контуры data/*/*.glif; тонкие линии: базовая 0 и x-height 510. Серые буквы нарисованы запасным шрифтом, не наши.", font=f_small, fill="#888")
im.save(OUT); print(OUT, im.size, f"{nd}/{total}")
