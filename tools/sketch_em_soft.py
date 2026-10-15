#!/usr/bin/env python3
"""Мягкая м: форма m1 (docs/glyphs/em.md) со смягчением: скругление внутренних углов (стыки диагоналей со стойками, засечек со стойками)
и внешних (вершина V, углы верха стоек). Три степени: ms1, ms2, ms3. Запуск: python3 -I tools/sketch_em_soft.py (нужен shapely)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import em_sign
ref = Ref(); os.makedirs("build/em", exist_ok=True); os.makedirs("data/em", exist_ok=True)
VAR = {"ms1": (4.0, 8.0, 8.0), "ms2": (5.0, 12.0, 8.0), "ms3": (8.0, 16.0, 12.0)}       # внешний радиус, внутренний радиус, плоская вершина V
items, meta = [], {}
for key, (rc, ri, flat) in VAR.items():
    base, info = em_sign(ref, apex=26.0, head_l="u", flat=flat)
    path = soften(base, rc, ri); adv = info["xmax"] + 15
    label = f"{key}  скругление {rc:g} / {ri:g}"
    ttf = f"build/em/IS-ems-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x43C, ttf); m.update(label=label, contours=len(list(path.contours)), r_convex=rc, r_concave=ri, flat=flat)
    write_svg(path, adv, f"data/em/{key}.svg"); write_glif(path, "em-cy", adv, 0x43C, f"data/em/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "м", ["nмnuмv", "мHмnмo", "мnмi мм"], "docs/img/em_soft_ms1-ms3.png", col_w=700, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/em/meta_soft.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["contours"], v["ymin"], v["ymax"]) for k, v in meta.items()})
