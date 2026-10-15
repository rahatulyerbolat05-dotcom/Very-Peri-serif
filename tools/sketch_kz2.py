#!/usr/bin/env python3
"""Эскизы казахских Ө (U+04E8), ө (U+04E9) и Ғ (U+0492) из деталей оригинала.
Ө: О + горизонтальная черта 27 (O1) и 30 (O2). ө: о + черта 25 (o1) и 30 (o2). Ғ: Г (G1) + черта 30 половиной длины 75, 90, 105 (Gh1–Gh3).
Запуск: python3 -I tools/sketch_kz2.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import obar_sign, ghe_stroke_sign
ref = Ref(); os.makedirs("build/kz2", exist_ok=True); os.makedirs("data/kz2", exist_ok=True)
meta = {}
def emit(group, rows, cp, gname, char, samples, png, size):
    items = []
    for key, label, (path, info) in rows:
        adv = info["adv"]; ttf = f"build/kz2/IS-{key}.ttf"
        m = install(ref.ttf, path, adv, cp, ttf); m.update(label=label, **info)
        write_svg(path, adv, f"data/kz2/{key}.svg"); write_glif(path, gname, adv, cp, f"data/kz2/{key}.glif")
        items.append((label, ttf, adv)); meta[key] = m
    render(items, char, samples, png, col_w=620, size=size, base=760 if group == "cap" else 620, guides=(0, 720 if group == "cap" else 510))
rows = [("O1", "Ө  черта 27", obar_sign(ref, True, 27.0)), ("O2", "Ө  черта 30", obar_sign(ref, True, 30.0))]
emit("cap", rows, 0x4E8, "Obarred-cy", "Ө", ["HӨHOӨ", "ӨHӨPӨ", "ӨӨӨӨ"], "docs/img/kz_O_bar.png", 700)
rows = [("o1", "ө  черта 25", obar_sign(ref, False, 25.0)), ("o2", "ө  черта 30", obar_sign(ref, False, 30.0))]
emit("low", rows, 0x4E9, "obarred-cy", "ө", ["nөnoө", "өnөeө", "өөөө"], "docs/img/kz_o_bar.png", 700)
rows = [(f"Gh{i}", f"Ғ  черта ±{h}", ghe_stroke_sign(ref, h)) for i, h in ((1, 75.0), (2, 90.0), (3, 105.0))]
emit("cap", rows, 0x492, "Ghestroke-cy", "Ғ", ["HҒHOҒ", "ҒHҒPҒ", "ҒҒҒҒ"], "docs/img/kz_Ghe.png", 700)
json.dump(meta, open("data/kz2/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["ymax"], v["contours"]) for k, v in meta.items()})
