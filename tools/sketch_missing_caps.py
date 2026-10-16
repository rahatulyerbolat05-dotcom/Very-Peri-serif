#!/usr/bin/env python3
"""[РЕШЕНИЕ] Ч Ъ Ы Э: воспроизводимые предложения капителей, не финальный релиз.

Запуск из корня: python -I tools/sketch_missing_caps.py
Латинские доноры используются без масштабирования. Числа новых сочленений
и интервалов — решения эскиза, а не измеренные свойства оригинала.
"""
import hashlib
import json
import sys
from pathlib import Path as FilePath
from types import SimpleNamespace

sys.path.insert(0, str(FilePath(__file__).resolve().parent))
from sketchlib import Ref, Path, AND, SUB, OR, rect, shift, write_svg
from fontTools.pens.pointPen import PointToSegmentPen, SegmentToPointPen
from fontTools.ufoLib.glifLib import readGlyphFromString, writeGlyphToString
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = FilePath(__file__).resolve().parents[1]
DATA = ROOT / 'data/capitals-che-hard-yeru-e'
BUILD = ROOT / 'build/capitals-che-hard-yeru-e'
NAMES = {'Ч': 'Che-cy', 'Ъ': 'Hardsign-cy', 'Ы': 'Yeru-cy', 'Э': 'Ereversed-cy'}
LABELS = {'Ч': 'Поднятая чаша U', 'Ъ': 'Чаша Ь, плечо T',
          'Ы': 'Чаша Ь, отдельная I', 'Э': 'Открытые окончания, перекладина H'}
NOTES = {
    'Ч': '[РЕШЕНИЕ] Силуэт: верхняя левая чаша и правая стойка. Ход: левая ветвь вниз, дуга вправо, правая стойка вниз. F2: ножка правой I; верхние засечки I; чаша U перенесена без масштаба. Уровень чаши — нижняя грань перекладины H. Интервалы предварительные.',
    'Ъ': '[РЕШЕНИЕ] Силуэт: левое верхнее плечо и Ь. Ход: плечо вправо, стойка вниз, нижняя чаша вправо. F2: ножка Ь из B; верхнее плечо T без масштаба. Родная левая головная засечка Ь заменена плечом. Интервалы предварительные.',
    'Ы': '[РЕШЕНИЕ] Силуэт: Ь и отдельная правая стойка. Ход: стойка и нижняя чаша, затем правая стойка вниз. F2: ножки B/I. Оба компонента без масштаба. Зазор между чашей и левой засечкой I — две толщины кончика ножки из params.json; это решение эскиза. Интервалы предварительные.',
    'Э': '[РЕШЕНИЕ] Силуэт: правая открытая дуга и средняя горизонталь. Ход: вход слева сверху, дуга вправо вниз, открытый нижний выход слева; горизонталь в чашу. Дуги C задают пропорции и вертикальную ось; оба окончания построены заново. F7: тонкая горизонталь по капительной H (не строчной e). Интервалы предварительные.',
}


def load_glif(filename):
    p = Path()
    g = SimpleNamespace()
    readGlyphFromString(FilePath(filename).read_text(), g, PointToSegmentPen(p.getPen()))
    return p, g.width


def make_e(ref, params):
    # [ИЗМЕРЕНО] Координаты дуг C оригинального TTF; без масштабирования.
    # [РЕШЕНИЕ] Новые открытые терминалы, без зеркальной головной скобки C.
    p = Path(); q = p.getPen()
    q.moveTo((194, -9))
    q.qCurveTo((268, -9), (379, 83), (440, 250), (440, 364))
    q.qCurveTo((440, 474), (373, 639), (260, 730), (191, 730))
    q.qCurveTo((145, 730), (80, 713), (57, 692))
    q.qCurveTo((49, 685), (52, 671))
    q.lineTo((65, 606))
    q.qCurveTo((68, 591), (80, 594))
    q.qCurveTo((90, 597), (86, 611))
    q.qCurveTo((81, 636), (131, 701), (199, 701))
    q.qCurveTo((269, 701), (362, 528), (362, 364))
    q.qCurveTo((362, 252), (315, 98), (240, 20), (198, 20))
    q.qCurveTo((145, 20), (88, 76), (76, 143))
    q.qCurveTo((73, 158), (61, 155))
    q.qCurveTo((49, 152), (53, 137))
    q.lineTo((68, 51))
    q.qCurveTo((70, 36), (84, 25))
    q.qCurveTo((129, -9), (194, -9))
    q.closePath()
    m = params['regular']['stems_hairlines']
    cy, thickness = m['H_crossbar_center'], m['H_crossbar']
    low, high = cy - thickness / 2, cy + thickness / 2
    # [РЕШЕНИЕ] Скруглённое открытое начало; подкосы по H у правой стенки.
    bar = Path(); b = bar.getPen()
    b.moveTo((115, low)); b.lineTo((348, low))
    b.qCurveTo((362, low), (362, low - 14))
    b.lineTo((400, low - 14)); b.lineTo((400, high + 14))
    b.lineTo((362, high + 14)); b.qCurveTo((362, high), (348, high))
    b.lineTo((115, high)); b.qCurveTo((100, high), (100, cy))
    b.qCurveTo((100, low), (115, low)); b.closePath()
    return OR(p, bar), ref.adv('C')


def outlines(ref, params):
    m = params['regular']['stems_hairlines']
    top = params['regular']['vertical']['flat_cap']
    bottom = m['H_crossbar_center'] - m['H_crossbar'] / 2
    u, i = ref.glyph('U'), ref.glyph('I')
    # [ИЗМЕРЕНО] U: стойки x92..163 / x422..454; I: x89..160.
    # [РЕШЕНИЕ] Круглое дно U поднято к низу перекладины H.
    rise = bottom - u.bounds[1]
    bowl = AND(shift(u, 0, rise), rect(-1000, -1000, 2000, top))
    head = AND(shift(i, 3), rect(-1000, 192 + rise, 2000, top))
    right = shift(i, 422 - 89)
    che = OR(bowl, head, right)
    soft, soft_adv = load_glif(ROOT / 'data/codex/uni042C-01.glif')
    # [РЕШЕНИЕ] Плечо T целиком по высоте и изгибам; сдвиг совмещает стойки.
    tdx = params['spacing_regular']['H']['lsb'] - 10
    dx = 195 + tdx - 89
    body = shift(SUB(soft, rect(-1000, 654, 89, 1000)), dx)
    arm = AND(shift(ref.glyph('T'), tdx), rect(-1000, 514, 195 + tdx, 1000))
    hard = OR(body, arm)
    gap = 2 * params['regular']['serifs']['foot_thickness_tip_x20']
    idx = soft.bounds[2] + gap - i.bounds[0]
    yeru = OR(soft, shift(i, idx))
    return {'Ч': (che, round(che.bounds[2] + 19)),
            'Ъ': (hard, round(soft_adv + dx)),
            'Ы': (yeru, round(ref.adv('I') + idx)), 'Э': make_e(ref, params)}


def proof_font(cfg):
    from alphabet_sheet import source_items
    f = TTFont('reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf')
    order = list(f.getGlyphOrder())
    for ch in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ':
        item = source_items(ch, cfg)[0]
        path, advance = load_glif(ROOT / item['path'])
        pen = TTGlyphPen(None)
        path.draw(Cu2QuPen(pen, 0.5, reverse_direction=False))
        name = f'uni{ord(ch):04X}.review'
        g = pen.glyph(); f['glyf'][name] = g; order.append(name)
        g.recalcBounds(f['glyf'])
        f['hmtx'][name] = (round(advance), g.xMin)
        for table in f['cmap'].tables:
            if table.isUnicode(): table.cmap[ord(ch)] = name
    f.setGlyphOrder(order); f['maxp'].numGlyphs = len(order)
    for nid, value in ((1, 'Very Peri Serif Capitals Study'), (2, 'Regular'),
                       (4, 'Very Peri Serif Capitals Study Regular'),
                       (6, 'VeryPeriSerif-CapitalsStudy-Regular')):
        for record in f['name'].names:
            if record.nameID == nid:
                record.string = value.encode(record.getEncoding())
    target = BUILD / 'VeryPeriSerif-CapitalsStudy.ttf'
    f.save(target)
    return target


def render_proof(ttf):
    im = Image.new('RGB', (1800, 1750), '#f5f2ec'); d = ImageDraw.Draw(im)
    label = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 27)
    d.text((60, 35), 'Ч  Ъ  Ы  Э  ·  Very Peri Serif  ·  предложения / Regular', font=label, fill='#272333')
    f = ImageFont.truetype(str(ttf), 440)
    for x, ch in zip((65, 480, 910, 1390), NAMES):
        d.line((x, 485, x + 350, 485), fill='#ddaaaa')
        d.line((x, 168, x + 350, 168), fill='#aabbdd')
        d.text((x, 485), ch, font=f, fill='#272333', anchor='ls')
    samples = ['НОЧЬ  ЧАША  ЧЕТЫРЕ', 'ОБЪЕКТ  ПОДЪЁМ  СЪЕЗД', 'БЫЛЬ  ВЫХОД  МЫСЛЬ', 'ЭТО  ЭХО  ПОЭТ  ЭКРАН']
    for j, line in enumerate(samples):
        d.text((60, 590 + j * 145), line, font=ImageFont.truetype(str(ttf), 125), fill='#272333')
    for y, size in ((1220, 100), (1380, 24), (1460, 12)):
        d.text((60, y - 30), f'{size} px', font=label, fill='#777777')
        d.text((220, y), 'НЧОЧН  НЪОЪН  НЫОЫН  НЭОЭН', font=ImageFont.truetype(str(ttf), size), fill='#272333')
    d.rectangle((0, 1540, 1800, 1750), fill='#272333')
    d.text((60, 1580), 'ЧАША  ОБЪЕКТ  МЫСЛЬ  ЭХО', font=ImageFont.truetype(str(ttf), 100), fill='#f5f2ec')
    im.save(BUILD / 'comparison.png')


def vector_proof(cfg):
    from alphabet_sheet import canvas, text, glyph, load_glif, source_items
    import matplotlib.pyplot as plt
    fig, ax = canvas(1800, 1350)
    text(ax, 60, 35, 'Ч Ъ Ы Э · Very Peri Serif · предложения / Regular', 30)
    for x, ch in zip((210, 650, 1080, 1510), NAMES):
        glyph(ax, cfg['codex'][ch]['variants'][0]['path'], x, 510, .5)
    for j, line in enumerate(('НОЧЬ  ЧАША  ЧЕТЫРЕ', 'ОБЪЕКТ  ПОДЪЁМ  СЪЕЗД',
                              'БЫЛЬ  ВЫХОД  МЫСЛЬ', 'ЭТО  ЭХО  ПОЭТ  ЭКРАН')):
        x, baseline, scale = 60, 710 + j * 155, .14
        for ch in line:
            if ch == ' ':
                x += 35
                continue
            filename = source_items(ch, cfg)[0]['path']
            outline = load_glif(filename)
            xmin, _, xmax, _ = outline.bounds
            glyph(ax, filename, x + (xmin + xmax) * scale / 2, baseline, scale)
            x += outline.advance * scale
    text(ax, 60, 1270, 'Интервалы предварительные; контуры на рассмотрении. Родная латиница не изменена.', 22)
    fig.savefig(ROOT / 'docs/img/capitals_che_hard_yeru_e.svg')
    plt.close(fig)


def main():
    DATA.mkdir(parents=True, exist_ok=True); BUILD.mkdir(parents=True, exist_ok=True)
    ref = Ref(); params = json.loads((ROOT / 'data/params.json').read_text())
    cfg = json.loads((ROOT / 'data/alphabet.json').read_text())
    context = json.loads((ROOT / 'data/context/serif_bl.json').read_text())
    manifest = {}
    for ch, (p, advance) in outlines(ref, params).items():
        p.simplify()
        filename = DATA / f'uni{ord(ch):04X}-01.glif'
        g = SimpleNamespace(width=advance, unicodes=[ord(ch)], note=NOTES[ch])
        xml = writeGlyphToString(NAMES[ch], g, lambda pp: p.draw(SegmentToPointPen(pp)), formatVersion=2)
        filename.write_text(xml, encoding='utf-8')
        write_svg(p, advance, str(filename.with_suffix('.svg')))
        relative = str(filename.relative_to(ROOT))
        record = {'path': relative, 'label': LABELS[ch], 'variant': '01',
                  'status': 'proposal', 'advance': advance, 'bounds': list(p.bounds),
                  'glif_sha256': hashlib.sha256(filename.read_bytes()).hexdigest()}
        previous = cfg['codex'].get(ch, {})
        cfg['codex'][ch] = {'selected': previous.get('selected'), 'shared_with_claude': False, 'conflict': False,
                            'variants': [record], 'provenance': 'Codex; native Instrument Serif donors, no scaling'}
        context['built_bases'][ch] = relative
        manifest[ch] = dict(record, note=NOTES[ch], contours=len(list(p.contours)))
        # Roundtrip validates actual saved GLIF, not just in-memory geometry.
        loaded, width = load_glif(filename)
        assert width == advance and loaded.bounds == p.bounds
        assert not list(SUB(loaded, p).contours) and not list(SUB(p, loaded).contours)
    # [ИЗМЕРЕНО] Новые контуры проверяются тем же геометрическим критерием.
    from check_context_classes import test
    for ch in NAMES:
        p, _ = load_glif(ROOT / context['built_bases'][ch])
        included, _ = test(p)
        upper = context['declared_class']['upper']
        outside = context['expected_not_in_class']
        if ch in upper: upper.remove(ch)
        if ch in outside: outside.remove(ch)
        (upper if included else outside).append(ch)
    event = '16.10.2026: добавлены предложения Ч Ъ Ы Э; @serif_bl пересчитан по новым контурам, утверждение форм пользователем остаётся открытым.'
    if event not in context['history']: context['history'].append(event)
    for filename, obj in ((ROOT / 'data/alphabet.json', cfg),
                          (ROOT / 'data/context/serif_bl.json', context), (DATA / 'manifest.json', manifest)):
        filename.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    render_proof(proof_font(cfg))
    vector_proof(cfg)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
