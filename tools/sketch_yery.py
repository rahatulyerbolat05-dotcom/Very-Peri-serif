#!/usr/bin/env python3
"""Эскизы строчной ы (U+044B, yeru-cy): ь плюс правая стойка (инструкция, раздел 7).
ь: латинская b со срезанным верхним выносным и головкой на x-height. Правая стойка: ı или стойка u.
Оси вариантов: головки (флажок ı или плоская засечка как у u), расстояние между чашей и стойкой
(185: как контрформа n по инструкции; 119: естественный зазор bi), чаша от b или от p.
Запуск: python3 -I tools/sketch_yery.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *

ref = Ref(); os.makedirs("build/yery", exist_ok=True); os.makedirs("data/yery", exist_ok=True)
B, P, I, U = ref.glyph("b"), ref.glyph("p"), ref.glyph("dotlessi"), ref.glyph("u")
GAP_DOC, GAP_TIGHT = 182, 119          # 182: контрформа n (142–324); 119: rsb b (40) + отступ стойки ı (79)
BODY_I = AND(I, rect(-50, 60, 400, 700))
FLAG = lambda dx: shift(AND(BODY_I, rect(-50, 400, 400, 700)), dx)          # головка ı (стойка 79–147)
UHEAD = lambda dx: shift(AND(U, rect(-50, 400, 150, 700)), dx)               # головка u (стойка 70–138)
I_LOW = lambda dx: shift(AND(I, rect(-50, -50, 400, 400)), dx)               # низ ı с опорными засечками

def bowl_b():            # ь от b: стойка 62–130 срезана на 510, чаша до x=402
    # стойку b выше 400 убираем целиком (до x=128, чашу и её верхний стык правее не трогаем): верх стойки берётся у ı или u,
    # иначе плоский срез b перекрывает пик флажка и ь читается как «D»
    return SUB(B, rect(0, 400, 128, 800)), 62, 402
def bowl_p():            # ь от p: стойка 73–141, спуск срезан, чаша до x=414, головка своя
    # спуск p с опорной засечкой (до x=223) режем целиком ниже -12; ствол -12…0 срезаем, дно чаши (до -9) не трогаем
    return SUB(SUB(P, rect(-50, -300, 800, -12)), rect(0, -12, 150, 0)), 73, 414

def build(kind, heads, gap):
    body, stem_x, bowl_r = bowl_b() if kind == "b" else bowl_p()
    right_x = bowl_r + gap
    if kind == "b":
        head = FLAG(stem_x - 79) if heads == "flag" else UHEAD(stem_x - 70)
        left = OR(body, head)
        # остаток выносного b (2 единицы стойки) срезаем ровно по верху головки: без «зазубрины»;
        # верх чаши (516) начинается правее x=196, срез до x=170 его не задевает
        left = SUB(left, rect(-50, head.bounds[3], 170, 900))
    else:
        left = OR(body, FOOT_L(stem_x)) if heads == "flag" else OR(SUB(body, rect(0, 440, 150, 800)), UHEAD(stem_x - 70), FOOT_L(stem_x))
    if heads == "flag": right = shift(I, right_x - 79)
    else: right = OR(I_LOW(right_x - 79), UHEAD(right_x - 70))
    return OR(left, right)
def FOOT_L(stem_x): return shift(AND(I, rect(-50, -50, 113, 60)), stem_x - 79)   # левая половина опорной засечки ı

VAR = {"Y1": ("b", "flag", GAP_DOC, "Y1   флажки, зазор 182"),
       "Y2": ("b", "flag", GAP_TIGHT, "Y2   флажки, зазор 119"),
       "Y3": ("b", "u", GAP_TIGHT, "Y3   головки u, зазор 119"),
       "Y4": ("p", "flag", GAP_TIGHT, "Y4   чаша от p, зазор 119")}
items, meta = [], {}
for key, (kind, heads, gap, label) in VAR.items():
    path = build(kind, heads, gap); path.simplify()
    ttf = f"build/yery/IS-yery-{key}.ttf"
    m = install(ref.ttf, path, 0, 0x44B, ttf)             # первая установка: узнать xmax
    adv = m["xmax"] + 11
    m = install(ref.ttf, build(kind, heads, gap), adv, 0x44B, ttf); m.update(label=label, kind=kind, heads=heads, gap=gap)
    p2 = build(kind, heads, gap); p2.simplify()
    write_svg(p2, adv, f"data/yery/{key}.svg"); write_glif(p2, "yeru-cy", adv, 0x44B, f"data/yery/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "ы", ["nыmыu", "ыыы", "ы n ы i"], "docs/img/yery_Y1-Y4.png", col_w=800, size=860, base=620)
json.dump(meta, open("data/yery/meta.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(meta, ensure_ascii=False))
