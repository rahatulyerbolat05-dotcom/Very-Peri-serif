#!/usr/bin/env python3
"""Эскизы строчной т (U+0442, te-cy) по инструкции (раздел 7): горизонталь с короткими засечками вниз по краям, центральная стойка с ножкой.
Конец горизонтали как у ъ (K2: засечка вниз 70, перекладина 27), стойка 68 и ножка от ı (F2). Три варианта вылета горизонтали:
  t1: 125 (основа, выбрана автором проекта 15.10.2026), t2: 150, t3: 175 (как у T: 175 с каждой стороны стойки),
  t1b: как t1, но каплевидные ушки (F5) вместо засечек вниз.
  t1c: как t1, ушки по наброску автора проекта (docs/img/author_sketch_te_ear.png): вертикальный внешний край, круглый низ, большое сопряжение с горизонталью.
Запуск: python3 -I tools/sketch_te.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import te_sign
ref = Ref(); os.makedirs("build/te", exist_ok=True); os.makedirs("data/te", exist_ok=True)
VAR = {"tn125": (125.0, "none"), "tn140": (140.0, "none"), "tn175": (175.0, "none"), "t1": (125.0, "serif"), "t1b": (125.0, "drop"), "t1c": (125.0, "user"), "t2": (150.0, "serif"), "t3": (175.0, "serif")}
items, meta = [], {}
for key, (ov, ear) in VAR.items():
    path, info = te_sign(ref, overhang=ov, ear=ear); path.simplify()
    adv = round(info["xmax"] + 20)
    label = f"{key}  " + {"drop": "капля", "user": "набросок", "serif": "засечка", "none": "без ушек"}[ear]
    ttf = f"build/te/IS-te-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x442, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/te/{key}.svg"); write_glif(path, "te-cy", adv, 0x442, f"data/te/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
ALL = dict((k, (l, f, a)) for (l, f, a), k in zip(items, VAR))
render([ALL[k] for k in ("t1", "t1b", "t1c", "t2", "t3")], "т", ["nтnuтo", "HтHnтu", "тTтiт"], "docs/img/te_t1-t3.png", col_w=560, size=700, base=620, guides=(0, 510))
render([ALL[k] for k in ("t1", "tn125", "tn140", "tn175")], "т", ["nтnuтo", "HтHnтu", "тTтiт"], "docs/img/te_plain.png", col_w=560, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/te/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["contours"], v["ymin"], v["ymax"]) for k, v in meta.items()})

