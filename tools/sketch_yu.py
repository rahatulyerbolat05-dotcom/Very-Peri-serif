#!/usr/bin/env python3
"""Эскизы строчной ю (U+044E, yu-cy): стойка слева (ı), тонкая горизонталь на середине высоты x, овал справа (о оригинала).
Овал не касается стойки. Три длины соединения: ю1 55, ю2 80, ю3 105 (между правым краем стойки и левым краем овала).
Запуск: python3 -I tools/sketch_yu.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import yu_sign
ref = Ref(); os.makedirs("build/yu", exist_ok=True); os.makedirs("data/yu", exist_ok=True)
VAR = {"yu1": 55.0, "yu2": 80.0, "yu3": 105.0}
items, meta = [], {}
for key, link in VAR.items():
    path, info = yu_sign(ref, link=link); path.simplify()
    adv = round(info["xmax"] + 25)                                     # правое поле 25, как у о
    label = f"{key}  связь {link:g}"
    ttf = f"build/yu/IS-yu-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x44E, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/yu/{key}.svg"); write_glif(path, "yu-cy", adv, 0x44E, f"data/yu/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ю", ["nюnuюo", "HюHnюo", "юoюi юю"], "docs/img/yu_yu1-yu3.png", col_w=760, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/yu/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["contours"], v["ymin"], v["ymax"], v["stem_touches_oval"]) for k, v in meta.items()})
