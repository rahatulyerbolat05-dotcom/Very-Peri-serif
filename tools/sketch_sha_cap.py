#!/usr/bin/env python3
"""Эскизы заглавной Ш (U+0428, sha-cy) из H оригинала: три стойки с засечками и общая нижняя горизонталь 30 (зеркало П по высоте).
  Sh1: шаг стоек 250, Sh2: 270, Sh3: 290 (у H между стойками 297).
Запуск: python3 -I tools/sketch_sha_cap.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import sha_cap_sign
ref = Ref(); os.makedirs("build/sha_cap", exist_ok=True); os.makedirs("data/sha_cap", exist_ok=True)
items, meta = [], {}
for key, p in (("Sh1", 250.0), ("Sh2", 270.0), ("Sh3", 290.0)):
    path, info = sha_cap_sign(ref, p); adv = info["adv"]
    label = f"{key}  шаг {p:g}"
    ttf = f"build/sha_cap/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x428, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/sha_cap/{key}.svg"); write_glif(path, "Sha-cy", adv, 0x428, f"data/sha_cap/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "Ш", ["HШHOШ", "ШHШPШ", "ШШШШ"], "docs/img/sha_cap_Sh1-Sh3.png", col_w=840, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/sha_cap/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["contours"], v["top_pieces"]) for k, v in meta.items()})
