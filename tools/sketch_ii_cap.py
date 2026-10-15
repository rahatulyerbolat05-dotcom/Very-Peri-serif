#!/usr/bin/env python3
"""Эскизы заглавной И (U+0418, ii-cy) из N оригинала (зеркало, правило 16.2 инструкции).
  I1: чистое зеркало N (остриё внизу слева ниже линии, −9).
  I2: остриё срезано по базовой линии, под левой стойкой опорная засечка F2 (копия правой).
Запуск: python3 -I tools/sketch_ii_cap.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import ii_cap_sign
ref = Ref(); os.makedirs("build/ii_cap", exist_ok=True); os.makedirs("data/ii_cap", exist_ok=True)
adv = ref.adv("N"); items, meta = [], {}
for key, foot, label in (("I1", False, "И1  чистое зеркало N"), ("I2", True, "И2  остриё срезано, засечка слева внизу")):
    path = ii_cap_sign(ref, foot); path.simplify()
    ttf = f"build/ii_cap/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x418, ttf); m.update(label=label, contours=len(list(path.contours)), xmin=round(path.bounds[0], 1), xmax=round(path.bounds[2], 1), ymin=round(path.bounds[1], 1), ymax=round(path.bounds[3], 1))
    write_svg(path, adv, f"data/ii_cap/{key}.svg"); write_glif(path, "Ii-cy", adv, 0x418, f"data/ii_cap/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "И", ["HИHNИ", "ИHИOИ", "ИИИИ"], "docs/img/ii_cap_I1-I2.png", col_w=900, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/ii_cap/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["ymax"], v["contours"]) for k, v in meta.items()})
