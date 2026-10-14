#!/usr/bin/env python3
"""Снимает измерения с оригинала Instrument Serif и пишет data/params.json.

Запуск: python3 -I tools/extract_params.py [reference/instrument-serif] [data/params.json]
Нужны: fonttools, pillow, glyphsLib. Значения в единицах em/1000.
Растровые измерения идут при 2000 px/em (шаг 0.5 ед.), округление до 1 ед.
Числа из этого файла — единственный источник чисел для кода. Числа в текстах — слепок.
"""
import json, math, subprocess, sys, os
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image, ImageDraw, ImageFont
from glyphsLib import GSFont

REF = sys.argv[1] if len(sys.argv) > 1 else "reference/instrument-serif"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/params.json"
SIZE = 2000

def r(v, n=0):
    return round(v, n) if n else int(round(v))

class Raster:
    def __init__(self, path):
        self.font = ImageFont.truetype(path, SIZE)
        self.cache = {}
    def glyph(self, ch):
        if ch not in self.cache:
            im = Image.new("L", (SIZE * 2, SIZE * 2), 0)
            ImageDraw.Draw(im).text((SIZE // 2, SIZE), ch, font=self.font, fill=255, anchor="ls")
            self.cache[ch] = im.point(lambda v: 255 if v > 127 else 0).load(), im.size
        return self.cache[ch]
    @staticmethod
    def _runs(vals):
        out, s = [], None
        for i, v in enumerate(vals):
            if v and s is None: s = i
            if not v and s is not None: out.append((s, i)); s = None
        if s is not None: out.append((s, len(vals)))
        return out
    def hruns(self, ch, y):
        px, (w, _) = self.glyph(ch); yy = SIZE - int(y * SIZE / 1000)
        return [((a - SIZE // 2) * 1000 / SIZE, (b - SIZE // 2) * 1000 / SIZE)
                for a, b in self._runs([px[x, yy] for x in range(w)])]
    def vruns(self, ch, x):
        px, (_, h) = self.glyph(ch); xx = SIZE // 2 + int(x * SIZE / 1000)
        return [((SIZE - b) * 1000 / SIZE, (SIZE - a) * 1000 / SIZE)
                for a, b in self._runs([px[xx, y] for y in range(h)])]
    def ring(self, ch, step=5):
        px, _ = self.glyph(ch)
        xs = [x for x in range(SIZE * 2) for y in range(0, SIZE * 2, 8) if px[x, y]]
        ys = [y for y in range(SIZE * 2) for x in range(0, SIZE * 2, 8) if px[x, y]]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        res = {}
        for ang in range(0, 360, step):
            t = math.radians(ang); dx, dy = math.cos(t), -math.sin(t)
            rr, inner, outer = 0, None, None
            while rr < SIZE:
                on = px[int(cx + dx * rr), int(cy + dy * rr)] > 0
                if on and inner is None: inner = rr
                if not on and inner is not None: outer = rr; break
                rr += 1
            res[ang] = (outer - inner) * 1000 / SIZE if outer else None
        return res
    def width_at(self, ch, y, which=0):
        runs = self.hruns(ch, y)
        return r(runs[which][1] - runs[which][0]) if len(runs) > which else None
    def vthick(self, ch, x, near_y):
        for a, b in self.vruns(ch, x):
            if a - 2 <= near_y <= b + 2: return r(b - a)
        return None
    def diag(self, ch, y1, y2):
        a, b = self.hruns(ch, y1), self.hruns(ch, y2)
        if len(a) != len(b): return None
        out = []
        for (x0, x1), (X0, X1) in zip(a, b):
            dy = y2 - y1; dx = (X0 + X1) / 2 - (x0 + x1) / 2; w = (x1 - x0 + X1 - X0) / 2
            out.append({"angle": r(math.degrees(math.atan2(dy, dx))), "thickness": r(w * abs(dy) / math.hypot(dx, dy))})
        return out

def bounds(gs, name):
    p = BoundsPen(gs); gs[name].draw(p); return p.bounds

def measure_style(ttf, style):
    f = TTFont(ttf); cm = f.getBestCmap(); gs = f.getGlyphSet(); ras = Raster(ttf)
    def b(ch): return bounds(gs, cm[ord(ch)])
    out = {"style": style, "glyphs": len(f.getGlyphOrder()), "codepoints": len(cm),
           "italic_angle": f["post"].italicAngle,
           "gsub_features": sorted({x.FeatureTag for x in f["GSUB"].table.FeatureList.FeatureRecord}),
           "gpos_features": sorted({x.FeatureTag for x in f["GPOS"].table.FeatureList.FeatureRecord})}
    out["vertical"] = {
        "flat_x": r(b("x")[3]), "flat_cap": r(b("H")[3]), "round_x_top": r(b("o")[3]), "round_x_bottom": r(b("o")[1]),
        "round_cap_top": r(b("O")[3]), "round_cap_bottom": r(b("O")[1]),
        "ascender_d": r(b("d")[3]), "ascender_b": r(b("b")[3]), "ascender_f": r(b("f")[3]),
        "descender_p": r(b("p")[1]), "descender_q": r(b("q")[1]), "descender_g": r(b("g")[1]), "descender_j": r(b("j")[1]),
        "T_top": r(b("T")[3]), "Z_top": r(b("Z")[3]), "V_bottom": r(b("V")[1]), "A_top": r(b("A")[3])}
    o, O = ras.ring("o"), ras.ring("O")
    def axis(ring):
        up = {a: t for a, t in ring.items() if t and 0 < a < 180}
        amin = min(up, key=up.get); amax_t = max(t for t in ring.values() if t)
        return {"thin_angle_deg": amin, "thin": r(up[amin]), "thick": r(amax_t), "contrast": r(amax_t / up[amin], 2),
                "thickness_by_angle": {str(a): r(t) for a, t in ring.items() if t and a % 15 == 0}}
    out["stress_axis"] = {"o": axis(o), "O": axis(O),
                          "note": "thin_angle_deg: 90 = вертикальная ось нажима; смещение от 90 = наклон оси"}
    out["stems_hairlines"] = {
        "H_stem": ras.width_at("H", 100), "n_stem": ras.width_at("n", 250), "p_stem": ras.width_at("p", 250),
        "d_stem": ras.width_at("d", 250, 1) if style == "Regular" else None, "o_side": ras.width_at("o", 255),
        "H_crossbar": ras.vthick("H", 273, 360), "e_crossbar": ras.vthick("e", 170, 290),
        "H_crossbar_center": None}
    if style != "Regular":  # в курсиве горизонтальный срез захватывает входной штрих: значения не сопоставимы
        for k in ("n_stem", "d_stem", "e_crossbar"): out["stems_hairlines"][k] = None
    cb = [x for x in ras.vruns("H", 273) if x[0] < 500 < x[1] + 400 and 300 < (x[0] + x[1]) / 2 < 450]
    if cb: out["stems_hairlines"]["H_crossbar_center"] = r((cb[0][0] + cb[0][1]) / 2)
    if style == "Regular":
        hb = b("H"); out["serifs"] = {
            "foot_thickness_tip_x20": ras.vthick("H", hb[0] + 11, 10), "foot_thickness_x50": ras.vthick("H", hb[0] + 31, 10),
            "n_foot_thickness_tip": ras.vthick("n", 30, 10), "n_foot_thickness_near_stem": ras.vthick("n", 60, 10),
            "i_head_thickness_tip": ras.vthick("i", 30, 450), "i_head_thickness_near_stem": ras.vthick("i", 60, 450),
            "H_serif_span_left": r(ras.hruns("H", 10)[0][1] - ras.hruns("H", 10)[0][0]),
            "n_foot_runs_y5": [(r(a), r(c)) for a, c in ras.hruns("n", 5)]}
        D = {}
        for name, ch, y1, y2 in [("N", "N", 200, 500), ("V", "V", 216, 504), ("A", "A", 150, 550), ("M", "M", 216, 504),
                                 ("v", "v", 150, 350), ("y", "y", 150, 350), ("w", "w", 250, 330),
                                 ("k_arm", "k", 380, 440), ("k_leg", "k", 60, 140), ("K_arm", "K", 520, 620), ("K_leg", "K", 60, 200),
                                 ("x_lower", "x", 100, 180), ("X_lower", "X", 100, 250), ("Y_arms", "Y", 520, 640),
                                 ("z", "z", 200, 320), ("Z", "Z", 250, 450)]:
            D[name] = ras.diag(ch, y1, y2)
        out["diagonals"] = D
        mc = ras.vruns("M", (b("M")[0] + b("M")[2]) / 2)
        out["M_vertex_bottom"] = r(mc[0][0]) if mc else None
    return out, f, cm, gs

def main():
    ttf_r = f"{REF}/fonts/ttf/InstrumentSerif-Regular.ttf"; ttf_i = f"{REF}/fonts/ttf/InstrumentSerif-Italic.ttf"
    reg, f, cm, gs = measure_style(ttf_r, "Regular")
    ita, fi, cmi, gsi = measure_style(ttf_i, "Italic")
    src = GSFont(f"{REF}/sources/Instrument_Serif.glyphs"); m = src.masters[0]
    params = {"meta": {
        "reference_repo": "https://github.com/Instrument/instrument-serif",
        "reference_commit": subprocess.run(["git", "-C", REF, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "license": "SIL OFL 1.1; Reserved Font Name не объявлен (OFL.txt содержит только строку копирайта)",
        "copyright_line": f["name"].getName(0, 3, 1, 0x409).toUnicode(),
        "note": "Измерено по готовому TTF (ttfautohint), контуры квадратичные. Исходники .glyphs использованы для зон, групп, якорей. Растр 2000 px/em."}}
    params["source_master"] = {
        "upm": src.upm, "ascender": m.ascender, "capHeight": m.capHeight, "xHeight": m.xHeight, "descender": m.descender,
        "alignment_zones": [{"position": z.position, "size": z.size} for z in m.alignmentZones],
        "guides": [{"name": g.name, "y": round(g.position.y), "x": round(g.position.x)} for g in m.guides],
        "custom_parameters": {p.name: p.value for p in m.customParameters},
        "feature_tags": [ft.name for ft in src.features]}
    params["regular"] = reg; params["italic"] = ita
    spacing = {}
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
        g = cm[ord(ch)]; bb = bounds(gs, g); adv = f["hmtx"][g][0]
        row = {"adv": adv, "lsb": r(bb[0]), "rsb": r(adv - bb[2]), "ymin": r(bb[1]), "ymax": r(bb[3])}
        sg = src.glyphs[g]
        if sg is not None and (sg.leftKerningGroup or sg.rightKerningGroup):
            row["kern_left_group"] = sg.leftKerningGroup; row["kern_right_group"] = sg.rightKerningGroup
        spacing[ch] = row
    params["spacing_regular"] = spacing
    gi = {}
    for ch in "HOno":
        g = cmi[ord(ch)]; bb = bounds(gsi, g); gi[ch] = {"adv": fi["hmtx"][g][0], "lsb": r(bb[0]), "rsb": r(fi["hmtx"][g][0] - bb[2])}
    params["spacing_italic_sample"] = gi
    acc = {}
    for name in ("acutecomb", "gravecomb", "uni0308", "uni0306", "uni0301"):
        if name in f.getGlyphOrder():
            bb = bounds(gs, name)
            if bb: acc[name] = {"ymin": r(bb[1]), "ymax": r(bb[3]), "adv": f["hmtx"][name][0]}
    comp = f["glyf"]
    for name in ("Edieresis", "edieresis", "Abreve", "abreve", "Eacute"):
        gl = comp[name]; acc[name] = {"components": [(c.glyphName, c.x, c.y) for c in gl.components], "ymax": r(bounds(gs, name)[3])}
    gl = max(((n, bounds(gs, n)[3]) for n in f.getGlyphOrder() if bounds(gs, n)), key=lambda t: t[1])
    gb = min(((n, bounds(gs, n)[1]) for n in f.getGlyphOrder() if bounds(gs, n)), key=lambda t: t[1])
    acc["extremes"] = {"top": [gl[0], r(gl[1])], "bottom": [gb[0], r(gb[1])]}
    acc["rule_capital_accent_raise"] = {"value": src.masters[0].capHeight - src.masters[0].xHeight, "note": "capHeight − xHeight; применяется как y-смещение знака в композитах Ё, Й и т. п."}
    ra = src.glyphs["E"].layers[m.id].anchors; ea = src.glyphs["e"].layers[m.id].anchors
    acc["anchors_source"] = {"E": {a.name: [round(a.position.x), round(a.position.y)] for a in ra},
                             "e": {a.name: [round(a.position.x), round(a.position.y)] for a in ea},
                             "acutecomb": {a.name: [round(a.position.x), round(a.position.y)] for a in src.glyphs["acutecomb"].layers[m.id].anchors},
                             "brevecomb": {a.name: [round(a.position.x), round(a.position.y)] for a in src.glyphs["brevecomb"].layers[m.id].anchors},
                             "dieresiscomb": {a.name: [round(a.position.x), round(a.position.y)] for a in src.glyphs["dieresiscomb"].layers[m.id].anchors}}
    params["accents"] = acc
    ss = {}
    for g in f.getGlyphOrder():
        if g.endswith(".ss01"):
            base = g[:-5]; b0, b1 = bounds(gs, base), bounds(gs, g)
            ss[g] = {"d_xmin": r(b1[0] - b0[0]), "d_ymin": r(b1[1] - b0[1]), "d_xmax": r(b1[2] - b0[2]), "d_ymax": r(b1[3] - b0[3]),
                     "adv_base": f["hmtx"][base][0], "adv_alt": f["hmtx"][g][0]}
    params["ss01_deltas_vs_base"] = ss
    need = {"U+02BC modifier apostrophe": 0x2BC, "U+2116 numero": 0x2116, "U+20B8 tenge": 0x20B8, "U+20BD ruble": 0x20BD,
            "U+20B4 hryvnia": 0x20B4, "U+25CC dotted circle": 0x25CC, "U+2009 thin space": 0x2009, "U+202F narrow nbsp": 0x202F,
            "U+2010 hyphen": 0x2010, "U+2011 nb hyphen": 0x2011, "U+2012 figure dash": 0x2012, "U+2015 horizontal bar": 0x2015,
            "U+2032 prime": 0x2032, "U+2033 double prime": 0x2033, "U+2007 figure space": 0x2007, "U+200A hair space": 0x200A,
            "U+2002 en space": 0x2002, "U+2003 em space": 0x2003, "U+200B zero width space": 0x200B, "U+259 schwa": 0x259,
            "U+18F Schwa": 0x18F, "U+2020 dagger": 0x2020, "U+FFFD replacement": 0xFFFD, "U+2248 approx": 0x2248}
    have = {"U+00A0 nbsp": 0xA0, "U+00AB guillemotleft": 0xAB, "U+00BB guillemotright": 0xBB, "U+201E quotedblbase": 0x201E,
            "U+201C quotedblleft": 0x201C, "U+2014 emdash": 0x2014, "U+2013 endash": 0x2013, "U+2212 minus": 0x2212,
            "U+00A7 section": 0xA7, "U+00B0 degree": 0xB0, "U+2030 permille": 0x2030, "U+2026 ellipsis": 0x2026,
            "U+0301 acutecomb": 0x301, "U+0300 gravecomb": 0x300, "U+0308 dieresiscomb": 0x308, "U+0306 brevecomb": 0x306,
            "U+0131 dotlessi": 0x131}
    params["coverage"] = {"cyrillic_codepoints_U0400_052F": sum(1 for c in cm if 0x400 <= c <= 0x52F),
                          "absent_must_draw_or_decide": [k for k, v in need.items() if v not in cm],
                          "present_reusable": [k for k, v in have.items() if v in cm],
                          "latin_homoglyph_donors_present": all(ord(c) in cm for c in "ABEKMHOPCTXaeopcxy")}
    k = f["GPOS"].table.LookupList.Lookup[0]
    pair1 = sum(len(s.PairSet) for s in k.SubTable if getattr(s, "Format", 0) == 1)
    params["kerning"] = {"pairs_in_source": sum(len(v) for v in src.kerning.get(m.id, {}).values()),
                         "first_level_keys": len(src.kerning.get(m.id, {})),
                         "groups": len({g.leftKerningGroup for g in src.glyphs if g.leftKerningGroup} | {g.rightKerningGroup for g in src.glyphs if g.rightKerningGroup}),
                         "gpos_pairpos_fmt1_pairsets": pair1}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh: json.dump(params, fh, ensure_ascii=False, indent=1)
    print("written", OUT, os.path.getsize(OUT), "bytes")

if __name__ == "__main__":
    main()
