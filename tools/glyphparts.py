"""Общие детали глифов, которые используются в нескольких буквах (одна сборка = одна форма везде)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sketchlib import *

STEM_X = 62        # левый край стойки ь (как у b), ширина 68

def soft_sign(ref, kind="flag"):
    """Строчная ь (карточка docs/glyphs/soft.md). Возвращает (контур, правая граница чаши).
    kind: "flag" (S3, наклонный флажок ı; выбран автором проекта) или "u" (S4, плоская засечка как у u)."""
    A, I, U = (ref.glyph(n) for n in ("a", "dotlessi", "u"))
    body_i = AND(I, rect(-50, 60, 400, 700))
    head = shift(AND(body_i, rect(-50, 400, 400, 700)), STEM_X - 79) if kind == "flag" \
        else shift(AND(U, rect(-50, 400, 150, 700)), STEM_X - 70)
    # нижняя чаша a (стойка 245–313, чаша до x=24) зеркально: x' = 375 − x → стойка 62–130; стойку и хвост a отсекаем (x < 130)
    bowl = AND(tf(AND(A, rect(-50, -50, 700, 325)), (-1, 0, 0, 1, 375, 0)), rect(130, -50, 700, 400))
    foot_l = shift(AND(I, rect(-50, -50, 113, 60)), STEM_X - 79)               # левая половина опорной засечки ı
    path = OR(bowl, rect(STEM_X, 0, STEM_X + 68, 410), head, foot_l)
    return path, 130 + 221


def hard_sign(ref, serif_depth=0, bar_extra=46):
    """Строчная ъ (карточка docs/glyphs/hard.md): ь с головкой как у u, головка удлинена в перекладину слева
    (перекладина не доходит до чаши), на левом конце засечка вниз глубиной serif_depth (0: без засечки).
    Перекладина с засечкой строится одним контуром, как левый конец перекладины T: левый край вертикальный,
    верхний угол закруглён, вогнутая скобка плавно входит в низ перекладины (швов от склейки кусков нет).
    Измерено у T: ширина засечки 70 на глубине 40, 54 на 100, 37 на 140.
    Возвращает (контур, правая граница чаши)."""
    base, bowl_r = soft_sign(ref, "u")                         # стойка 62–130 с головкой u, чаша, засечка внизу
    tx = 3 - bar_extra                                         # левый кончик перекладины до общего сдвига вправо
    top, bot = 510, 483                                        # верх и низ перекладины (толщина 27; кончик u: 24–26, у стойки 28–32)
    p = Path(); q = p.getPen()
    q.moveTo((tx, top - 10)); q.qCurveTo((tx, top), (tx + 10, top)); q.lineTo((60, top)); q.lineTo((60, bot))
    if serif_depth:
        yb = bot - serif_depth
        q.lineTo((tx + 110, bot)); q.qCurveTo((tx + 42, bot), (tx + 36, yb + 14))
        q.qCurveTo((tx + 36, yb), (tx + 18, yb)); q.qCurveTo((tx, yb), (tx, yb + 14))
    else:
        q.lineTo((tx + 13, bot)); q.qCurveTo((tx, bot), (tx, bot + 13))
    q.closePath()
    path = OR(SUB(base, rect(-50, 470, 32, 520)), p)           # кончик головки u заменяет новый левый конец
    return shift(path, bar_extra), bowl_r + bar_extra          # весь глиф вправо: левый кончик снова около x=3
