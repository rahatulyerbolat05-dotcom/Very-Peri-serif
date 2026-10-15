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


import math

def _arc(pen, cx, cy, a, b, t0, t1, n=6):
    """Дуга эллипса от угла t0 до t1 (радианы) квадратичными кривыми; перо уже стоит в начальной точке."""
    dt = (t1 - t0) / n
    for i in range(n):
        ta = t0 + i * dt; tm = ta + dt / 2; tb = ta + dt; k = 1 / math.cos(dt / 2)
        pen.qCurveTo((cx + a * math.cos(tm) * k, cy + b * math.sin(tm) * k), (cx + a * math.cos(tb), cy + b * math.sin(tb)))

def _inner_ellipse(a, b, t_top, t_l, t_r, beta, alpha):
    """Внутренний эллипс (контрформа арки) так, чтобы толщины ног, измеренные по нормали к ним, были t_l (левая) и t_r (правая),
    а толщина вершины t_top. Опорная функция эллипса: h(n) = n·c + sqrt(a²nx² + b²ny²). Возвращает (a_in, b_in, δ)."""
    cL, sL, cR, sR = math.cos(beta), math.sin(beta), math.cos(alpha), math.sin(alpha)
    b_in = b - t_top
    f = lambda ain, c, s: math.sqrt(a * a * c * c + b * b * s * s) - math.sqrt(ain * ain * c * c + b_in * b_in * s * s)
    g = lambda ain: (t_l - f(ain, cL, sL)) / cL - (f(ain, cR, sR) - t_r) / cR
    lo, hi = 5.0, a - 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if g(lo) * g(mid) <= 0: hi = mid
        else: lo = mid
    ain = (lo + hi) / 2
    return ain, b_in, (t_l - f(ain, cL, sL)) / cL

def el_sign(ref, beta_deg=14.0, alpha_deg=None, gap_target=226.0, a=130.0, b=170.0, top=730.0, t_l=30.0, t_r=71.0, t_top=27.0, donor="H", LB=89, RB=160):
    """Заглавная Л (карточка docs/glyphs/el.md): арка и две ноги. Левая нога тонкая и наклонена влево (угол beta от вертикали),
    правая толстая со слабым расхождением вниз (alpha). Построена параметрически, по измерениям:
    толщины: тонкая диагональ A, V 30–31; стойка H 71; волосная вершины O 27; высота 730 (овершут круглого верха);
    засечки внизу: половины опорной засечки H (скобка встаёт на стойку на высоте 60), прикрепляются к краям ног.
    Если alpha_deg=None, alpha подбирается так, чтобы просвет между ногами у основания равнялся gap_target (по умолчанию 226:
    контрформа между стойками H). Для строчной л (карточка docs/glyphs/el_lower.md): top=516, donor="dotlessi", LB=79, RB=147.
    Возвращает (контур, словарь параметров)."""
    H = ref.glyph(donor); ATT = 60                                    # стойка H: 89–160, ı: 79–147; скобка засечки встаёт на y=60
    beta = math.radians(beta_deg)
    y_e = top - b

    def geometry(alpha):
        ain, bin_, dl = _inner_ellipse(a, b, t_top, t_l, t_r, beta, alpha)
        tb, ta = math.tan(beta), math.tan(alpha)
        uL, uR = math.atan(b / a * tb), math.atan(b / a * ta)
        uLi, uRi = math.atan(bin_ / ain * tb), math.atan(bin_ / ain * ta)
        P = {"oL": (-a * math.cos(uL), y_e + b * math.sin(uL)), "oR": (a * math.cos(uR), y_e + b * math.sin(uR)),
             "iL": (dl - ain * math.cos(uLi), y_e + bin_ * math.sin(uLi)), "iR": (dl + ain * math.cos(uRi), y_e + bin_ * math.sin(uRi))}
        X = {"oL": P["oL"][0] - (P["oL"][1] - ATT) * tb, "iL": P["iL"][0] - (P["iL"][1] - ATT) * tb,
             "oR": P["oR"][0] + (P["oR"][1] - ATT) * ta, "iR": P["iR"][0] + (P["iR"][1] - ATT) * ta}
        return ain, bin_, dl, uL, uR, uLi, uRi, P, X

    if alpha_deg is None:                                           # просвет у основания = gap_target: подбор угла правой ноги
        lo, hi = 0.0, math.radians(12)
        for _ in range(60):
            mid = (lo + hi) / 2; X = geometry(mid)[-1]
            if X["iR"] - X["iL"] < gap_target: lo = mid
            else: hi = mid
        alpha = (lo + hi) / 2
    else:
        alpha = math.radians(alpha_deg)
    ain, bin_, dl, uL, uR, uLi, uRi, P, X = geometry(alpha)

    po = Path(); q = po.getPen()                                      # внешний контур: арка и ноги до y=0
    q.moveTo((X["oL"], 0)); q.lineTo((X["oL"], ATT)); q.lineTo(P["oL"])
    _arc(q, 0, y_e, a, b, math.pi - uL, uR)
    q.lineTo((X["oR"], ATT)); q.lineTo((X["oR"], 0)); q.closePath()
    pi_ = Path(); q = pi_.getPen()                                    # контрформа, открытая вниз
    q.moveTo((X["iL"], -60)); q.lineTo((X["iL"], ATT)); q.lineTo(P["iL"])
    _arc(q, dl, y_e, ain, bin_, math.pi - uLi, uRi)
    q.lineTo((X["iR"], ATT)); q.lineTo((X["iR"], -60)); q.closePath()
    body = SUB(po, pi_)
    pieceL = AND(H, rect(-50, -50, LB, ATT)); pieceR = AND(H, rect(RB, -50, 300, ATT))   # половины засечки H вне стойки
    feet = [shift(pieceL, X["oL"] - LB), shift(pieceR, X["iL"] - RB),                   # левая нога: засечка слева и справа от тонкой ноги
            shift(pieceL, X["iR"] - LB), shift(pieceR, X["oR"] - RB)]                   # правая нога
    path = OR(body, *feet)
    bb = path.bounds; dx = 19 - bb[0]                                 # левое поле 19, как у H
    path = shift(path, dx)
    info = {"beta_deg": beta_deg, "alpha_deg": round(math.degrees(alpha), 2), "gap_at_baseline": round(X["iR"] - X["iL"], 1),
            "a_in": round(ain, 1), "delta": round(dl, 1), "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1)}
    return path, info
