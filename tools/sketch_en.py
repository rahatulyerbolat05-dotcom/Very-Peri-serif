#!/usr/bin/env python3
"""Эскизы строчной н (U+043D, en-cy): две стойки (ı оригинала) и перекладина по середине высоты x (H-образная, раздел 7 инструкции).
  n1: флажок ı на обеих стойках (F1), перекладина 27, центр 264 (51,8% по H) [основа по правилам];
  n2: плоские головки u на обеих стойках;
  n3: как n1, перекладина 30 (как у H);
  n4: по просьбе автора проекта 15.10.2026: левая стойка ı (флажок слева вверху, обычная ножка), правая как у латинской u (головка вверху, хвост-выход внизу справа).
Запуск: python3 -I tools/sketch_en.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import en_sign
ref = Ref(); os.makedirs("build/en", exist_ok=True); os.makedirs("data/en", exist_ok=True)
VAR = {"n1": dict(head="flag", bar_t=27.0), "n2": dict(head="u", bar_t=27.0), "n3": dict(head="flag", bar_t=30.0), "n4": dict(head="mix", bar_t=27.0)}
items, meta = [], {}
for key, kw in VAR.items():
    path, info = en_sign(ref, **kw); path.simplify()
    adv = round(info["xmax"] + (15 if kw["head"] == "mix" else 11))                                     # правое поле 11, как у n
    label = f"{key}  {kw['head']} {kw['bar_t']:g}"
    ttf = f"build/en/IS-en-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x43D, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/en/{key}.svg"); write_glif(path, "en-cy", adv, 0x43D, f"data/en/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "н", ["nнnuнo", "HнHnнu", "нnнi нн"], "docs/img/en_n1-n3.png", col_w=520, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/en/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["contours"], v["ymin"], v["ymax"]) for k, v in meta.items()})
