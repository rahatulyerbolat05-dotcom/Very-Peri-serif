#!/usr/bin/env python3
"""Эскизы строчной ы (U+044B, yeru-cy) по рисунку автора проекта: ь + правая стойка от латинской u.
Правая стойка это стойка u целиком: плоская головка слева, стойка, стык с чашей, хвост-выход справа внизу (F3).
Чаша ь вливается в стойку (зазора нет), как у u чаша вливается в правую стойку.
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
OVERLAP = 6        # чаша ь (правый край 351) заходит в стойку на 6: вливается, а не касается
U_STEM_LEFT = 312  # левый край правой стойки u (измерено)
def right_stem(bowl_r):
    # правая стойка u: головка целиком (выше y=400 левее стойки чаши u нет, берём от x=250), ниже y=400 от x=290
    # (левее лежит чаша u, её не берём), со стыком и хвостом
    part = OR(AND(U, rect(250, 400, 500, 700)), AND(U, rect(290, -50, 500, 400)))
    return shift(part, bowl_r - OVERLAP - U_STEM_LEFT)

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
