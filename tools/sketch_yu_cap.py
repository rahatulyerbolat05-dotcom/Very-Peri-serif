#!/usr/bin/env python3
"""Эскизы заглавной Ю (U+042E, yu-cy): стойка H слева (без перекладины), тонкая горизонталь и овал О оригинала справа, овал не касается стойки.
Три длины связи как у строчной ю: Yu1 55, Yu2 80, Yu3 105 (между правым краем стойки и левым краем овала).
Запуск: python3 -I tools/sketch_yu_cap.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import yu_cap_sign
ref = Ref(); os.makedirs("build/yu_cap", exist_ok=True); os.makedirs("data/yu_cap", exist_ok=True)
items, meta = [], {}
for key, link in (("Yu1", 55.0), ("Yu2", 80.0), ("Yu3", 105.0)):
    path, info = yu_cap_sign(ref, link); adv = info["adv"]
    label = f"{key}  связь {link:g}"
    ttf = f"build/yu_cap/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x42E, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/yu_cap/{key}.svg"); write_glif(path, "Yu-cy", adv, 0x42E, f"data/yu_cap/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "Ю", ["HЮHOЮ", "ЮHЮOЮ", "ЮЮЮЮ"], "docs/img/yu_cap_Yu1-Yu3.png", col_w=840, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/yu_cap/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["ymax"], v["contours"], v["min_gap_serif_oval"]) for k, v in meta.items()})
