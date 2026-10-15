#!/usr/bin/env python3
"""Эскизы заглавной Л стандартной формы (плоская вершина): St1 головная засечка с обеих сторон, St2 левый выступ, St3 без засечек. Угол ноги 16°.
Запуск: python3 -I tools/sketch_el_std.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import el_std_sign
ref = Ref(); os.makedirs("build/el_std", exist_ok=True); os.makedirs("data/el_std", exist_ok=True)
items, meta = [], {}
for key, apex, lab in (("St1", "both", "засечка с обеих сторон"), ("St2", "left", "левый выступ"), ("St3", "none", "без засечек")):
    path, info = el_std_sign(ref, apex); adv = info["adv"]
    label = f"{key}  {lab}"
    ttf = f"build/el_std/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x41B, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/el_std/{key}.svg"); write_glif(path, "El-cy", adv, 0x41B, f"data/el_std/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "Л", ["HЛHOЛ", "ЛHЛPЛ", "ЛЛЛЛ"], "docs/img/el_std_St1-St3.png", col_w=700, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/el_std/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["feet_gap"], v["contours"], v["xmin"], v["xmax"]) for k, v in meta.items()})
