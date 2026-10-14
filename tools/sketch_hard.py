#!/usr/bin/env python3
"""Эскизы строчной ъ (U+044A, hardsign-cy): ь + верхняя левая перекладина с засечкой (инструкция, раздел 7).
Перекладина это удлинённая головка u (S4), на левом конце засечка вниз:
  K1: без засечки (плоский кончик), K2: засечка 70, K3: засечка 120 (ближе к T).
Длина перекладины слева от стойки около 105 (догадка, в 2 раза длиннее головки u): ОТКРЫТО.
Запуск: python3 -I tools/sketch_hard.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import hard_sign

ref = Ref(); os.makedirs("build/hard", exist_ok=True); os.makedirs("data/hard", exist_ok=True)
RSB = 30
VAR = {"K1": (0, "K1  без засечки"), "K2": (70, "K2  засечка 70"), "K3": (120, "K3  засечка 120")}
items, meta = [], {}
for key, (depth, label) in VAR.items():
    path, bowl_r = hard_sign(ref, depth); path.simplify()
    adv = bowl_r + RSB; ttf = f"build/hard/IS-hard-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x44A, ttf); m.update(label=label, serif_depth=depth, bowl_right=bowl_r, contours=len(list(path.contours)))
    write_svg(path, adv, f"data/hard/{key}.svg"); write_glif(path, "hardsign-cy", adv, 0x44A, f"data/hard/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ъ", ["nъmъu", "ъъъ", "ъ n ъ i"], "docs/img/hard_K1_K3.png", col_w=700, size=900, base=640)
json.dump(meta, open("data/hard/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["ymax"], v["contours"]) for k, v in meta.items()})
