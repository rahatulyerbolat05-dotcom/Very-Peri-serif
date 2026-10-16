#!/usr/bin/env python3
"""[РЕШЕНИЕ] Ә ә Һ ұ — новые предложения Regular, без масштабирования доноров.

Запуск из корня: python -I tools/sketch_remaining_kz.py
Числа оригинала читаются из params.json; новые терминалы и интервалы —
композиционные решения, не измеренные факты готовой кириллицы.
"""
import hashlib
import json
import math
import sys
from pathlib import Path as FilePath
from types import SimpleNamespace

sys.path.insert(0, str(FilePath(__file__).resolve().parent))
from sketchlib import Ref, Path, AND, OR, rect, shift, write_svg
from glyphparts import _rrect
from fontTools.pens.pointPen import SegmentToPointPen, PointToSegmentPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ufoLib.glifLib import writeGlyphToString, readGlyphFromString
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageFont, ImageDraw

DATA = FilePath('data/kz-completion')
BUILD = FilePath('build/kz-completion')
NAMES = {'Ә': 'Schwa-cy', 'ә': 'schwa-cy', 'Һ': 'Shha-cy', 'ұ': 'ustraightstroke-cy'}
LABELS = {'Ә': 'Открытая верхняя дуга', 'ә': 'Открытая верхняя дуга',
          'Һ': 'Капительная стойка, плечо h', 'ұ': 'Основа ү, поперечная черта'}
NOTES = {
    'Ә': '[РЕШЕНИЕ] Силуэт: нижняя замкнутая чаша, правая дуга, открытый верх слева и горизонталь. Ход: вход слева сверху, верхняя дуга вправо, вниз и вокруг нижней чаши; горизонталь замыкает нижнюю контрформу. Новые кубические кривые по ширине, овершутам и контрасту O; не поворот e. Терминал нарисован заново. F7: капительная волосная O. Поля и апертура предварительные.',
    'ә': '[РЕШЕНИЕ] Силуэт: нижняя замкнутая чаша, правая дуга, открытый верх слева и горизонталь. Ход: вход слева сверху, дуга вправо вниз вокруг чаши, горизонталь в стенку. Новые кубические кривые по ширине, овершутам и контрасту o; не поворот e и не масштаб прописной. F7: волосная o/e. Поля и апертура предварительные.',
    'Һ': '[РЕШЕНИЕ] Силуэт: высокая левая стойка, плечо и правая стойка. Ход: левая стойка вниз, плечо вправо с выходом в правую стойку. Родное плечо h без масштаба; левая стойка I с капительными засечками, F2: ножки I/h. Отличается от строчной һ высотой и капительной головкой. Поля предварительные.',
    'ұ': '[РЕШЕНИЕ] Силуэт: выбранная для ү латинская y с поперечной чертой на нижнем выносе. Ход: левая ветвь вниз вправо, правая вниз влево в родной хвост; поперечина отдельным движением. F5: родная капля y, F8: родной нижний вынос y. Штрихи без масштаба. Следует существующему решению ү = y; положение черты и интервалы предварительные.',
}


def ellipse_point(cx, cy, rx, ry, angle):
    a = math.radians(angle)
    return cx + rx * math.cos(a), cy + ry * math.sin(a)


def arc(pen, cx, cy, rx, ry, start, stop):
    """Elliptical cubic segments; at most 45 degrees per segment."""
    count = math.ceil(abs(stop - start) / 45)
    for n in range(count):
        a = math.radians(start + (stop - start) * n / count)
        b = math.radians(start + (stop - start) * (n + 1) / count)
        k = 4 / 3 * math.tan((b - a) / 4)
        p0 = (cx + rx * math.cos(a), cy + ry * math.sin(a))
        p3 = (cx + rx * math.cos(b), cy + ry * math.sin(b))
        pen.curveTo((p0[0] - k * rx * math.sin(a), p0[1] + k * ry * math.cos(a)),
                    (p3[0] + k * rx * math.sin(b), p3[1] - k * ry * math.cos(b)), p3)


def schwa(ref, params, cap):
    donor = 'O' if cap else 'o'
    xmin, bottom, xmax, top = ref.glyph(donor).bounds
    cx, cy = (xmin + xmax) / 2, (bottom + top) / 2
    rx, ry = (xmax - xmin) / 2, (top - bottom) / 2
    # [ИЗМЕРЕНО] Толщины родных округлых; середина полосы — центр овала.
    m = params['regular']
    side = m['stress_axis']['O']['thickness_by_angle']['0'] if cap else m['stems_hairlines']['o_side']
    hair = m['stress_axis'][donor]['thin']
    irx, iry = rx - side, ry - hair
    high, low = cy + hair / 2, cy - hair / 2
    angle = 145  # [РЕШЕНИЕ] Апертура; новый округлый срез верхнего входа.
    outer_tip = ellipse_point(cx, cy, rx, ry, angle)
    inner_tip = ellipse_point(cx, cy, irx, iry, angle)
    p = Path(); q = p.getPen()
    q.moveTo((xmin, cy)); arc(q, cx, cy, rx, ry, 180, 360 + angle)
    midx = (outer_tip[0] + inner_tip[0]) / 2
    midy = (outer_tip[1] + inner_tip[1]) / 2
    q.qCurveTo((midx - hair / 2, midy - hair), inner_tip)
    inner_angle = math.degrees(math.asin((high - cy) / iry))
    arc(q, cx, cy, irx, iry, angle, inner_angle)
    q.lineTo((xmin, high)); q.closePath()
    # Нижняя контрформа с противоположным обходом, без наложенных деталей.
    a = math.degrees(math.asin((low - cy) / iry))
    q.moveTo(ellipse_point(cx, cy, irx, iry, a))
    arc(q, cx, cy, irx, iry, a, -180 - a)
    q.closePath()
    return p, ref.adv(donor)


def outlines(ref, params):
    # [ИЗМЕРЕНО] h: левая стойка 74..142; I: 89..160; плечо h до516.
    shoulder = AND(ref.glyph('h'), rect(142, -1000, 1000, 516))
    shha = shift(OR(shift(ref.glyph('I'), -15), shoulder), 11)
    # [РЕШЕНИЕ] Черта ниже базовой линии; чертёж y и капля сохранены.
    cy = params['regular']['vertical']['descender_p'] / 3
    t = params['regular']['stems_hairlines']['e_crossbar']
    bar = _rrect(110, cy - t / 2, 260, cy + t / 2, 4)
    straight = OR(ref.glyph('y'), bar)
    return {'Ә': schwa(ref, params, True), 'ә': schwa(ref, params, False),
            'Һ': (shha, round(shha.bounds[2] + 15)), 'ұ': (straight, ref.adv('y'))}


def review(cfg):
    from alphabet_sheet import canvas, text, glyph, load_glif, source_items
    import matplotlib.pyplot as plt
    fig, ax = canvas(1800, 1560)
    text(ax, 60, 35, 'Ә ә Һ ұ · Very Peri Serif · предложения Regular', 32)
    for x, ch in zip((250, 680, 1110, 1540), NAMES):
        glyph(ax, cfg['codex'][ch]['variants'][0]['path'], x, 550, .55)
    # Вся строка состоит из текущих GLIF карты, без подстановки системного шрифта.
    for j, line in enumerate(('ӘЛЕМ  ӘДЕМІ  ӘУЕ', 'әлем  әдемі  әуе',
                              'ҺАҺ  ҺОҺ  ҺӘҺ', 'ұлт  ұлы  құс  ұш')):
        x, baseline, scale = 60, 810 + j * 180, .15
        for ch in line:
            if ch == ' ':
                x += 45
                continue
            filename = source_items(ch, cfg)[0]['path']; outline = load_glif(filename)
            xmin, _, xmax, _ = outline.bounds
            glyph(ax, filename, x + (xmin + xmax) * scale / 2, baseline, scale)
            x += outline.advance * scale
    text(ax, 60, 1490, 'Новые формы на рассмотрении; интервалы предварительные.', 24)
    fig.savefig('docs/img/kz_completion.svg')
    fig.savefig(BUILD / 'comparison.png', dpi=100)
    plt.close(fig)


def check_ttf(ref, drawings):
    f = TTFont(ref.ttf); order = list(f.getGlyphOrder())
    for ch, (path, advance) in drawings.items():
        p = TTGlyphPen(None); path.draw(Cu2QuPen(p, .5, reverse_direction=False))
        name = NAMES[ch] + '.study'; g = p.glyph(); f['glyf'][name] = g
        order.append(name); g.recalcBounds(f['glyf']); f['hmtx'][name] = (advance, g.xMin)
        for table in f['cmap'].tables:
            if table.isUnicode(): table.cmap[ord(ch)] = name
    f.setGlyphOrder(order); f['maxp'].numGlyphs = len(order)
    for nid, value in ((1, 'Very Peri Serif Kazakh Study'), (2, 'Regular'),
                       (4, 'Very Peri Serif Kazakh Study Regular'), (6, 'VeryPeriSerif-KazakhStudy-Regular')):
        for record in f['name'].names:
            if record.nameID == nid: record.string = value.encode(record.getEncoding())
    target = BUILD / 'VeryPeriSerif-KazakhStudy.ttf'; f.save(target)
    restored = TTFont(target, checkChecksums=2); restored.ensureDecompiled()
    gs = restored.getGlyphSet()
    for ch, (path, advance) in drawings.items():
        name = restored.getBestCmap()[ord(ch)]
        assert name == NAMES[ch] + '.study'
        assert restored['hmtx'][name][0] == advance
        assert restored['glyf'][name].numberOfContours == len(list(path.contours))
        bounds = BoundsPen(gs); gs[name].draw(bounds)
        assert all(abs(a - b) < 1 for a, b in zip(bounds.bounds, path.bounds))
    original = TTFont(ref.ttf)
    for name in original.getGlyphOrder():
        assert restored['glyf'][name].compile(restored['glyf']) == original['glyf'][name].compile(original['glyf'])
    im = Image.new('RGB', (1000, 500), 'white'); d = ImageDraw.Draw(im)
    for j, size in enumerate((100, 24, 12)):
        font = ImageFont.truetype(str(target), size)
        d.text((30, 30 + j * 150), 'Әә Һ ұ Әә Һ ұ', font=font, fill='black')
    im.save(BUILD / 'raster-check.png')


def main():
    DATA.mkdir(parents=True, exist_ok=True); BUILD.mkdir(parents=True, exist_ok=True)
    ref = Ref(); params = json.loads(FilePath('data/params.json').read_text())
    cfg = json.loads(FilePath('data/alphabet.json').read_text())
    context = json.loads(FilePath('data/context/serif_bl.json').read_text())
    drawings = outlines(ref, params); manifest = {}
    from check_context_classes import test, test_top
    for ch, (p, advance) in drawings.items():
        p.simplify()
        path = DATA / f'uni{ord(ch):04X}-01.glif'
        g = SimpleNamespace(width=advance, unicodes=[ord(ch)], note=NOTES[ch])
        path.write_text(writeGlyphToString(NAMES[ch], g,
            lambda pp: p.draw(SegmentToPointPen(pp)), formatVersion=2))
        write_svg(p, advance, str(path.with_suffix('.svg')))
        back = Path(); meta = SimpleNamespace()
        readGlyphFromString(path.read_text(), meta, PointToSegmentPen(back.getPen()))
        import pathops
        assert abs(pathops.op(p, back, pathops.PathOp.XOR).area) < .01
        assert meta.width == advance and back.bounds == p.bounds
        item = {'path': str(path), 'label': LABELS[ch], 'variant': '01',
                'status': 'proposal', 'advance': advance, 'bounds': list(p.bounds),
                'glif_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest[ch] = dict(item, note=NOTES[ch], contours=len(list(p.contours)))
        cfg['codex'][ch] = {'selected': cfg['codex'].get(ch, {}).get('selected'),
            'shared_with_claude': False, 'conflict': False, 'variants': [item],
            'provenance': 'Codex; Instrument Serif metrics and unscaled native donors'}
        context['built_bases'][ch] = str(path)
        rules = [(context, test(p)[0])]
        if ch.islower(): rules.append((context['ka_short'], test_top(p)[0]))
        for rule, inside in rules:
            members = rule['declared_class']['upper' if ch.isupper() else 'lower']
            outside = rule['expected_not_in_class']
            if ch in members: members.remove(ch)
            if ch in outside: outside.remove(ch)
            (members if inside else outside).append(ch)
    event = '16.10.2026: построены предложения Ә ә Һ ұ; классы пересчитаны по геометрии; утверждение форм остаётся открытым.'
    if event not in context['history']: context['history'].append(event)
    for filename, data in ((DATA / 'manifest.json', manifest),
                           (FilePath('data/alphabet.json'), cfg),
                           (FilePath('data/context/serif_bl.json'), context)):
        filename.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    check_ttf(ref, drawings); review(cfg)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
