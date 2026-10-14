#!/usr/bin/env python3
"""Эскизы строчной ы (U+044B, yeru-cy) = ь (S3, выбрана автором проекта) + правая стойка ı (инструкция, раздел 7).
Левая часть берётся из общего кода ь (tools/glyphparts.py), чтобы ь и ы не расходились.
Параметр: зазор между правой границей чаши и стойкой.
  Y1: 182, как контрформа n (по инструкции: «расстояние между ь и стойкой равно промежутку между стойками н»).
  Y2: 109 = поле справа у ь (30) + отступ стойки ı от края глифа (79): естественный зазор пары «ь» и «ı».
Запуск: python3 -I tools/sketch_yery.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import soft_sign

ref = Ref(); os.makedirs("build/yery", exist_ok=True); os.makedirs("data/yery", exist_ok=True)
I = ref.glyph("dotlessi")                                   # правая стойка: флажок и обе опорные засечки (стойка 79–147)
VAR = {"Y1": (182, "Y1  зазор 182 (как у n)"), "Y2": (109, "Y2  зазор 109 (естественный)")}
items, meta = [], {}
for key, (gap, label) in VAR.items():
    left, bowl_r = soft_sign(ref, "flag")
    path = OR(left, shift(I, bowl_r + gap - 79)); path.simplify()
    ttf = f"build/yery/IS-yery-{key}.ttf"
    m = install(ref.ttf, path, 0, 0x44B, ttf); adv = m["xmax"] + 11           # rsb 11, как у ı
    m = install(ref.ttf, path, adv, 0x44B, ttf); m.update(label=label, gap=gap, bowl_right=bowl_r)
    write_svg(path, adv, f"data/yery/{key}.svg"); write_glif(path, "yeru-cy", adv, 0x44B, f"data/yery/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ы", ["nыmыu", "ыыы", "ы n ы i"], "docs/img/yery_Y1_Y2.png", col_w=840, size=900, base=640)
json.dump(meta, open("data/yery/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["ymin"], v["ymax"], len(list(path.contours))) for k, v in meta.items()})
