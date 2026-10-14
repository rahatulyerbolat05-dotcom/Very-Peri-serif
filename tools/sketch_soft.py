#!/usr/bin/env python3
"""Эскизы строчной ь (U+044C, softsign-cy): стойка с головкой и чаша справа (инструкция, раздел 7).
Чаша: S1, S2 от латинской a (нижняя чаша, отражена по горизонтали: ниже и уже, чем у b; хвост a становится шпорой слева);
S3, S4 то же без крючка. Чаши от b и от p на всю высоту x-height отброшены: ь читается как «D». Головка стойки: флажок ı или плоская засечка как у u.
Запуск: python3 -I tools/sketch_soft.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *

ref = Ref(); os.makedirs("build/soft", exist_ok=True); os.makedirs("data/soft", exist_ok=True)
A, B, P, I, U = (ref.glyph(n) for n in ("a", "b", "p", "dotlessi", "u"))
STEM_X = 62                                                    # левый край стойки (как у b), ширина 68
BODY_I = AND(I, rect(-50, 60, 400, 700))
FLAG = lambda dx: shift(AND(BODY_I, rect(-50, 400, 400, 700)), dx)        # головка ı: стойка 79–147
UHEAD = lambda dx: shift(AND(U, rect(-50, 400, 150, 700)), dx)             # головка u: стойка 70–138
RSB = 30                                                       # поле справа: между o (25) и b (40), подобрать при кернинге

def head(kind): return FLAG(STEM_X - 79) if kind == "flag" else UHEAD(STEM_X - 70)
def bowl_a():     # нижняя чаша a (стойка 245–313, чаша до x=24) зеркально: x' = 375 − x → стойка 62–130
    part = AND(A, rect(-50, -50, 700, 325))
    return tf(part, (-1, 0, 0, 1, 375, 0)), 130 + 221
def foot_l(): return shift(AND(I, rect(-50, -50, 113, 60)), STEM_X - 79)    # левая половина опорной засечки ı

def build(src, kind):
    body, right = bowl_a(); h = head(kind)
    if src == "a_notail":                       # хвост a (теперь слева внизу) снят, вместо него опорная засечка ı
        body = OR(SUB(body, rect(-50, -50, STEM_X - 1, 200)), foot_l())
    return OR(body, rect(STEM_X, 300, STEM_X + 68, 410), h), right

VAR = {"S1": ("a", "flag", "S1   чаша от a, флажок"),
       "S2": ("a", "u", "S2   чаша от a, головка u"),
       "S3": ("a_notail", "flag", "S3   без крючка, флажок"),
       "S4": ("a_notail", "u", "S4   без крючка, головка u")}
items, meta = [], {}
for key, (src, kind, label) in VAR.items():
    path, right = build(src, kind); path.simplify()
    adv = right + RSB; ttf = f"build/soft/IS-soft-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x44C, ttf); m.update(label=label, bowl=src, heads=kind, bowl_right=right)
    write_svg(path, adv, f"data/soft/{key}.svg"); write_glif(path, "softsign-cy", adv, 0x44C, f"data/soft/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ь", ["nьmьu", "ььь", "ь n ь i"], "docs/img/soft_S1-S4.png", col_w=620, size=1000, base=680)
json.dump(meta, open("data/soft/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["ymin"], v["ymax"]) for k, v in meta.items()})
