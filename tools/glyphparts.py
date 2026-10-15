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


def em_sign(ref, apex=26.0, lean_deg=2.0, gamma_deg=16.0, t_l=30.0, t_r=68.0, t_d1=67.0, t_d2=29.0, head_l="u", join=18.0, flat=8.0):
    """Строчная м (карточка docs/glyphs/em.md): две стойки и V между ними, роли штрихов от латинской M:
    левая стойка тонкая, правая толстая, «\\» толстая, «/» тонкая. Стойки наклонены внутрь на lean_deg (у M 88° и 92°),
    диагонали на gamma_deg от вертикали (строчные v, y, w: 16–17°; у заглавных A, V, M 14°). Вершина V на высоте apex (у M 37 из 720, то есть 26 из 510).
    Верх стоек: засечка-головка слева, как у u и v (head_l="u") или косой флажок ı у левой стойки (head_l="flag");
    низ: половины опорной засечки ı. Диагонали входят в стойки сверху на join (без этого контакт в точке).
    Возвращает (контур, словарь параметров)."""
    I, U = ref.glyph("dotlessi"), ref.glyph("u")
    X = 510.0; tl_ = math.tan(math.radians(lean_deg)); tg = math.tan(math.radians(gamma_deg))
    run = (X - apex) * tg
    h1, h2 = t_d1 / math.cos(math.radians(gamma_deg)), t_d2 / math.cos(math.radians(gamma_deg))   # горизонтальные ширины диагоналей
    L0 = 0.0                                                             # левый край левой стойки у основания
    # верхние внутренние края: слева L0 + t_l + X*tl_, справа R_i0 − X*tl_; диагонали входят в стойки на join
    sLi = L0 + t_l + X * tl_ - join
    xv = sLi + run + flat / 2                                            # середина вершины
    sRi = xv + flat / 2 + run - join * 0 + 0                              # край "/" у верха; правая стойка начинается в sRi − (t_d2 доли)
    R_i0 = (xv + flat / 2 + run) - 0 + X * tl_ - join                    # внутренний край правой стойки у основания (так, чтобы "/" входила на join)
    R_o0 = R_i0 + t_r
    stemL = poly((L0, 0), (L0 + t_l, 0), (L0 + t_l + X * tl_, X), (L0 + X * tl_, X))
    stemR = poly((R_i0, 0), (R_o0, 0), (R_o0 - X * tl_, X), (R_i0 - X * tl_, X))
    xl = lambda y: xv - flat / 2 - (y - apex) * tg                        # левый край "\"
    xr = lambda y: xv + flat / 2 + (y - apex) * tg                        # правый край "/"
    y0, y1 = apex - 30, X + 10
    d1 = poly((xl(y0), y0), (xl(y1), y1), (xl(y1) + h1, y1), (xl(y0) + h1, y0))
    d2 = poly((xr(y0) - h2, y0), (xr(y1) - h2, y1), (xr(y1), y1), (xr(y0), y0))
    wedge = poly((xv - flat / 2, apex), (xv + flat / 2, apex), (xr(X + 10), X + 10), (xl(X + 10), X + 10))
    diag = AND(AND(OR(d1, d2), wedge), rect(-500, -60, 3000, X))
    # головки: слева от стойки на высоте верха (стойка наклонена, смещение по x у верха)
    xtopL, xtopR = L0 + X * tl_, R_i0 - X * tl_
    if head_l == "flag":
        hl = shift(AND(I, rect(-50, 440, 79, 700)), xtopL - 79)
    else:
        hl = shift(AND(U, rect(-50, 400, 70, 700)), xtopL - 70)
    hr = shift(AND(U, rect(-50, 400, 70, 700)), xtopR - 70)
    # низ: половины опорной засечки ı у основания обеих стоек
    fL, fR = AND(I, rect(-50, -50, 79 + 6, 60)), AND(I, rect(147 - 6, -50, 300, 60))     # заходят на 6 внутрь стойки: без швов
    feet = [shift(fL, L0 - 79), shift(fR, L0 + t_l - 147), shift(fL, R_i0 - 79), shift(fR, R_o0 - 147)]
    path = OR(stemL, stemR, diag, hl, hr, *feet)
    path = AND(path, rect(-100, -60, 2000, 516))
    dx = 15 - path.bounds[0]; path = shift(path, dx)
    info = {"apex": apex, "head_l": head_l, "lean_deg": lean_deg, "gamma_deg": gamma_deg, "weights": [t_l, t_r, t_d1, t_d2],
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def te_sign(ref, overhang=150.0, serif_depth=70.0, bar_t=27.0, stem=68.0, ear="serif", ear_w=35.0, fillet=28.0, tip_t=22.0, root_t=32.0):
    """Строчная т (карточка docs/glyphs/te.md): горизонталь с засечками вниз на обоих концах и центральная стойка с опорной засечкой.
    Конец горизонтали тот же, что у ъ (K2, hard_sign): одним контуром, верхний угол закруглён, скобка засечки по замеру T
    (ширина 70 на глубине 40, 54 на 100, 37 на 140). Ножка: нижняя часть ı (опорная засечка F2), стойка ı 79–147 (68).
    overhang: вылет горизонтали от края стойки до кончика; каждый конец одинаковый (зеркало относительно оси стойки).
    ear: "none" (без ушек, по наброску автора проекта: прямая горизонталь с плоскими концами, толщина сужается от root_t у стойки до tip_t на кончике, как у головной засечки: 32 → 20–23), "serif" (засечка вниз, как у ъ K2), "user" (ушко по наброску автора проекта: вертикальный внешний край, круглый низ шириной ear_w, большое сопряжение fillet с низом горизонтали, глубина serif_depth) или "drop" (каплевидное ушко F5: на конце горизонтали капля радиуса 30, свисающая на 40 ниже, сопряжение скруглено)."""
    I = ref.glyph("dotlessi")
    top, bot = 510.0, 510.0 - bar_t
    cx = overhang + stem / 2; tx = 0.0
    p = Path(); q = p.getPen(); yb = bot - serif_depth
    if ear == "none":
        L = cx - tx                                                             # от кончика до оси стойки
        bar = poly((tx, top), (cx, top), (cx, top - root_t), (tx, top - tip_t))
        top_stem = rect(cx - stem / 2, 400, cx + stem / 2, top)
        p = soften(OR(bar, top_stem), 5, 16)
        p = AND(p, rect(-100, -100, cx, 600))                                   # левая половина, правая будет зеркалом
    elif ear == "user":
        rr = ear_w / 2
        cap = Path(); cq = cap.getPen()
        cq.moveTo((tx, top - 13)); cq.qCurveTo((tx, top), (tx + 13, top)); cq.lineTo((cx, top)); cq.lineTo((cx, bot)); cq.lineTo((tx + ear_w, bot))
        cq.lineTo((tx + ear_w, yb + rr)); _arc(cq, tx + rr, yb + rr, rr, rr, 0.0, -math.pi, n=6); cq.lineTo((tx, yb + rr)); cq.closePath()
        p = soften(cap, 0, fillet)
    elif ear == "drop":
        rd = 30.0; ccx, ccy = tx + rd, bot - 10.0
        q.moveTo((tx, top - 10)); q.qCurveTo((tx, top), (tx + 10, top)); q.lineTo((cx, top)); q.lineTo((cx, bot)); q.lineTo((tx + rd, bot)); q.lineTo((tx, bot)); q.closePath()
        ball = Path(); bq = ball.getPen(); _ep = ccx, ccy
        bq.moveTo((ccx + rd, ccy)); _arc(bq, ccx, ccy, rd, rd, 0.0, 2 * math.pi, n=8); bq.closePath()
        p = soften(OR(p, ball), 0, 11)
    else:
        q.moveTo((tx, top - 10)); q.qCurveTo((tx, top), (tx + 10, top)); q.lineTo((cx, top)); q.lineTo((cx, bot))
        q.lineTo((tx + 110, bot)); q.qCurveTo((tx + 42, bot), (tx + 36, yb + 14))
        q.qCurveTo((tx + 36, yb), (tx + 18, yb)); q.qCurveTo((tx, yb), (tx, yb + 14))
        q.closePath()
    right = tf(p, (-1, 0, 0, 1, 2 * cx, 0))
    if ear == "none": stem_top = rect(cx - stem / 2, 200, cx + stem / 2, top - 1)       # стойка до горизонтали (сопряжение уже в p)
    lower = shift(AND(I, rect(-50, -50, 400, 300)), cx - 113.0)                    # ножка ı: стойка 79–147 → вокруг оси cx
    stem_r = rect(cx - stem / 2, 200, cx + stem / 2, bot + 1) if ear != "none" else stem_top
    path = OR(p, right, lower, stem_r)
    dx = 20 - path.bounds[0]; path = shift(path, dx)
    info = {"overhang": overhang, "serif_depth": serif_depth, "bar_t": bar_t, "stem": stem, "ear": ear,
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def _u_taper(x0=312.0, x1=317.0):
    """Контур отсечения левого края правой стойки u (там, где в оригинале в стойку входит чаша): вертикаль x0 выше y=170, плавный S-изгиб (две квадратичные кривые,
    касательные вертикальные на концах и общая в середине, без изломов) к вертикали x1 ниже y=62. Прежний вариант был прямой косой от (x0,150) до (x1,62) с изломами на концах."""
    t = Path(); q = t.getPen()
    q.moveTo((x0, 400)); q.lineTo((x0, 170))
    q.qCurveTo((x0, 120), ((x0 + x1) / 2, 107.5)); q.qCurveTo((x1, 95), (x1, 62))
    q.lineTo((x1, -50)); q.lineTo((500, -50)); q.lineTo((500, 400)); q.closePath()
    return t


def _u_edge_fix():
    """Добавка к правой стойке u (координаты u, левый край стойки 312): делает левый край прямой вертикалью x=312 от y=175 до y=7 и ведёт нижнюю кривую ножки в ту же точку (326, -5),
    где у u продолжаются родные узлы (управляющая (317, -5), конец (326, -5)). Убирает сужение стойки 312 -> 317 книзу (правило автора проекта: левый край правой стойки прямой от начала до конца)."""
    fix = Path(); q = fix.getPen()
    q.moveTo((312, 175)); q.lineTo((312, 7)); q.qCurveTo((312, -5), (326, -5)); q.lineTo((326, 175)); q.closePath()
    return fix


def en_sign(ref, head="flag", bar_t=27.0, center=264.0, spacing=250.0):
    """Строчная н (карточка docs/glyphs/en.md): две стойки и перекладина по середине высоты x, H-образная (инструкция, раздел 7).
    Стойки это ı оригинала (головной флажок F1 и опорная засечка F2 уже в нём), без масштаба, на расстоянии spacing между левыми краями
    (у n: 74 и 324, spacing 250). head: "flag" (флажок ı на обеих стойках), "u" (плоская головка u слева от стойки) или "mix" (по просьбе автора проекта: слева ı с флажком и ножкой, справа стойка u с головкой и хвостом-выходом, как у латинской u).
    Перекладина: толщина bar_t (H: 30, e: 25), центр center = 51,8% высоты x (H: центр перекладины 373 при высоте 720, то есть выше середины)."""
    I, U = ref.glyph("dotlessi"), ref.glyph("u")
    U_STEM_LEFT = 312.0                                                 # левый край правой стойки u
    sx0, sx1 = 79.0 - 5.0, 79.0 - 5.0 + spacing                         # левые края стоек (ı: стойка 79–147, сдвиг −5: левая 74, как у n)
    def u_right(sx):
        # правая стойка u: головка слева от стойки, ножка с хвостом-выходом вправо (F3); ниже y=400 левый край прямой от 312 с плавным сужением до 317
        # к y=62 (как в ы, tools/sketch_yery.py): без наплыва там, где в стойку u вливается её чаша
        taper = _u_taper(U_STEM_LEFT)
        part = OR(AND(U, rect(250, 400, 500, 700)), AND(U, taper))
        part = OR(part, _u_edge_fix()); part.simplify()                      # левый край прямой вертикалью по всей длине, без сужения
        return shift(part, sx - U_STEM_LEFT)
    if head == "mix":
        stem = None
    elif head == "flag":
        stem = lambda sx: shift(I, sx - 79.0)
    else:
        def stem(sx):
            low = shift(AND(I, rect(-50, -50, 400, 400)), sx - 79.0)
            top = shift(AND(U, rect(-50, 400, 70, 700)), sx - 70.0)
            return OR(low, top, rect(sx, 395, sx + 68, 510))
    bar = rect(sx0 + 64.0, center - bar_t / 2, sx1 + 4.0, center + bar_t / 2)
    path = OR(shift(I, sx0 - 79.0), u_right(sx1), bar) if head == "mix" else OR(stem(sx0), stem(sx1), bar)
    info = {"head": head, "bar_t": bar_t, "center": center, "spacing": spacing,
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def yu_sign(ref, link=60.0, bar_t=25.0, center=254.0):
    """Строчная ю (карточка docs/glyphs/yu.md): стойка слева (ı), тонкая соединительная горизонталь и овал справа (о оригинала без масштаба).
    Овал равен о по высоте и овершуту (инструкция: ю); овал не касается стойки: между правым краем стойки и левым краем овала 'link',
    горизонталь входит в овал на 8, засечка ı до овала не доходит (проверяется)."""
    I, O = ref.glyph("dotlessi"), ref.glyph("o")
    stem_r = 147.0
    ox = stem_r + link - 23.0                                           # у о левый край 23
    oval = shift(O, ox)
    bar = rect(stem_r - 4, center - bar_t / 2, ox + 23.0 + 8.0, center + bar_t / 2)
    path = OR(I, bar, oval)
    foot_gap = AND(shift(I, 0), oval)                                    # проверка: стойка и овал не пересекаются
    touch = bool(list(foot_gap.contours))
    info = {"link": link, "bar_t": bar_t, "center": center, "stem_touches_oval": touch,
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def pe_flag(ref):
    """п.flag (карточка docs/glyphs/pe.md): латинская n оригинала, у которой нижний правый угол правой стойки заменён хвостом-выходом (флажком) от u.
    Нужна в позиции перед буквой, у которой в нижнем левом углу опорная засечка: хвост уходит вправо к ней и не сталкивается с её засечкой так, как плоская засечка n.
    Ниже y=150 стойка n (324–392) заменяется стойкой u (312–380, сдвиг +12) с ножкой и хвостом; выше без изменений."""
    N, U = ref.glyph("n"), ref.glyph("u")
    taper = poly((312, 400), (312, 150), (317, 62), (317, -50), (500, -50), (500, 400))
    tail = shift(AND(OR(AND(U, taper), _u_edge_fix()), rect(0, -50, 700, 150)), 12.0)
    top = SUB(N, rect(240, -50, 700, 150))
    return OR(top, tail)


def ka_sign(ref, short=False):
    """Строчная к (карточка docs/glyphs/ka.md) и контекстная форма ka-cy.short. Вторая версия (15.10.2026): к это сама латинская k оригинала,
    у которой убрана только верхняя часть стойки выше y=440 (выносной элемент) и вместо неё поставлен флажок ı (F1, сдвиг −5: стойка ı 74–142 как у k).
    Ножка, обе ветви и все их изгибы остаются контуром k без изменений (площадь изменений правее стойки равна нулю).
    short=True: головка верхней ветви укорочена: срез по x=392 (толщина головки там 32), оба правых угла кончика закруглены радиусом 10 (открытие shapely по кончику, внутреннее тело и изгибы выше и ниже зоны x 366–392 не тронуты)."""
    K, I = ref.glyph("k"), ref.glyph("dotlessi")
    head = shift(AND(I, rect(-50, 440, 400, 700)), -5.0)
    ka = OR(SUB(K, rect(-100, 440, 146, 800)), head); ka.simplify()
    if not short:
        return ka
    X = 392.0
    slab = AND(ka, rect(300, 430, X, 525))                                                     # кончик ветви, обрезанный по x=392 (левый край 300 глубоко внутри тела)
    rounded = soften(slab, 10.0, 0)                                                            # открытие радиусом 10: оба правых угла скруглены, заусенцев нет
    zone = rect(366, 430, 700, 560)
    out = OR(SUB(ka, zone), AND(rounded, zone)); out.simplify()
    return out


def ef_sign(ref):
    """Строчная ф (карточка docs/glyphs/ef.md): овал о оригинала без масштаба и сквозная стойка 68 по оси овала: сверху от l (выносной элемент 740 с флажком),
    снизу от p (выносной −205 с опорной засечкой). Стойка проходит через контрформу овала."""
    O, L, P = ref.glyph("o"), ref.glyph("l"), ref.glyph("p")
    cx = (23.0 + 383.0) / 2                                              # ось овала
    top = shift(AND(L, rect(-50, 380, 400, 800)), cx - 108.0)            # стойка l 74–142 (центр 108): верх с флажком
    bot = shift(AND(P, rect(-50, -300, 400, -20)), cx - 107.0)            # стойка p 73–141 (центр 107): низ с засечкой на −205
    stem = rect(cx - 34.0, -150.0, cx + 34.0, 600.0)
    return OR(O, top, bot, stem)


def zhe_sign(ref):
    """Заглавная Ж (карточка docs/glyphs/zhe.md): правая половина K оригинала и её зеркало относительно оси стойки (правило 16.2: Ж из двух половин K,
    верхняя ветвь тонкая, нижняя толстая, стойка толстая). Ось стойки K: x = 124,5 (стойка 89–160)."""
    K = ref.glyph("K"); ax = 124.5
    half = AND(K, rect(ax, -50, 700, 800))
    mirror = tf(half, (-1, 0, 0, 1, 2 * ax, 0))
    full = OR(half, mirror)
    return shift(full, 19.0 - full.bounds[0])                           # левое поле 19, как у K и H


def _ellipse(cx, cy, a, b, n=8):
    p = Path(); q = p.getPen()
    q.moveTo((cx + a, cy)); _arc(q, cx, cy, a, b, 0.0, 2 * math.pi, n=n); q.closePath()
    return p

def ef2_sign(ref, a_e=135.0, wall=72.0, hair=25.0, stem=68.0):
    """Строчная ф из двух эллипсов (карточка docs/glyphs/ef.md, правка автора проекта 15.10.2026: «должна состоять из двух эллипсов, а не из одного»):
    левый и правый овал-кольцо по обе стороны сквозной стойки, их внутренние боковые стенки скрыты в стойке, виден по глазу слева и справа.
    Овал: высота 516 / −9 (круглые строчные), боковая стенка wall (у о 76), верх и низ hair (волосная 25 у вершины о).
    Стойка: сверху от l (740, флажок F1), снизу от p (−205, опорная засечка F2); ширина stem = 68.
    a_e: внешняя полуось каждого эллипса; ширина буквы 2·(2·a_e) − stem."""
    L, P = ref.glyph("l"), ref.glyph("p")
    cy = (516.0 - 9.0) / 2; b = (516.0 + 9.0) / 2
    cx = 2 * a_e - stem / 2                                              # ось стойки: левый эллипс от x=0 до x=2a_e (край внутри стойки)
    cL, cR = a_e, 2 * a_e - stem + a_e
    def ring(c):
        return SUB(_ellipse(c, cy, a_e, b), _ellipse(c, cy, a_e - wall, b - hair))
    axis = (cL + cR) / 2
    top = shift(AND(L, rect(-50, 380, 400, 800)), axis - 108.0)
    bot = shift(AND(P, rect(-50, -300, 400, -20)), axis - 107.0)
    st = rect(axis - stem / 2, -150.0, axis + stem / 2, 600.0)
    path = OR(ring(cL), ring(cR), top, bot, st)
    dx = 23.0 - path.bounds[0]
    return shift(path, dx)


def _superellipse(cx, cy, a, b, n, steps=240):
    """Суперэллипс |x/a|^n + |y/b|^n = 1 (n=2 эллипс, больше 2 квадратнее) ломаной."""
    p = Path(); q = p.getPen()
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = cx + a * math.copysign(abs(c) ** (2 / n), c); y = cy + b * math.copysign(abs(s) ** (2 / n), s)
        (q.moveTo if i == 0 else q.lineTo)((x, y))
    q.closePath(); return p

def ef3_sign(ref, a_o=170.0, a_i=100.0, n_o=2.2, n_i=2.2, hair=25.0, stem=68.0, axis=257.0):
    """Строчная ф по образцу автора проекта (docs/img/author_ef_reference.svg, 15.10.2026), нарисована заново из параметров, не обводкой.
    По замерам образца: стойка 68 (x 223–291, ось 257), боковая стенка овалов 61, верх и низ колец 25, высота 516 / −9, ширина 514;
    овалы это не эллипсы, а квадратнее: верх плоский доходит до стойки, контрформа «D» прижата прямым краем к стойке.
    Построение: левый овал = левая половина большого суперэллипса (центр a_o, левый край 0), срезанная осью стойки; контрформа так же (левый край 61);
    правый овал зеркало левого. Параметры подобраны сеткой по минимуму площади расхождения овалов с образцом.
    Сверху стойка от l (740, флажок), снизу от p (−205, опорная засечка)."""
    L, P = ref.glyph("l"), ref.glyph("p")
    cy = (516.0 - 9.0) / 2; b = (516.0 + 9.0) / 2
    half = rect(-100, -100, axis, 700)
    outer = AND(_superellipse(a_o, cy, a_o, b, n_o), half)
    inner = AND(_superellipse(61.0 + a_i, cy, a_i, b - hair, n_i), half)
    ringL = SUB(outer, inner)
    ringR = tf(ringL, (-1, 0, 0, 1, 2 * axis, 0))
    top = shift(AND(L, rect(-50, 380, 400, 800)), axis - 108.0)
    bot = shift(AND(P, rect(-50, -300, 400, -20)), axis - 107.0)
    st = rect(axis - stem / 2, -150.0, axis + stem / 2, 600.0)
    path = OR(ringL, ringR, top, bot, st)
    return shift(path, 23.0 - path.bounds[0])


def pe_cap_sign(ref, bar_t=30.0, top=720.0):
    """Заглавная П (карточка docs/glyphs/pe_cap.md): H оригинала без перекладины, вместо неё верхняя горизонталь (инструкция, раздел 7: П-образная, углы с засечками).
    Стойки, опорные и головные засечки H остаются как есть (F2 внизу, головные засечки на обеих стойках), верхняя горизонталь толщиной bar_t лежит на плоской линии 720 заподлицо с засечками
    и входит в обе стойки. Ширина и поля H (546, 19/19)."""
    H = ref.glyph("H")
    stems = SUB(H, rect(160, 330, 386, 410))                              # убрать перекладину H (358–388)
    bar = rect(150.0, top - bar_t, 396.0, top)
    path = OR(stems, bar); path.simplify()
    info = {"bar_t": bar_t, "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def ii_cap_sign(ref, foot=False):
    """Заглавная И (карточка docs/glyphs/ii_cap.md): зеркало N оригинала относительно оси ширины (правило 16.2: роли штрихов от N, стойки тонкие 31, диагональ «/» толстая 76).
    foot=False: чистое зеркало (И1). foot=True (И2): остриё внизу слева срезано по базовой линии и под левую стойку поставлена опорная засечка F2, копия правой
    (инструкция: ножки на обеих стойках); у N на этом месте остриё ниже линии (−9)."""
    N = ref.glyph("N"); adv = ref.adv("N")
    M = tf(N, (-1, 0, 0, 1, adv, 0))
    if not foot:
        return M
    SL, SR = 103.5, 436.5                                              # оси левой (88–119) и правой (421–452) стоек
    serif = shift(AND(M, rect(330, -20, 540, 100)), SL - SR)           # опорная засечка правой стойки с подкосом, на левую стойку
    low = SUB(M, rect(0, -50, 300, 0))
    path = OR(low, serif); path.simplify()
    zone = rect(100, -5, 215, 70)                                       # шов диагонали с засечкой: вогнутый угол скруглён, остальной контур не тронут
    smooth = soften(path, 0, 10.0)
    out = OR(SUB(path, zone), AND(smooth, zone)); out.simplify()
    return out


def sha_cap_sign(ref, pitch=250.0, bar_t=30.0):
    """Заглавная Ш (карточка docs/glyphs/sha_cap.md): три стойки H оригинала (без перекладины, с головными и опорными засечками) и общая нижняя горизонталь bar_t заподлицо с опорными засечками (y 0).
    Левая и средняя стойки от левой половины H, правая от правой (засечки H 66/69 слева/справа). pitch это расстояние между левыми краями соседних стоек (у H между стойками 297).
    Просвет контрформ равный по построению; ширина = 527 + сдвиг правой стойки + поле 19."""
    H = ref.glyph("H")
    cut = rect(160, 330, 386, 410)
    Lh = SUB(AND(H, rect(-100, -50, 273, 800)), cut)                     # левая стойка H (89–160) с засечками
    Rh = SUB(AND(H, rect(273, -50, 700, 800)), cut)                      # правая стойка H (386–457) с засечками
    s2 = pitch; s3 = 2 * pitch - 297.0                                    # сдвиги: средняя на pitch, правая так, чтобы левый край стойки был на 89 + 2*pitch
    parts = [Lh, shift(Lh, s2), shift(Rh, s3)]
    bar = rect(89.0 + 30.0, 0.0, 386.0 + s3 + 41.0, bar_t)
    path = OR(*parts, bar); path.simplify()
    adv = 527.0 + s3 + 19.0
    # просвет между головными засечками соседних стоек (y 700): ближайшее расстояние между краями засечек
    top = AND(path, rect(-100, 700, 2000, 722)); xs = sorted((min(pt[0] for sg in c.segments for pt in sg[1]), max(pt[0] for sg in c.segments for pt in sg[1])) for c in top.contours)
    info = {"pitch": pitch, "bar_t": bar_t, "adv": adv, "top_pieces": [(round(a), round(b)) for a, b in xs],
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def yu_cap_sign(ref, link=55.0, bar_t=30.0, center=361.0):
    """Заглавная Ю (карточка docs/glyphs/yu_cap.md): стойка слева (левая половина H без перекладины, головные и опорные засечки H), тонкая горизонталь и овал справа (О оригинала без масштаба).
    Овал не касается стойки: расстояние от правого края стойки (160) до левого края овала (у О 40) равно link; горизонталь входит в овал на 8.
    Центр горизонтали по центру овала (как у строчной ю): (730 + (−9)) / 2 = 360,5. Поля: 19 слева (как у H), 40 справа (как у О)."""
    H, O = ref.glyph("H"), ref.glyph("O")
    stem = SUB(AND(H, rect(-100, -50, 273, 800)), rect(160, 330, 300, 410))
    ox = 160.0 + link - 40.0
    oval = shift(O, ox)
    bar = rect(160.0 - 4.0, center - bar_t / 2, ox + 40.0 + 8.0, center + bar_t / 2)
    path = OR(stem, bar, oval); path.simplify()
    # наименьший просвет между стойкой (с засечками) и овалом по горизонтальным срезам (шаг 5)
    def span(p, y):
        s = AND(p, rect(-100, y - 0.5, 2000, y + 0.5)); r = []
        for c in s.contours:
            xs = [pt[0] for sg in c.segments for pt in sg[1]]; r.append((min(xs), max(xs)))
        return sorted(r)
    gap = 1e9
    for y in range(0, 721, 5):
        a, b = span(stem, y), span(oval, y)
        if a and b: gap = min(gap, b[0][0] - a[-1][1])
    gap = round(gap, 1)
    adv = round(path.bounds[2] + 40.0)
    info = {"link": link, "bar_t": bar_t, "center": center, "min_gap_serif_oval": gap, "adv": adv,
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def ge_cap_sign(ref, shorten=0.0, rsb=19.0):
    """Заглавная Г (карточка docs/glyphs/ge_cap.md): стойка H (опорные засечки внизу), верх стойки и верхняя горизонталь с наклонным правым носиком от E оригинала.
    Горизонталь E почти симметрична относительно x=231 (низ 695): укорачивание вырезает отрезок длиной shorten между двумя точками с равным низом (разница < 0,1) и сдвигает носик влево, шов без ступеньки.
    Стойка 89–160, как у H и E. Левое поле 19 (H, E), правое rsb [РЕШЕНИЕ] 19, как у L."""
    H, E = ref.glyph("H"), ref.glyph("E")
    foot = AND(H, rect(-100, -50, 273, 330))                              # низ стойки H с опорными засечками
    mid = rect(89.0, 300.0, 160.0, 520.0)                                  # стойка между низом и верхом (H и E: 89–160)
    def under(x):                                                          # низ горизонтали E в точке x
        s_ = AND(E, rect(x - 0.05, 505, x + 0.05, 800)); return min(pt[1] for c in s_.contours for sg in c.segments for pt in sg[1])
    if shorten > 0:                                                        # шов в двух точках x_a и x_a + shorten с равным низом (разница < 0,1)
        x_a = min((abs(under(a / 2) - under(a / 2 + shorten)), a / 2) for a in range(400, 520))[1]
    else:
        x_a = 230.0
    top_l = AND(E, rect(-100, 505, x_a, 800))                              # верх стойки E (головная засечка) и левая часть горизонтали
    top_r = shift(AND(E, rect(x_a + shorten, 505, 700, 800)), -shorten)    # правая часть горизонтали с носиком
    path = OR(foot, mid, top_l, top_r); path.simplify()
    adv = round(path.bounds[2] + rsb)
    info = {"shorten": shorten, "rsb": rsb, "adv": adv, "contours": len(list(path.contours)),
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def el_std_sign(ref, apex="both", beta_deg=16.0, t_l=30.0, stem=71.0, top=720.0, soft_r=6.0):
    """Заглавная Л стандартной формы (карточка docs/glyphs/el.md, раздел «Стандартная форма»): плоская вершина вместо купола.
    Правая стойка вертикальная, 71 (H), левая нога тонкая диагональ t_l=30 под углом beta от вертикали (A, V: 14°), правый край ноги встаёт на левый край стойки на высоте 700.
    Верх на плоской линии 720 (круглых форм на 720 нет). Низ: вертикальные пеньки до y=60 и половины опорной засечки H (как в el_sign).
    apex: "both" головная засечка H с обеих сторон стойки, "left" только левый выступ (правая сторона стойки плоская), "none" без засечек (вершина: срез на 720).
    Внутренний угол между ногой и стойкой скругляется радиусом soft_r в зоне вершины контрформы (shapely, зона отдельной вставкой)."""
    H = ref.glyph("H"); ATT = 60.0
    tb, cb = math.tan(math.radians(beta_deg)), math.cos(math.radians(beta_deg)); wL = t_l / cb
    xr0 = 400.0; yj = 700.0
    xR = lambda y: xr0 - (yj - y) * tb
    xL = lambda y: xR(y) - wL
    leg = poly((xL(ATT), 0), (xL(ATT), ATT), (xL(top), top), (xR(top), top), (xR(ATT), ATT), (xR(ATT), 0))
    body = rect(xr0, 0, xr0 + stem, top)
    pieceL = AND(H, rect(-50, -50, 89, ATT)); pieceR = AND(H, rect(160, -50, 300, ATT))
    feet = [shift(pieceL, xL(ATT) - 89), shift(pieceR, xR(ATT) - 160), shift(pieceL, xr0 - 89), shift(pieceR, xr0 + stem - 160)]
    parts = [leg, body, *feet]
    dx = xr0 - 386.0                                                       # правая стойка H: 386–457, головные засечки 317–386 слева и 457–523 справа
    if apex in ("both", "left"): parts.append(shift(AND(H, rect(273, 640, 386, 740)), dx))
    if apex == "both": parts.append(shift(AND(H, rect(457, 640, 700, 740)), dx))
    path = OR(*parts); path.simplify()
    if soft_r:
        zone = rect(xr0 - 40.0, yj - 160.0, xr0 + 8.0, yj + 8.0)           # вершина контрформы между ногой и стойкой
        path = OR(SUB(path, zone), AND(soften(path, 0, soft_r), zone)); path.simplify()
    if apex == "none":                                                     # без засечек: острые верхние углы (ноги и стойки) скругляются радиусом 6, как кончики засечек
        for zx0, zx1 in ((xL(top) - 14.0, xL(top) + 40.0), (xr0 + stem - 40.0, xr0 + stem + 10.0)):
            zone = rect(zx0, top - 45.0, zx1, top + 8.0)
            path = OR(SUB(path, zone), AND(soften(path, 6.0, 0), zone))
        path.simplify()
    path = shift(path, 19.0 - path.bounds[0])                               # левое поле 19, как у H
    gap = (xr0 - 89 + 89) - (xR(ATT) + (229 - 160))                         # просвет между засечкой ноги и засечкой стойки у основания: левый край засечки стойки xr0 - 67
    gap = round((xr0 - (89 - 22)) - (xR(ATT) + (229 - 160)), 1)
    info = {"apex": apex, "beta_deg": beta_deg, "leg_width": round(wL, 1), "feet_gap": gap, "adv": round(path.bounds[2] + 19.0),
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def _rrect(x0, y0, x1, y1, r):
    """Прямоугольник со скруглёнными углами радиуса r (квадратичные кривые, без ломаных)."""
    p = Path(); q = p.getPen()
    q.moveTo((x0 + r, y0)); q.lineTo((x1 - r, y0)); q.qCurveTo((x1, y0), (x1, y0 + r)); q.lineTo((x1, y1 - r)); q.qCurveTo((x1, y1), (x1 - r, y1))
    q.lineTo((x0 + r, y1)); q.qCurveTo((x0, y1), (x0, y1 - r)); q.lineTo((x0, y0 + r)); q.qCurveTo((x0, y0), (x0 + r, y0)); q.closePath()
    return p


def obar_sign(ref, cap=True, bar_t=None):
    """Ө (cap=True) и ө (cap=False): О и о оригинала без масштаба и горизонтальная черта через овал (казахский, инструкция раздел 7: «О с горизонтальной чертой через овал»).
    Черта лежит по центру овала по высоте ((730 − 9)/2 = 360,5 у О; (516 − 9)/2 = 253,5 у о) и входит в обе стенки на 15, наружу не выходит.
    Толщина по умолчанию: волосная овала, 27 у О и 25 у о (`[ИЗМЕРЕНО]`: О 80 к 27, о 77 к 25; F7: перекладина e 25)."""
    O = ref.glyph("O" if cap else "o")
    t = bar_t if bar_t else (27.0 if cap else 25.0)
    c = 360.5 if cap else 253.5
    x0, x1 = (40 + 79 - 15, 500 - 79 + 15) if cap else (23 + 76 - 15, 383 - 76 + 15)         # внутренние края стенок ± 15
    path = OR(O, rect(x0, c - t / 2, x1, c + t / 2)); path.simplify()
    info = {"bar_t": t, "center": c, "adv": ref.adv("O" if cap else "o"), "contours": len(list(path.contours)),
            "xmin": round(path.bounds[0], 1), "xmax": round(path.bounds[2], 1), "ymin": round(path.bounds[1], 1), "ymax": round(path.bounds[3], 1)}
    return path, info


def ghe_stroke_sign(ref, half=90.0, bar_t=30.0, center=373.0):
    """Ғ: наша Г (G1, `ge_cap_sign`) и горизонтальная черта через стойку (казахский, инструкция раздел 7: «Г с поперечной чертой на стойке»).
    Центр стойки 124,5 (89–160); черта симметрична, половина длины half, концы скруглены (радиус 4, кривые). Высота центра 373, как у перекладины H (358–388, `[ИЗМЕРЕНО]`),
    толщина 30 (перекладина H). Левый конец не заходит левее левого поля Г (19)."""
    G, info = ge_cap_sign(ref)
    stem_c = 124.5
    bar = _rrect(stem_c - half, center - bar_t / 2, stem_c + half, center + bar_t / 2, 4.0)
    path = OR(G, bar); path.simplify()
    info = dict(info, half=half, bar_t=bar_t, center=center, contours=len(list(path.contours)),
                xmin=round(path.bounds[0], 1), xmax=round(path.bounds[2], 1), ymin=round(path.bounds[1], 1), ymax=round(path.bounds[3], 1))
    return path, info
