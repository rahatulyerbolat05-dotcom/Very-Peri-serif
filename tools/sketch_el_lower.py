#!/usr/bin/env python3
"""Эскизы строчной л (U+043B, el-cy): арка и две ноги, засечки от ı, верх 516 (овершут круглого верха строчных).
Тот же построитель, что у заглавной Л (glyphparts.el_sign, donor ı). Три варианта: угол и вес вместе.
  l1: по шрифту: нога 28, стойка 68, верх 25 (тонкие диагонали строчных 24–31, стебель n 68, волосная верха n 25), углы 14°/3°.
  l2: нога 34, стойка 72, верх 29, углы 12°/4°.
  l3: нога 40, стойка 76, верх 33, углы 10°/5° (плотнее по ощущению автора проекта: на заглавной Л тонкая линия показалась слабой).
Запуск: python3 -I tools/sketch_el_lower.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import el_sign
ref = Ref(); os.makedirs("build/el", exist_ok=True); os.makedirs("data/el_lower", exist_ok=True)
A_, B_ = 100.0, 92.0
VAR = {"l1": (14.0, 3.0, 28.0, 68.0, 25.0), "l2": (12.0, 4.0, 34.0, 72.0, 29.0), "l3": (10.0, 5.0, 40.0, 76.0, 33.0)}
items, meta = [], {}
for key, (beta, alpha, tl, tr, tt) in VAR.items():
    path, info = el_sign(ref, beta, alpha, a=A_, b=B_, top=516.0, t_l=tl, t_r=tr, t_top=tt, donor="dotlessi", LB=79, RB=147); path.simplify()
    adv = info["xmax"] + 15                                       # правое поле 15, как у i и n слева
    label = f"{key}  {beta:g}°/{alpha:g}°  {tl:g}/{tr:g}/{tt:g}"
    ttf = f"build/el/IS-ell-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x43B, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/el_lower/{key}.svg"); write_glif(path, "el-cy", adv, 0x43B, f"data/el_lower/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "л", ["nлnuлv", "лHлnлo", "лnлi лл"], "docs/img/el_lower_l1-l3.png", col_w=700, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/el_lower/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["alpha_deg"], v["gap_at_baseline"], v["contours"], v["ymax"]) for k, v in meta.items()})
