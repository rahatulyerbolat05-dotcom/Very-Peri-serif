#!/usr/bin/env python3
"""[РЕШЕНИЕ · 16.10.2026] Import user-confirmed ғ/Ң, preserving Beziers.

Run from repository root. Only the two known original SVG formats are accepted.
No simplification, automatic cleanup or inference of other glyph assignments.
"""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.pointPen import SegmentToPointPen, PointToSegmentPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ufoLib.glifLib import writeGlyphToString, readGlyphFromString
import pathops


def main():
    base = Path('data/user-2026-10-16-push')
    cfg = json.loads(Path('data/alphabet.json').read_text())
    cap = json.loads(Path('data/params.json').read_text())['regular']['vertical']['flat_cap']
    manifest = json.loads((base / 'manifest.json').read_text())
    imports = []
    for ch, name, filename, matrix, expected_transform, margin in (
        ('ғ', 'ghebar-cy', 'ghl2.svg', (1, 0, 0, 1, 0, 0), 'scale(1,-1)', 19),
        ('Ң', 'Endescender-cy', 'ң заглав.svg',
         (cap / 714, 0, 0, -cap / 714, 19, cap), None, 19),
    ):
        source = base / 'originals' / filename
        root = ET.fromstring(source.read_bytes())
        paths = root.findall('{http://www.w3.org/2000/svg}path')
        assert len(paths) == 1 and paths[0].get('transform') == expected_transform
        rec = RecordingPen()
        parse_path(paths[0].attrib['d'], TransformPen(rec, matrix))
        bounds = BoundsPen(None); rec.replay(bounds)
        advance = round(bounds.bounds[2] + margin)
        out = base / f'uni{ord(ch):04X}-primary.glif'
        note = ('[РЕШЕНИЕ] Авторский SVG; кривые сохранены без очистки. '
                + ('Координаты SVG уже в единицах шрифта; масштаб 1.' if ch == 'ғ' else
                   'Корпус SVG 714 равномерно приведён к высоте 720; поле слева 19.')
                + ' Интервалы предварительные; назначение буквы подтверждено пользователем.')
        obj = SimpleNamespace(width=advance, unicodes=[ord(ch)], note=note)
        out.write_text(writeGlyphToString(name, obj,
            lambda pp: rec.replay(SegmentToPointPen(pp)), formatVersion=2))
        back = RecordingPen(); metadata = SimpleNamespace()
        readGlyphFromString(out.read_text(), metadata, PointToSegmentPen(back))
        canonical = RecordingPen()
        rec.replay(SegmentToPointPen(PointToSegmentPen(canonical)))
        assert back.value == canonical.value and metadata.width == advance
        p = pathops.Path(); rec.replay(p.getPen())
        clean = pathops.simplify(p)
        difference = pathops.op(p, clean, pathops.PathOp.XOR)
        assert abs(difference.area) < 0.01
        item = {'character': ch, 'role': 'primary', 'path': str(out),
                'source_name': filename, 'transform': list(matrix),
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'glif_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
                'advance': advance, 'bounds': list(bounds.bounds),
                'status': 'user confirmed mapping; metrics provisional',
                'contours': len(list(p.contours)),
                'simplified_contours_for_diagnostic_only': len(list(clean.contours)),
                'note': note}
        cfg.setdefault('user', {})[ch] = {'selected': 'primary', 'origin': 'user',
            'variants': [item], 'provenance': 'авторский SVG пользователя',
            'status': 'user confirmed mapping; source only; not production font'}
        imports.append(item)
        print(ch, 'exact GLIF roundtrip OK; geometry OK;', item['bounds'])
    manifest['imports'] = imports
    context_path = Path('data/context/serif_bl.json')
    context = json.loads(context_path.read_text())
    from check_context_classes import load, test, test_top
    for item in imports:
        ch = item['character']; context['built_bases'][ch] = item['path']
        p = load(item['path'])
        rules = [(context, test(p)[0])]
        if ch.islower(): rules.append((context['ka_short'], test_top(p)[0]))
        for rule, included in rules:
            members = rule['declared_class']['lower' if ch.islower() else 'upper']
            outside = rule['expected_not_in_class']
            if ch in members: members.remove(ch)
            if ch in outside: outside.remove(ch)
            (members if included else outside).append(ch)
    event = '16.10.2026: авторские SVG ғ/Ң назначены пользователем; новые GLIF без очистки кривых, классы проверены по геометрии.'
    if event not in context['history']: context['history'].append(event)
    for target, data in ((base / 'manifest.json', manifest), (Path('data/alphabet.json'), cfg),
                         (context_path, context)):
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
