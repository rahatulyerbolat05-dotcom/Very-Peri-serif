#!/usr/bin/env python3
"""Эскизы строчной ш: две кандидатуры, обе сохранены (docs/glyphs/sha.md).
R1: латинская m, повёрнутая на 180°, верхушки как головки у u (плоская засечка слева).
R2: то же, но верхушки с наклонными флажками (головка ı).
Запуск: python3 -I tools/sketch_sha.py   (нужны reference/ после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *

ref = Ref(); os.makedirs("build/sha", exist_ok=True)
M = ref.glyph("m"); ADV = ref.adv("m")                      # 704
turned = tf(M, (-1, 0, 0, -1, ADV, 510))                    # поворот на 180° вокруг центра x-height (510)
stems = [78, 320, 562]                                      # левые края стоек после поворота: 704 − (626, 384, 142)
base = AND(turned, rect(-50, -50, 800, 410))                # низ и стойки до y=410, прежние засечки сняты
I = ref.glyph("dotlessi"); BODY = AND(I, rect(-50, 60, 400, 700))
flags = [shift(AND(BODY, rect(-50, 400, 400, 700)), x - 79) for x in stems]       # стойка ı: левый край 79
U = ref.glyph("u"); heads_u = [shift(AND(U, rect(-50, 400, 150, 700)), x - 70) for x in stems]  # стойка u: левый край 70
VAR = {"R1": (OR(base, *heads_u), "R1   головки как у u"), "R2": (OR(base, *flags), "R2   флажки")}
items, meta = [], {}
for key, (path, label) in VAR.items():
    ttf = f"build/sha/IS-sha-{key}.ttf"
    meta[key] = install(ref.ttf, path, ADV, 0x448, ttf); meta[key]["label"] = label
    write_svg(path, ADV, f"data/sha/{key}.svg"); write_glif(path, "sha-cy", ADV, 0x448, f"data/sha/{key}.glif")
    items.append((label, ttf, ADV))
render(items, "ш", ["nшmшu", "шшш", "ш n ш i"], "docs/img/sha_R1_R2.png")
json.dump(meta, open("data/sha/meta.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(meta, ensure_ascii=False))
