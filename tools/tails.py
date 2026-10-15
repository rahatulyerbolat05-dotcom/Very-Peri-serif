"""Принцип хвостов (карточка docs/tails.md): хвост под строкой собирается только из модулей оригинала, без масштаба, и вешается на стойку базы.
Модули нормированы так: стойка модуля на высоте y = 60 занимает x от 0 до ширины стойки (68 строчные, 71 прописные), всё, что ниже y = 60, принадлежит модулю.
База обрезается под этой стойкой ниже y = 60 (`cut_stem`), модуль ставится по левому краю стойки (`attach`); шов на y = 60 идёт по вертикальной стойке одинаковой ширины.
  K1 прямой: стойка до −205 и плоская засечка (строчные: p оригинала; прописные: стойка H и её опорная засечка, опущенная на −205).
  K2 крюк наружу: стойка уходит под строку с утончением и заканчивается каплей на −215 (строчные: j оригинала, прописные: J оригинала), зеркально, чтобы крюк шёл наружу буквы.
  K3 огонек: ogonekcomb оригинала без изменений на якоре у правого края стойки, как в Į (якорь ogonek у I на (160, 0), это правый край стойки I); стойка базы не обрезается."""
from sketchlib import *

def _module_from(ref, glyph, stem_left, mirror):
    """Нижняя часть глифа-донора (y < 60) как модуль: стойка в 0..w, при mirror зеркально (крюк смотрит вправо)."""
    p = AND(ref.glyph(glyph), rect(-300, -400, 1200, 60))
    if mirror:
        p = tf(p, (-1, 0, 0, 1, 0, 0))
        b = AND(p, rect(-1200, 40, 1200, 60)).bounds                     # стойка на y 40–60 после зеркала
        return shift(p, -b[0])
    return shift(p, -stem_left)

def module(ref, kind, cap, side="right"):
    """Модуль хвоста. kind: "K1" прямой, "K2" крюк наружу. side: "right" (крюк вправо) или "left" (влево, для левой ножки Д)."""
    if kind == "K2":
        donor, sl = ("J", 89.0) if cap else ("j", 79.0)
        return _module_from(ref, donor, sl, mirror=(side == "right"))
    if kind == "K1":
        if not cap:                                                      # p: только стойка 73–141 и засечка на −205, без чаши p (она заходит ниже y = 60)
            P = ref.glyph("p")
            m = SUB(AND(P, rect(-300, -400, 400, 60)), rect(141.0, -20, 400, 60))   # срез по правому краю стойки p (141) выше −20: чаша уходит, стойка 68 как у базы
            return shift(m, -73.0)
        H = ref.glyph("H")
        stem_and_foot = AND(H, rect(-100, -50, 273, 265))               # левая стойка H 89–160 от низа до y = 265, с опорной засечкой
        return shift(stem_and_foot, -89.0, -205.0)                       # опущена на 205: засечка на −205, стойка доходит до y = 60 без стыка
    raise ValueError(kind)

def cut_stem(base, stem_left, stem_right, y=60.0, y_exit=120.0):
    """Убрать у базы всё правее левого края стойки и ниже y (ножка, засечка этой стойки), и всё правее правого края стойки ниже y_exit:
    у стоек с хвостом-выходом (н n4, ш R1) выход начинается выше 60 (у n4 правый край уходит в хвост с y = 107), его остаток дал бы ступеньку."""
    return SUB(base, OR(rect(stem_left, -400, 2000, y), rect(stem_right, -400, 2000, y_exit)))

def attach(base, mod, stem_left):
    p = OR(base, shift(mod, stem_left)); p.simplify(); return p

def ogonek_on(ref, base, anchor_x):
    """K3: ogonekcomb оригинала (якорь _ogonek (194, 0)) в точке anchor_x на базовой линии. Как в оригинале: у стоечных букв на правом краю стойки (I: 160),
    у букв с ножкой-выходом в точке ножки (u: 336, a: 344)."""
    p = OR(base, shift(ref.glyph("ogonek"), anchor_x - 194.0)); p.simplify(); return p

# K4 цельный огонек: брюшко и загнутый кончик огонька оригинала, тонкое крепление заменено продолжением стойки.
# Оба края хвоста идут от стойки одной гладкой линией (касательная сохраняется на каждом стыке), без бугра на шве.
import math
from fontTools.pens.recordingPen import RecordingPen

def ogonek_points(ref):
    """точки ogonekcomb (uni0328) оригинала, квадратичные, с признаком on-curve [ИЗМЕРЕНО]"""
    g = ref.font["glyf"]; c = g[g["ogonek"].components[0].glyphName]
    coords, ends, flags = c.getCoordinates(g)
    return [(tuple(map(float, p)), bool(f & 1)) for p, f in zip(coords, flags)]

def depart(p0, c, p1, deg):
    """точка на квадратичной кривой p0-c-p1, где касательная идёт влево-вниз под deg к горизонтали;
    возвращает (ctrl левой половины, точку, единичную касательную): дуга режется без изменения формы"""
    def ang(t):
        dx = (1 - t) * (c[0] - p0[0]) + t * (p1[0] - c[0]); dy = (1 - t) * (c[1] - p0[1]) + t * (p1[1] - c[1])
        return math.degrees(math.atan2(-dy, -dx))
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if ang(m) > deg: lo = m
        else: hi = m
    t = (lo + hi) / 2
    a = (p0[0] + (c[0] - p0[0]) * t, p0[1] + (c[1] - p0[1]) * t); b = (c[0] + (p1[0] - c[0]) * t, c[1] + (p1[1] - c[1]) * t)
    m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    L = math.hypot(m[0] - a[0], m[1] - a[1])
    return a, m, ((m[0] - a[0]) / L, (m[1] - a[1]) / L)

def ogonek_stroke(ref, anchor_x, stem_left, stem_right, y_join, top, right_side, dep, ddir, belly=46.0, ka=55.0, kb=50.0):
    """Контур хвоста K4. anchor_x: якорь огонька, как у K3 (брюшко огонька на месте оригинала);
    stem_left, stem_right, y_join: края стойки и высота, где наружный край уходит от стойки;
    top: верх врезки; right_side: сегменты правой стороны от (stem_right, top) до точки отхода dep (деталь базы: шпора u или засечка H);
    ddir: касательная в dep; belly: ширина брюшка (46 огонек оригинала или ширина стойки);
    ka, kb: длины ручек наружной S-линии у брюшка и у стойки."""
    P = ogonek_points(ref); off = anchor_x - 194.0
    O = [(x + off, y) for (x, y), _ in P]
    ox = O[3][0]; ix = ox + belly
    s = (dep[0] - ix) / (-ddir[0]); C = (ix, dep[1] + s * ddir[1])
    p = Path(); q = p.getPen()
    q.moveTo(O[0]); q.qCurveTo(O[1], O[2], O[3])
    q.qCurveTo((ox, O[3][1] + ka), (stem_left, y_join - kb), (stem_left, y_join))
    if top > y_join: q.lineTo((stem_left, top))
    q.lineTo((stem_right, top))
    for op, pts in right_side: getattr(q, op)(*pts)
    q.qCurveTo(C, (ix, O[11][1]))
    if belly == 46.0: q.qCurveTo(O[12], O[13], O[14])
    else: q.qCurveTo((ix, O[14][1]), O[14])
    q.qCurveTo(O[15], O[16]); q.qCurveTo(O[17], O[18]); q.qCurveTo(O[19], O[20]); q.qCurveTo(O[21], O[22], O[0]); q.closePath()
    return p

def drop_collinear(p):
    """убрать точки, лежащие на прямой между двумя отрезками (остаются от шва врезки)"""
    r = RecordingPen(); p.draw(r); out = Path(); pen = out.getPen(); conts, cur = [], []
    for op, a in r.value:
        if op == "moveTo": cur = [a[0]]
        elif op in ("closePath", "endPath"): conts.append(cur); cur = []
        else: cur.append((op, a))
    for c in conts:
        start, segs = c[0], c[1:]
        if segs[-1][1][-1] != start: segs.append(("lineTo", (start,)))
        n = len(segs); ends = [s[1][-1] for s in segs]; keep = [True] * n
        for i in range(n):
            j = (i + 1) % n
            if segs[i][0] == "lineTo" and segs[j][0] == "lineTo":
                p0, p1, p2 = ends[i - 1], ends[i], ends[j]
                if abs((p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])) < 1e-6: keep[i] = False
        segs = [s for s, k in zip(segs, keep) if k]
        pen.moveTo(segs[-1][1][-1])
        for op, a in segs: getattr(pen, op)(*a)
        pen.closePath()
    return out

def k4_on(base, cut_x, top, tail):
    """база без низа правой стойки (правее cut_x, ниже top) плюс хвост K4"""
    p = OR(SUB(base, rect(cut_x, -400, 2000, top)), tail); p.simplify(); return drop_collinear(p)

def k4(ref, key, base, belly):
    """K4 на пробных базах: Ң (H), ң (n4), щ (R1). Правая сторона: у u-стойки шпора выхода, отход по 38°
    (угол снят с рисунка автора проекта); у H правая половина опорной засечки, отход по её низу (горизонталь)."""
    if key == "En":
        right = [("lineTo", ((457.0, 66.0),)), ("qCurveTo", ((457.0, 45.0), (470.0, 31.0), (491.0, 27.0))), ("lineTo", ((514.0, 23.0),)),
                 ("qCurveTo", ((527.0, 20.0), (527.0, 11.0))), ("qCurveTo", ((527.0, 0.0), (512.0, 0.0)))]
        tail = ogonek_stroke(ref, 457.0, 386.0, 457.0, 67.0, 67.0, right, (512.0, 0.0), (-1.0, 0.0), belly)
        return k4_on(base, 306.0, 67.0, tail)
    sl, sr, tip, anchor, cut = {"en": (324.0, 392.0, 451.0, 348.0, 300.0), "shcha": (567.0, 630.0, 689.0, 584.0, 567.0)}[key]
    t0, c0, t1 = ((tip, 61.0), (tip, 52.0), (tip - 16.0, 49.0)) if key == "en" else ((tip, 60.0), (tip, 52.0), (tip - 16.0, 49.0))
    a, D, d = depart(t0, c0, t1, 38.0)
    right = [("qCurveTo", ((sr, 89.0), (sr + 11.0, 76.0), (sr + 25.0, 74.0))), ("lineTo", ((tip - 13.0, 71.0),)),
             ("qCurveTo", ((tip, 70.0), t0)), ("qCurveTo", (a, D))]
    tail = ogonek_stroke(ref, anchor, sl, sr, 54.0, 107.0, right, D, d, belly)
    return k4_on(base, cut, 107.0, tail)
