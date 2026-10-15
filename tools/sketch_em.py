#!/usr/bin/env python3
"""Эскизы строчной м (U+043C, em-cy) по роли штрихов латинской M (инструкция 16.2): стойки и V.
  m1: вершина V на 26 (как у M: 37 из 720), головки u на обеих стойках.
  m2: вершина на базовой линии (0), головки u.
  m3: вершина на 26, левая стойка с косым флажком ı (F1), правая с головкой u.
Запуск: python3 -I tools/sketch_em.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import em_sign
ref = Ref(); os.makedirs("build/em", exist_ok=True); os.makedirs("data/em", exist_ok=True)
VAR = {"m1": dict(apex=26.0, head_l="u"), "m2": dict(apex=0.0, head_l="u"), "m3": dict(apex=26.0, head_l="flag")}
items, meta = [], {}
for key, kw in VAR.items():
    path, info = em_sign(ref, **kw); path.simplify()
    adv = info["xmax"] + 15
    label = f"{key}  вершина {kw['apex']:g}, головка {kw['head_l']}"
    ttf = f"build/em/IS-em-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x43C, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/em/{key}.svg"); write_glif(path, "em-cy", adv, 0x43C, f"data/em/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "м", ["nмnuмv", "мHмnмo", "мnмi мм"], "docs/img/em_m1-m3.png", col_w=700, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/em/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["contours"], v["ymin"], v["ymax"]) for k, v in meta.items()})
