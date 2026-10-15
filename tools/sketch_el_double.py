#!/usr/bin/env python3
"""Двойная л (лигатура лл, кандидат в dlig): две л основы л1 (docs/glyphs/el_lower.md) в одном глифе. В оригинале лигатур l·l нет
(dlig только f_b, f_h, q_j), это новая деталь по просьбе автора проекта.
  d1: встык: засечки соседних ног касаются (шаг как у слитой пары).
  d2: общая ножка: толстая стойка первой л служит левой ногой второй (вертикальная, 0°), арки одного размера.
  d3: плотнее d1: засечки сливаются в одну (сдвиг на 40 внутрь).
Запуск: python3 -I tools/sketch_el_double.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import el_sign
ref = Ref(); os.makedirs("build/el", exist_ok=True); os.makedirs("data/el_double", exist_ok=True)
KW = dict(a=100.0, b=92.0, top=516.0, donor="dotlessi", LB=79, RB=147)
BASE = dict(t_l=28.0, t_r=68.0, t_top=25.0, **KW)

def l(beta, alpha, **over):
    kw = dict(BASE); kw.update(over); p, i = el_sign(ref, beta, alpha, **kw); return p, i

def pair(cut):
    p1, i1 = l(14.0, 3.0); p2, _ = l(14.0, 3.0)
    dx = (p1.bounds[2] - cut) - p2.bounds[0]
    return OR(p1, shift(p2, dx)), 0

def shared():
    p1, i1 = l(14.0, 0.0); p2, i2 = l(0.0, 3.0, t_l=68.0, a=128.0)             # правая стойка первой и левая нога второй совпадают
    # правая стойка первой: внешний край справа у основания = xmax первой минус боковая часть засечки (ı: 212 − 147 = 65)
    right1 = p1.bounds[2] - 65.0; left2 = p2.bounds[0] + 64.0           # внешний левый край второй ноги у основания (засечка ı слева: 79 − 15 = 64)
    return OR(p1, shift(p2, right1 - 68.0 - left2)), 0

VAR = {"d1": lambda: pair(2.0), "d2": shared, "d3": lambda: pair(40.0)}
items, meta = [], {}
CP = 0xE001
for key, fn in VAR.items():
    path, _ = fn(); path.simplify(); dx = 15 - path.bounds[0]; path = shift(path, dx); adv = round(path.bounds[2] + 15)
    label = {"d1": "d1  встык", "d2": "d2  общая ножка", "d3": "d3  засечки слиты"}[key]
    ttf = f"build/el/IS-ell2-{key}.ttf"
    m = install(ref.ttf, path, adv, CP, ttf); m.update(label=label, contours=len(list(path.contours)))
    write_svg(path, adv, f"data/el_double/{key}.svg"); write_glif(path, "el_el-cy", adv, CP, f"data/el_double/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
G = chr(CP)
render(items, G, ["n" + G + "n", "H" + G + "Ho", "u" + G + "v" + G + G], "docs/img/el_double_d1-d3.png", col_w=760, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/el_double/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["contours"]) for k, v in meta.items()})
