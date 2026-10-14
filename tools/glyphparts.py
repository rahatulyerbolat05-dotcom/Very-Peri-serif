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
