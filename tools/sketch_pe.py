#!/usr/bin/env python3
"""п (U+043F, pe-cy) по решению автора проекта 15.10.2026: латинская n оригинала без изменений (арочная форма в прямом, исключение из инструкции раздел 7).
Контекстная форма pe-cy.flag: нижний правый угол правой стойки, флажок-хвост от u, перед буквами с опорной засечкой в нижнем левом углу.
Запуск: python3 -I tools/sketch_pe.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import pe_flag
ref = Ref(); os.makedirs("build/pe", exist_ok=True); os.makedirs("data/pe", exist_ok=True)
adv = ref.adv("n"); base = ref.glyph("n"); flag = pe_flag(ref); flag.simplify()
items, meta = [], {}
for key, path, name, label in (("pe", base, "pe-cy", "pe  латинская n"), ("pe_flag", flag, "pe-cy.flag", "pe.flag  хвост-флажок")):
    ttf = f"build/pe/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x43F, ttf); m.update(label=label, contours=len(list(path.contours)))
    write_svg(path, adv, f"data/pe/{key}.svg"); write_glif(path, name, adv, 0x43F if key == "pe" else None, f"data/pe/{key}.glif") if key == "pe" else write_glif(path, name, adv, 0xE002, f"data/pe/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "п", ["пnпiпhпH", "nпnпnп", "пnпn пп"], "docs/img/pe_pe_flag.png", col_w=760, size=700, base=620, guides=(0, 510))
json.dump(meta, open("data/pe/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["contours"]) for k, v in meta.items()})
