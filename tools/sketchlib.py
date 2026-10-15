"""Общие функции для эскизов глифов: сборка из деталей оригинала (булевы операции над контурами),
вставка эскиза в копию шрифта, выгрузка в SVG и GLIF, отрисовка сравнительной картинки.
Эскиз это не финальный контур: подкосы и сопряжения не отрисованы."""
import os
import pathops
from pathops import Path, PathOp
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.ufoLib.glifLib import writeGlyphToString
from PIL import Image, ImageDraw, ImageFont

LABEL_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LABEL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

class Ref:
    def __init__(self, ref_dir="reference/instrument-serif"):
        self.ttf = f"{ref_dir}/fonts/ttf/InstrumentSerif-Regular.ttf"
        self.font = TTFont(self.ttf); self.gs = self.font.getGlyphSet()
    def glyph(self, name, dx=0, dy=0):
        p = Path(); self.gs[name].draw(TransformPen(p.getPen(glyphSet=self.gs), (1, 0, 0, 1, dx, dy))); return p
    def adv(self, name): return self.font["hmtx"][name][0]

def rect(x0, y0, x1, y1):
    p = Path(); q = p.getPen(); q.moveTo((x0, y0)); q.lineTo((x1, y0)); q.lineTo((x1, y1)); q.lineTo((x0, y1)); q.closePath(); return p
def poly(*pts):
    p = Path(); q = p.getPen(); q.moveTo(pts[0])
    for pt in pts[1:]: q.lineTo(pt)
    q.closePath(); return p
def AND(a, b): return pathops.op(a, b, PathOp.INTERSECTION)
def SUB(a, b): return pathops.op(a, b, PathOp.DIFFERENCE)
def OR(*ps):
    r = ps[0]
    for p in ps[1:]: r = pathops.op(r, p, PathOp.UNION)
    return r
def soften(path, r_convex, r_concave, res=24):
    """Смягчение контура (shapely): внутренние углы скругляются радиусом r_concave (закрытие), внешние r_convex (раскрытие).
    Детали уже r_convex*2 пропадают, поэтому r_convex держать меньше половины самой тонкой детали (кончики засечек 20+).
    Контур становится ломаной (шаг мелкий): для эскиза и сравнения, не для финала."""
    from fontTools.pens.basePen import BasePen
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    from shapely.ops import unary_union
    class Flat(BasePen):
        def __init__(self): super().__init__(None); self.rings, self.cur = [], []
        def _moveTo(self, pt): self.cur = [pt]
        def _lineTo(self, pt): self.cur.append(pt)
        def _curveToOne(self, a, b, c):
            x0, y0 = self._getCurrentPoint()
            for i in range(1, 13):
                t = i / 12; u = 1 - t
                self.cur.append((u**3*x0 + 3*u*u*t*a[0] + 3*u*t*t*b[0] + t**3*c[0], u**3*y0 + 3*u*u*t*a[1] + 3*u*t*t*b[1] + t**3*c[1]))
        def _qCurveToOne(self, a, b):
            x0, y0 = self._getCurrentPoint()
            for i in range(1, 13):
                t = i / 12; u = 1 - t
                self.cur.append((u*u*x0 + 2*u*t*a[0] + t*t*b[0], u*u*y0 + 2*u*t*a[1] + t*t*b[1]))
        def _closePath(self): self.rings.append(self.cur); self.cur = []
        _endPath = _closePath
    fp = Flat(); path.draw(fp)
    polys = [Polygon(r).buffer(0) for r in fp.rings if len(r) > 2]
    geom = unary_union(polys)
    if r_concave: geom = geom.buffer(r_concave, res).buffer(-r_concave, res)
    if r_convex: geom = geom.buffer(-r_convex, res).buffer(r_convex, res)
    geom = geom.simplify(0.15)
    out = Path(); pen = out.getPen()
    for g in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        g = orient(g, sign=-1.0)
        for ring in [g.exterior, *g.interiors]:
            pts = list(ring.coords)[:-1]; pen.moveTo(pts[0])
            for q in pts[1:]: pen.lineTo(q)
            pen.closePath()
    return out

def tf(p, m):
    q = Path(); p.draw(TransformPen(q.getPen(), m)); return q
def shift(p, dx, dy=0): return tf(p, (1, 0, 0, 1, dx, dy))

def install(ref_ttf, path, adv, codepoint, out_ttf, name="uni%04X"):
    """Копия эталона, в которой кодовая точка codepoint указывает на эскиз."""
    path = path; path.simplify()
    pen = TTGlyphPen(None); path.draw(pen); g = pen.glyph()
    f = TTFont(ref_ttf); gname = name % codepoint
    order = f.getGlyphOrder() + [gname]
    f.setGlyphOrder(order); f["glyf"].glyphOrder = order; f["glyf"][gname] = g; g.recalcBounds(f["glyf"])
    f["hmtx"][gname] = (adv, g.xMin)
    for t in f["cmap"].tables:
        if t.isUnicode(): t.cmap[codepoint] = gname
    f["maxp"].numGlyphs = len(order); f.save(out_ttf)
    return {"adv": adv, "xmin": g.xMin, "xmax": g.xMax, "ymin": g.yMin, "ymax": g.yMax}

def write_svg(path, adv, out):
    pen = SVGPathPen(None); path.draw(pen)
    open(out, "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -780 {adv + 40} 1060">'
        f'<path transform="scale(1,-1)" d="{pen.getCommands()}"/></svg>\n')

def write_glif(path, glyph_name, adv, codepoint, out):
    class G: pass
    g = G(); g.width = adv; g.unicodes = [codepoint]
    xml = writeGlyphToString(glyph_name, g, lambda pp: path.draw(SegmentToPointPen(pp)), formatVersion=2)
    open(out, "w", encoding="utf-8").write(xml)

def render(items, char, samples, out_png, col_w=760, size=900, base=640, guides=(0, 510)):
    """items: [(подпись, ttf, ширина)]. Крупный глиф с направляющими и строки-образцы."""
    lab = ImageFont.truetype(LABEL_BOLD, 38); sub = ImageFont.truetype(LABEL, 26)
    H = base + 90 + len(samples) * 170 + 60; k = size / 1000
    im = Image.new("RGB", (col_w * len(items), H), "white"); d = ImageDraw.Draw(im)
    for i, (label, ttf, adv) in enumerate(items):
        ox = i * col_w
        if i: d.line([(ox, 40), (ox, H - 40)], fill="#ddd", width=2)
        f = ImageFont.truetype(ttf, size)
        for val, col in [(guides[0], "#e55"), (guides[1], "#59f")]:
            y = base - val * k; d.line([(ox + 20, y), (ox + col_w - 20, y)], fill=col, width=2)
        d.text((ox + 40, base), char, font=f, fill="black", anchor="ls")
        d.text((ox + 30, 40), label, font=lab, fill="black"); d.text((ox + 30, 92), f"ширина {adv}", font=sub, fill="#777")
        f2 = ImageFont.truetype(ttf, 130)
        for j, line in enumerate(samples): d.text((ox + 30, base + 100 + j * 170), line, font=f2, fill="black")
    im.save(out_png)
