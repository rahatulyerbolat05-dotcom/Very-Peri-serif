#!/usr/bin/env python3
"""Строчная м в форме латинской строчной m (арочная) по просьбе автора проекта 15.10.2026: контур m оригинала без изменений под U+043C.
Исключение из D1 (курсивные и арочные силуэты в прямом запрещены): вариант, не основа. Контур не растягивался (запрет на масштаб соблюдён).
Рядом m1 и ms2 (docs/glyphs/em.md). Запуск: python3 -I tools/sketch_em_latin.py (после tools/sketch_em.py, tools/sketch_em_soft.py)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
ref = Ref(); os.makedirs("build/em", exist_ok=True); os.makedirs("data/em", exist_ok=True)
adv = ref.adv("m")
path = ref.glyph("m")
ttf = "build/em/IS-em-latin.ttf"; info = install(ref.ttf, path, adv, 0x43C, ttf)
write_svg(path, adv, "data/em/m_latin.svg"); write_glif(path, "em-cy", adv, 0x43C, "data/em/m_latin.glif")
json.dump({"adv": adv, **info, "note": "контур латинской m без изменений"}, open("data/em/meta_latin.json", "w"), ensure_ascii=False, indent=1)
items = [("m1 (основа)", "build/em/IS-em-m1.ttf", 542), ("ms2 (мягкая)", "build/em/IS-ems-ms2.ttf", 542), ("как латинская m", ttf, adv)]
render(items, "м", ["nмnuмv", "мHмnмo", "мnмi мм"], "docs/img/em_latin_m.png", col_w=760, size=700, base=620, guides=(0, 510))
print(adv, info)
