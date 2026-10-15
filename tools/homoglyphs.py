#!/usr/bin/env python3
"""Омоглифы: кириллические буквы, у которых в оригинале есть латинский двойник, берутся из оригинала без редактирования
(тот же шрифт OFL, правило проекта о двойниках, раздел 3.3 CLAUDE.md). Записывает GLIF (имена по номенклатуре Glyphs) в data/homoglyph/.
В UFO эти глифы должны быть компонентами латинских (правка латиницы тогда автоматически идёт в кириллицу), здесь контуры для эскизов и проверок.
Запуск: python3 -I tools/homoglyphs.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
ref = Ref(); os.makedirs("data/homoglyph", exist_ok=True)
# (кириллица, латинский глиф, имя Glyphs, кодовая точка)
PAIRS = [("В", "B", "Ve-cy", 0x412), ("Е", "E", "Ie-cy", 0x415), ("Ё", "Edieresis", "Io-cy", 0x401), ("К", "K", "Ka-cy", 0x41A), ("М", "M", "Em-cy", 0x41C), ("Н", "H", "En-cy", 0x41D),
         ("О", "O", "O-cy", 0x41E), ("Р", "P", "Er-cy", 0x420), ("С", "C", "Es-cy", 0x421), ("Т", "T", "Te-cy", 0x422), ("Х", "X", "Ha-cy", 0x425),
         ("а", "a", "a-cy", 0x430), ("е", "e", "ie-cy", 0x435), ("ё", "edieresis", "io-cy", 0x451), ("о", "o", "o-cy", 0x43E), ("р", "p", "er-cy", 0x440), ("с", "c", "es-cy", 0x441),
         ("у", "y", "u-cy", 0x443), ("х", "x", "ha-cy", 0x445)]
# синхронные ss01-формы (D10): у латиницы a, c, e есть .ss01
SS01 = [("а", "a.ss01", "a-cy.ss01", 0xE010), ("с", "c.ss01", "es-cy.ss01", 0xE011), ("е", "e.ss01", "ie-cy.ss01", 0xE012), ("ё", "edieresis.ss01", "io-cy.ss01", 0xE013)]
meta = {}
for cyr, lat, gname, cp in PAIRS:
    p = ref.glyph(lat); adv = ref.adv(lat)
    write_glif(p, gname, adv, cp, f"data/homoglyph/{gname}.glif"); write_svg(p, adv, f"data/homoglyph/{gname}.svg")
    meta[cyr] = {"latin": lat, "glyph": gname, "unicode": f"U+{cp:04X}", "adv": adv, "bounds": [round(v) for v in p.bounds]}
for cyr, lat, gname, cp in SS01:
    p = ref.glyph(lat); adv = ref.adv(lat)
    write_glif(p, gname, adv, cp, f"data/homoglyph/{gname}.glif"); write_svg(p, adv, f"data/homoglyph/{gname}.svg")
    meta[gname] = {"latin": lat, "glyph": gname, "adv": adv, "bounds": [round(v) for v in p.bounds]}
json.dump(meta, open("data/homoglyph/meta.json", "w"), ensure_ascii=False, indent=1)
print(len(PAIRS), "омоглифов,", len(SS01), "ss01-форм")
