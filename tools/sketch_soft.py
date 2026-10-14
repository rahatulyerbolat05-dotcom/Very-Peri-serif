#!/usr/bin/env python3
"""Эскизы строчной ь (U+044C, softsign-cy): стойка с головкой и чаша справа (инструкция, раздел 7).
Чаша: нижняя чаша латинской a, отражённая по горизонтально (ниже и уже, чем у b). Хвост a не используется: крючки в этом шрифте бывают только справа.
Низ: стойка до базовой линии с опорной засечкой ı слева. Отброшены: засечки с двух сторон (замкнутая дырка у дна) и шпора как у b (грубый стык с дном чаши, нужна ручная отрисовка). Чаши от b и от p на всю высоту x-height отброшены: ь читается как «D».
Головка стойки: флажок ı или плоская засечка как у u.
Запуск: python3 -I tools/sketch_soft.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *

ref = Ref(); os.makedirs("build/soft", exist_ok=True); os.makedirs("data/soft", exist_ok=True)
from glyphparts import soft_sign
RSB = 30                                                       # поле справа: между o (25) и b (40), подобрать при кернинге
VAR = {"S3": ("flag", "S3  флажок"),
       "S4": ("u", "S4  как у u")}
items, meta = [], {}
for key, (kind, label) in VAR.items():
    path, right = soft_sign(ref, kind); path.simplify()
    adv = right + RSB; ttf = f"build/soft/IS-soft-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x44C, ttf); m.update(label=label, heads=kind, bowl_right=right)
    write_svg(path, adv, f"data/soft/{key}.svg"); write_glif(path, "softsign-cy", adv, 0x44C, f"data/soft/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ь", ["nьmьu", "ььь", "ь n ь i"], "docs/img/soft_S3_S4.png", col_w=760, size=1000, base=680)
json.dump(meta, open("data/soft/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["ymin"], v["ymax"]) for k, v in meta.items()})
