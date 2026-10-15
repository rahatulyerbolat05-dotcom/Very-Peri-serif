#!/usr/bin/env python3
"""Проверка класса @serif_bl (контекстная форма pe-cy.flag, docs/glyphs/pe.md, CLAUDE.md раздел 7) по геометрии, а не по списку.
Для каждой готовой основы (data/context/serif_bl.json, built_bases) считает критерий A, B, C и сравнивает с declared_class и expected_not_in_class.
При расхождении печатает его и завершается с кодом 1: перед сборкой пересмотреть класс. Запуск: python3 -I tools/check_context_classes.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pathops
from pathops import Path
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from sketchlib import AND, rect

CFG = json.load(open("data/context/serif_bl.json", encoding="utf-8"))
declared = set(CFG["declared_class"]["lower"]) | set(CFG["declared_class"]["upper"])
expected_out = set(CFG["expected_not_in_class"])
C = CFG["criterion"]

def load(path):
    class G: pass
    p = Path(); readGlyphFromString(open(path, encoding="utf-8").read(), G(), PointToSegmentPen(p.getPen())); return p

def leftmost(p, y0, y1):
    s = AND(p, rect(-1000, y0, 3000, y1))
    return s.bounds[0] if list(s.contours) else None

def test(p):
    xa = leftmost(p, 0, 12)
    if xa is None: return False, "нет контура у базовой линии"
    a = xa <= 60
    x150 = leftmost(p, 150, 151)
    b = x150 is not None and x150 - xa >= 35
    cs = AND(p, rect(-1000, -10, 120, 3))
    c = bool(list(cs.contours))
    return (a and b and c), f"A x={xa:.0f} (<=60: {a}), B x150-xA={(x150 - xa) if x150 is not None else None:.0f} (>=35: {b}), C {c}" if x150 is not None else f"A x={xa:.0f}"

def runs_at(p, y):
    from fontTools.pens.recordingPen import RecordingPen
    sl = AND(p, rect(-1000, y, 3000, y + 1))
    if not list(sl.contours): return []
    rp = RecordingPen(); sl.draw(rp)
    xs = sorted(pt[0] for op, a in rp.value for pt in a)
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= 1.5: groups[-1].append(x)
        else: groups.append([x])
    cent = [sum(g) / len(g) for g in groups]
    return [(cent[i], cent[i + 1]) for i in range(0, len(cent) - 1, 2)]

def test_top(p):
    rs = runs_at(p, 380)
    if not rs: return False, "нет контура на y=380"
    x0, x1 = rs[0]; w = x1 - x0
    c1 = 25 <= w <= 90
    xa = leftmost(p, 470, 512)
    c2 = xa is not None and xa <= x0 + 10
    return (c1 and c2), f"C1 первая стойка на y=380: x {x0:.0f}..{x1:.0f}, ширина {w:.0f} (25..90: {c1}); C2 верх у левого края: x_top={xa if xa is None else round(xa)} (<= {x0 + 10:.0f}: {c2})"

bad = 0
for ch, path in CFG["built_bases"].items():
    ok, why = test(load(path))
    want = ch in declared
    status = "ok" if ok == want else "РАСХОЖДЕНИЕ"
    if ok != want: bad += 1
    print(f"{ch}  в классе по геометрии: {ok!s:5}  в declared_class: {want!s:5}  {status}  [{why}]")
missing = [ch for ch in sorted(declared) if ch not in CFG["built_bases"]]
print("нет контура (не проверены):", " ".join(missing))
if bad: print(f"\nРАСХОЖДЕНИЙ: {bad}. Пересмотреть класс @serif_bl и правило calt."); sys.exit(1)
print("\nвсе готовые основы согласованы с declared_class")


# второе правило: ka-cy -> ka-cy.short перед буквой с засечкой слева вверху на x-height
KA = CFG["ka_short"]; kdec = set(KA["declared_class"]["lower"]) | set(KA["declared_class"]["upper"])
print("\nправило ka-cy.short (верхний левый угол следующей буквы):")
bad2 = 0
for ch, path in CFG["built_bases"].items():
    if ch.isupper(): continue
    ok, why = test_top(load(path)); want = ch in kdec
    st = "ok" if ok == want else "РАСХОЖДЕНИЕ"
    if ok != want: bad2 += 1
    print(f"{ch}  по геометрии: {ok!s:5}  в declared_class: {want!s:5}  {st}  [{why}]")
print("нет контура (не проверены):", " ".join(sorted(ch for ch in kdec if ch not in CFG["built_bases"])))
if bad2: print(f"\nРАСХОЖДЕНИЙ в правиле ka-cy.short: {bad2}"); sys.exit(1)
print("правило ka-cy.short: все готовые основы согласованы")
