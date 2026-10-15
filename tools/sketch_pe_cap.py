#!/usr/bin/env python3
"""Эскизы заглавной П (U+041F, pe-cy) из H оригинала: стойки и засечки H, верхняя горизонталь вместо перекладины.
  P1: горизонталь 30 (как перекладина H), P2: 27 (как верх Л и L), P3: 34 (плотнее, ближе к весу стоек у серифов).
Запуск: python3 -I tools/sketch_pe_cap.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import pe_cap_sign
ref = Ref(); os.makedirs("build/pe_cap", exist_ok=True); os.makedirs("data/pe_cap", exist_ok=True)
adv = ref.adv("H"); items, meta = [], {}
for key, t in (("P1", 30.0), ("P2", 27.0), ("P3", 34.0)):
    path, info = pe_cap_sign(ref, t)
    label = f"{key}  горизонталь {t:g}"
    ttf = f"build/pe_cap/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x41F, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/pe_cap/{key}.svg"); write_glif(path, "Pe-cy", adv, 0x41F, f"data/pe_cap/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "П", ["HПHOП", "ПHПPП", "ПППП"], "docs/img/pe_cap_P1-P3.png", col_w=700, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/pe_cap/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymax"], v["contours"]) for k, v in meta.items()})
