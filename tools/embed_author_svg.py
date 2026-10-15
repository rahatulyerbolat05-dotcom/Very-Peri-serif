#!/usr/bin/env python3
"""Вставка собственного вектора автора проекта (SVG, его чертёж) в глиф без изменения формы: только масштаб и сдвиг.
Соответствие по умолчанию: верх SVG = 740 (выносной элемент), низ = −205, масштаб 945 / высота viewBox; левое поле задаётся (23).
Запуск: python3 -I tools/embed_author_svg.py файл.svg имя_глифа кодовая_точка(hex) каталог_данных ключ [левое_поле] [верх=740] [высота_единиц=945]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from fontTools.svgLib.path import parse_path
from fontTools.pens.transformPen import TransformPen
svg, gname, cp, ddir, key = sys.argv[1], sys.argv[2], int(sys.argv[3], 16), sys.argv[4], sys.argv[5]
left = float(sys.argv[6]) if len(sys.argv) > 6 else 23.0
top = float(sys.argv[7]) if len(sys.argv) > 7 else 740.0
units = float(sys.argv[8]) if len(sys.argv) > 8 else 945.0
src = open(svg, encoding="utf-8").read()
vh = float(re.search(r'viewBox="[\d.]+ [\d.]+ [\d.]+ ([\d.]+)"', src).group(1)); k = units / vh
d = " ".join(re.findall(r' d="([^"]+)"', src))
p = Path(); parse_path(d, TransformPen(p.getPen(), (k, 0, 0, -k, 0, top))); p.simplify()
p = shift(p, left - p.bounds[0]); adv = round(p.bounds[2] + left)
os.makedirs(ddir, exist_ok=True); os.makedirs("build/batch2", exist_ok=True)
write_svg(p, adv, f"{ddir}/{key}.svg"); write_glif(p, gname, adv, cp, f"{ddir}/{key}.glif")
ttf = f"build/batch2/IS-{key}-author.ttf"; m = install(Ref().ttf, p, adv, cp, ttf)
print({"adv": adv, "bounds": [round(v, 1) for v in p.bounds], "contours": len(list(p.contours)), "scale": round(k, 4)})
