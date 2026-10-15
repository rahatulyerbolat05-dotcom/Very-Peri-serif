#!/usr/bin/env python3
"""Пробная сборка хвостов по принципу docs/tails.md на Ң (Н = H оригинала), ң (н n4) и щ (ш R1): K1 прямой, K2 крюк наружу, K3 огонек,
K4 цельный огонек (K4a брюшко огонька 46, K4b брюшко в ширину стойки).
Ничего не регистрирует как основу. Запуск: python3 -I tools/sketch_tails.py (после tools/fetch_reference.sh)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *
from tails import module, cut_stem, attach, ogonek_on, k4
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from pathops import Path
def load(f):
    class G: pass
    g = G(); g.width = 0; p = Path(); readGlyphFromString(open(f, encoding="utf-8").read(), g, PointToSegmentPen(p.getPen())); return p, g.width
ref = Ref(); os.makedirs("build/tails", exist_ok=True); os.makedirs("data/tails", exist_ok=True)
H = ref.glyph("H"); n4, wn = load("data/en/n4.glif"); sha, ws = load("data/sha/R1.glif")
# (имя, буква, код, база, ширина, левый край стойки, якорь огонька, прописная): якорь у Н как у I (правый край стойки), у н как у u (336 + 12), у ш в точке ножки (низ 569–584)
bases = [("Endesc", "Ң", 0x4A2, H, 546, 386.0, 457.0, True), ("endesc", "ң", 0x4A3, n4, wn, 324.0, 348.0, False), ("shcha", "щ", 0x449, sha, ws, 562.0, 584.0, False)]
meta = {}; cells = []
for key, ch, cp, base, adv, sl, sr, cap in bases:
    for kind in ("K1", "K2", "K3"):
        if kind == "K3":
            p = ogonek_on(ref, base, sr)
        else:
            p = attach(cut_stem(base, sl, sl + (71.0 if cap else 68.0)), module(ref, kind, cap), sl)
        name = f"{key}_{kind}"; ttf = f"build/tails/{name}.ttf"
        m = install(ref.ttf, p, adv, cp, ttf); m.update(contours=len(list(p.contours)), points=sum(len(list(c.segments)) for c in p.contours))
        write_svg(p, adv, f"data/tails/{name}.svg"); write_glif(p, name, adv, cp, f"data/tails/{name}.glif")
        meta[name] = m; cells.append((ch, kind, ttf, cp))
k4cells = []
for key, ch, cp, base, adv, sl, sr, cap in bases:
    for kind, belly in (("K4a", 46.0), ("K4b", 71.0 if cap else 68.0)):
        p = k4(ref, {"Endesc": "En", "endesc": "en", "shcha": "shcha"}[key], base, belly)
        name = f"{key}_{kind}"; ttf = f"build/tails/{name}.ttf"
        m = install(ref.ttf, p, adv, cp, ttf); m.update(contours=len(list(p.contours)), points=sum(len(list(c.segments)) for c in p.contours))
        write_svg(p, adv, f"data/tails/{name}.svg"); write_glif(p, name, adv, cp, f"data/tails/{name}.glif")
        meta[name] = m; k4cells.append((ch, kind, ttf, cp))
json.dump(meta, open("data/tails/meta.json", "w"), ensure_ascii=False, indent=1)
from PIL import Image, ImageDraw, ImageFont
S = 300; k = S / 1000; CW, CH = 420, 560
im = Image.new("RGB", (3 * CW + 40, 3 * CH + 80), "white"); d = ImageDraw.Draw(im)
lab = ImageFont.truetype(LABEL_BOLD, 22); sm = ImageFont.truetype(LABEL, 18)
names = {"K1": "K1 прямой (p / H, −205)", "K2": "K2 крюк наружу (j / J, −215)", "K3": "K3 огонек (как Į, −216)"}
for i, (ch, kind, ttf, cp) in enumerate(cells):
    r, c = divmod(i, 3); x0 = 20 + c * CW; y0 = 60 + r * CH; base = y0 + 330
    if r == 0: d.text((x0 + 8, 14), names[kind], font=lab, fill="black")
    for gy, col in ((0, "#e99"), (-205, "#bbb"), (-215, "#ddd"), (510, "#9bf"), (720, "#9bf")):
        d.line([(x0 + 6, base - gy * k), (x0 + CW - 6, base - gy * k)], fill=col)
    f = ImageFont.truetype(ttf, S); d.text((x0 + 40, base), chr(cp), font=f, fill="black", anchor="ls")
    f2 = ImageFont.truetype(ttf, 90)
    sample = {"Ң": "HҢHOҢ", "ң": "nңnoң", "щ": "nщnoщ"}[ch]
    d.text((x0 + 10, y0 + 420), sample, font=f2, fill="black")
im.save("docs/img/tails_K1-K3.png")
# лист K4: принятый K2 и альтернативы K3, K4a, K4b
names.update({"K4a": "K4a цельный, брюшко 46", "K4b": "K4b цельный, брюшко = стойка"})
cols = ("K2", "K3", "K4a", "K4b"); allc = {(ch, kd): (t, c) for ch, kd, t, c in cells + k4cells}
im = Image.new("RGB", (4 * CW + 40, 3 * CH + 80), "white"); d = ImageDraw.Draw(im)
for c, kind in enumerate(cols): d.text((20 + c * CW + 8, 14), names[kind], font=lab, fill="black")
for r, ch in enumerate(("Ң", "ң", "щ")):
    for c, kind in enumerate(cols):
        ttf, cp = allc[(ch, kind)]; x0 = 20 + c * CW; y0 = 60 + r * CH; base = y0 + 330
        for gy, col in ((0, "#e99"), (-205, "#bbb"), (-215, "#ddd"), (510, "#9bf"), (720, "#9bf")):
            d.line([(x0 + 6, base - gy * k), (x0 + CW - 6, base - gy * k)], fill=col)
        f = ImageFont.truetype(ttf, S); d.text((x0 + 40, base), chr(cp), font=f, fill="black", anchor="ls")
        f2 = ImageFont.truetype(ttf, 90); d.text((x0 + 10, y0 + 420), {"Ң": "HҢHOҢ", "ң": "nңnoң", "щ": "nщnoщ"}[ch], font=f2, fill="black")
im.save("docs/img/tails_K4.png"); print({k_: (v["xmin"], v["xmax"], v["ymin"], v["contours"], v["points"]) for k_, v in meta.items()})
