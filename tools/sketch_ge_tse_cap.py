#!/usr/bin/env python3
"""Эскизы заглавных Г (U+0413, ge-cy) и Ц (U+0426, tse-cy) из H и E оригинала.
Г: один вариант G1 с горизонталью E без изменений (укороченные варианты отклонены: излом или ступеньки на шве). Ц: T1 хвост 100, T2 140 (старт, D5), T3 205.
Запуск: python3 -I tools/sketch_ge_tse_cap.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import ge_cap_sign, tse_cap_sign
ref = Ref(); os.makedirs("build/ge_cap", exist_ok=True); os.makedirs("data/ge_cap", exist_ok=True); os.makedirs("build/tse_cap", exist_ok=True); os.makedirs("data/tse_cap", exist_ok=True)
items, meta = [], {}
for key, d in (("G1", 0.0),):
    path, info = ge_cap_sign(ref, d); adv = info["adv"]
    label = f"{key}  короче на {d:g}"
    ttf = f"build/ge_cap/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x413, ttf); m.update(label=label, **info)
    write_svg(path, adv, f"data/ge_cap/{key}.svg"); write_glif(path, "Ge-cy", adv, 0x413, f"data/ge_cap/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "Г", ["HГHOГ", "ГEГLГ", "ГГГГ"], "docs/img/ge_cap_G1.png", col_w=620, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/ge_cap/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["contours"]) for k, v in meta.items()})
items, meta = [], {}
for key, t in (("T1", 100.0), ("T2", 140.0), ("T3", 205.0)):
    path, info = tse_cap_sign(ref, t); adv = info["adv"]
    label = f"{key}  хвост {t:g}"
    ttf = f"build/tse_cap/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x426, ttf); m.update(label=label, **info)
    write_svg(path, adv, f"data/tse_cap/{key}.svg"); write_glif(path, "Tse-cy", adv, 0x426, f"data/tse_cap/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "Ц", ["HЦHOЦ", "ЦHЦPЦ", "ЦЦЦЦ"], "docs/img/tse_cap_T1-T3.png", col_w=700, size=700, base=760, guides=(0, 720))
json.dump(meta, open("data/tse_cap/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["contours"]) for k, v in meta.items()})
