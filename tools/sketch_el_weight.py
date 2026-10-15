#!/usr/bin/env python3
"""Л (L3, 12°/4°) в трёх весах рядом с латиницей эталона: W1 по шрифту (30/71/27), W2 и W3 плотнее.
Проверка ощущения автора проекта, что линии Л тонкие. Запуск: python3 -I tools/sketch_el_weight.py"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import el_sign
ref = Ref(); os.makedirs("build/el", exist_ok=True)
W = {"W1": (30.0, 71.0, 27.0), "W2": (38.0, 78.0, 32.0), "W3": (46.0, 86.0, 38.0)}
items = []
for key, (tl, tr, tt) in W.items():
    path, info = el_sign(ref, 12.0, 4.0, a=128.0, b=110.0, t_l=tl, t_r=tr, t_top=tt); path.simplify()
    adv = info["xmax"] + 19; ttf = f"build/el/IS-elw-{key}.ttf"
    install(ref.ttf, path, adv, 0x41B, ttf)
    items.append((f"{key}  {tl:g} / {tr:g} / {tt:g}", ttf, adv))
render(items, "Л", ["HЛAЛV", "ЛNЛMЛO", "AЛHVЛN"], "docs/img/el_weights.png", col_w=700, size=700, base=760, guides=(0, 720))
