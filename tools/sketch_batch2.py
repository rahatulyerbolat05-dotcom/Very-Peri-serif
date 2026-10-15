#!/usr/bin/env python3
"""Вторая партия: ф, и, к (+ ka-cy.short), А, Ж (15.10.2026, по просьбе автора проекта; из старой разработки взяты только логика и идея, контуры собраны заново
из деталей оригинала: ı, k, l, p, o, K).
  и = латинская u оригинала без изменений (как п = n), А = латинская A (омоглиф), к = ı + ветви k, ka.short = укороченная правая часть засечки на кончике верхней ветви,
  ф = овал о + сквозная стойка (l сверху, p снизу), Ж = правая половина K + зеркало.
Запуск: python3 -I tools/sketch_batch2.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import ka_sign, ef_sign, ef2_sign, zhe_sign
ref = Ref()
for d in ("ka", "ef", "ef2", "ii", "A", "zhe"): os.makedirs(f"data/{d}", exist_ok=True)
os.makedirs("build/batch2", exist_ok=True)
items = {
    "ii": (ref.glyph("u"), ref.adv("u"), 0x438, "ii-cy", "и = латинская u"),
    "ka": (ka_sign(ref), 454, 0x43A, "ka-cy", "к"),
    "ka_short": (ka_sign(ref, short=True), 454, 0xE003, "ka-cy.short", "к.short"),
    "ef": (ef_sign(ref), 410, 0x444, "ef-cy", "ф"),
    "ef2": (ef2_sign(ref), 0, 0x444, "ef-cy", "ф из двух эллипсов"),
    "A": (ref.glyph("A"), ref.adv("A"), 0x410, "A-cy", "А = латинская A"),
    "zhe": (zhe_sign(ref), 0, 0x416, "Zhe-cy", "Ж"),
}
out = {}
for key, (path, adv, cp, gname, label) in items.items():
    path.simplify()
    if key == "zhe": adv = round(path.bounds[2] + 19)                       # симметричные поля 19/19
    if key == "ka": adv = round(path.bounds[2] + 11)
    if key == "ka_short": adv = out["ka"]["adv"]
    if key in ("ef", "ef2"): adv = round(path.bounds[2] + 23)
    ttf = f"build/batch2/IS-{key}.ttf"
    m = install(ref.ttf, path, adv, cp, ttf); m.update(label=label, contours=len(list(path.contours)))
    sub = {"ka_short": "ka", "ka": "ka", "ef2": "ef"}.get(key, key)
    write_svg(path, adv, f"data/{sub}/{key}.svg"); write_glif(path, gname, adv, cp, f"data/{sub}/{key}.glif")
    out[key] = m
def show(key, ch, cp):
    """ttf, где вариант стоит на основной кодовой точке (для показа в строке)."""
    ttf = f"build/batch2/IS-{key}-show.ttf"; install(ref.ttf, items[key][0], out[key]["adv"], cp, ttf); return ttf
render([(out["ka"]["label"], show("ka", "к", 0x43A), out["ka"]["adv"]), ("ka-cy.short (перед буквой с засечкой слева вверху)", show("ka_short", "к", 0x43A), out["ka"]["adv"])], "к", ["кнкпк", "нкнкп", "кккккк"], "docs/img/batch2_ka.png", col_w=700, size=700, base=620, guides=(0, 510))
render([(out["ef2"]["label"], "build/batch2/IS-ef2.ttf", out["ef2"]["adv"])], "ф", ["nфnфo", "HфHnф", "фnфf"], "docs/img/batch2_ef2.png", col_w=760, size=700, base=620, guides=(0, 510))
render([(out["ii"]["label"], "build/batch2/IS-ii.ttf", out["ii"]["adv"])], "и", ["nиnиo", "HиHnи", "иnиu"], "docs/img/batch2_ii.png", col_w=760, size=700, base=620, guides=(0, 510))
render([(out["zhe"]["label"], "build/batch2/IS-zhe.ttf", out["zhe"]["adv"])], "Ж", ["HЖHKЖ", "AЖAЖ", "ЖHЖ"], "docs/img/batch2_zhe.png", col_w=900, size=700, base=760, guides=(0, 720))
render([(out["A"]["label"], "build/batch2/IS-A.ttf", out["A"]["adv"])], "А", ["HАHKА", "AАAА", "АHА"], "docs/img/batch2_A.png", col_w=760, size=700, base=760, guides=(0, 720))
json.dump(out, open("data/batch2_meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["xmin"], v["xmax"], v["ymin"], v["ymax"], v["contours"]) for k, v in out.items()})
