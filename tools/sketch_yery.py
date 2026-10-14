#!/usr/bin/env python3
"""Эскизы строчной ы (U+044B, yeru-cy) по рисунку автора проекта: ь + правая стойка от латинской u.
Правая стойка это стойка u: плоская головка слева, прямая стойка, острая ножка и хвост-выход справа внизу (F3).
Между чашей ь и стойкой зазор 44 (как на рисунке); левый край стойки прямой до острой ножки.
Левая часть берётся из общего кода ь (tools/glyphparts.py).
  Y1: ь = S3 (флажок), правая стойка с головкой u (как на рисунке слева).
  Y2: ь = S4 (головка u), обе головки плоские (как на рисунке справа).
Запуск: python3 -I tools/sketch_yery.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import soft_sign

ref = Ref(); os.makedirs("build/yery", exist_ok=True); os.makedirs("data/yery", exist_ok=True)
U = ref.glyph("u")
GAP = 44           # зазор между правым краем чаши ь (351) и левым краем стойки: снят с рисунка автора проекта (около 44)
U_STEM_LEFT = 312  # левый край правой стойки u (измерено)
def right_stem(bowl_r):
    # стойка u: головка целиком (выше y=400 левее стойки чаши u нет, берём от x=250);
    # ниже y=400 левый край прямой, от x=312: без наплыва там, где у u в стойку вливается её чаша; ножка и хвост-выход остаются
    # левый край ниже: 312 до y=150, затем плавное сужение до 317 к y=62 (там у u начинается прямой край ножки x=317, измерено);
    # прямой срез по 312 давал ступеньку в 5 единиц на стыке
    taper = poly((U_STEM_LEFT, 400), (U_STEM_LEFT, 150), (317, 62), (317, -50), (500, -50), (500, 400))
    part = OR(AND(U, rect(250, 400, 500, 700)), AND(U, taper))
    return shift(part, bowl_r + GAP - U_STEM_LEFT)

VAR = {"Y1": ("flag", "Y1  ь с флажком, стойка как у u"), "Y2": ("u", "Y2  обе головки как у u")}
items, meta = [], {}
for key, (kind, label) in VAR.items():
    left, bowl_r = soft_sign(ref, kind)
    path = OR(left, right_stem(bowl_r)); path.simplify()
    ttf = f"build/yery/IS-yery-{key}.ttf"
    m = install(ref.ttf, path, 0, 0x44B, ttf); adv = m["xmax"] + 15           # rsb 15, как у u
    m = install(ref.ttf, path, adv, 0x44B, ttf); m.update(label=label, heads=kind, bowl_right=bowl_r, contours=len(list(path.contours)))
    write_svg(path, adv, f"data/yery/{key}.svg"); write_glif(path, "yeru-cy", adv, 0x44B, f"data/yery/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ы", ["nыmыu", "ыыы", "ы n ы i"], "docs/img/yery_Y1_Y2.png", col_w=860, size=900, base=640)
json.dump(meta, open("data/yery/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["ymax"], v["contours"]) for k, v in meta.items()})
