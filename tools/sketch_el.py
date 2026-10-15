#!/usr/bin/env python3
"""Эскизы заглавной Л (U+041B, el-cy) по наброску автора проекта (docs/img/author_sketch_el.png): арка и две ноги.
Левая нога тонкая и наклонена влево, правая толстая со слабым расхождением вниз; засечки внизу от H.
Построено параметрически (tools/glyphparts.py, el_sign), набросок не обводился.
  L1: по шрифту: левая нога 14° (тонкие диагонали A и V измерены 14°), правая 3°.
  L2: как на наброске автора (замер: левая нога 10°, правая 5°).
  L3: середина: 12° и 4°.
Арка по замеру наброска (a=128, b=110), толщины по шрифту (нога 30, стойка 71, верх 27); на наброске ноги толще (44 и 100).
Запуск: python3 -I tools/sketch_el.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from glyphparts import el_sign
from PIL import Image

ref = Ref(); os.makedirs("build/el", exist_ok=True); os.makedirs("data/el", exist_ok=True)
A_, B_ = 128.0, 110.0         # полуоси внешнего эллипса арки: замер наброска автора (купол шириной около 256, высотой около 110; b/a = 0,86)
VAR = {"L1": (14.0, 3.0), "L2": (10.0, 5.0), "L3": (12.0, 4.0)}
items, meta = [], {}
for key, (beta, alpha) in VAR.items():
    path, info = el_sign(ref, beta, alpha, a=A_, b=B_); path.simplify()
    adv = info["xmax"] + 19                                       # правое поле 19, как у H
    label = f"{key}  нога {beta:g}°, стойка {alpha:g}°"
    ttf = f"build/el/IS-el-{key}.ttf"
    m = install(ref.ttf, path, adv, 0x41B, ttf); m.update(label=label, contours=len(list(path.contours)), **info)
    write_svg(path, adv, f"data/el/{key}.svg"); write_glif(path, "El-cy", adv, 0x41B, f"data/el/{key}.glif")
    items.append((label, ttf, adv)); meta[key] = m
render(items, "Л", ["HЛH", "ЛЛЛ", "Л H Л O"], "build/el/_mine.png", col_w=700, size=700, base=760, guides=(0, 720))
# рядом набросок автора, масштаб по высоте (верх 95 px, база 540 px на наброске = 730 единиц при 700 px/em)
sk = Image.open("docs/img/author_sketch_el.png").convert("RGB").crop((140, 85, 515, 550))
scale = (730 * 0.7) / 445.0
sk = sk.resize((int(sk.width * scale), int(sk.height * scale)), Image.LANCZOS)
mine = Image.open("build/el/_mine.png"); col = 460
canvas = Image.new("RGB", (mine.width + col, mine.height), "white"); canvas.paste(mine, (col, 0))
base_y = 760; canvas.paste(sk, (30, int(base_y - (540 - 85) * scale)))
from PIL import ImageDraw, ImageFont
d = ImageDraw.Draw(canvas); d.text((30, 40), "набросок автора", font=ImageFont.truetype(LABEL_BOLD, 38), fill="black")
canvas.save("docs/img/el_L1-L3.png")
json.dump(meta, open("data/el/meta.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["adv"], v["alpha_deg"], v["gap_at_baseline"], v["contours"]) for k, v in meta.items()})
