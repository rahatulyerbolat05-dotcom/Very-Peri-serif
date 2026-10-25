#!/usr/bin/env python3
"""Independent first repair-batch acceptance, including serialized CFF geometry.

The baseline is published 1.110. The three tail glyphs retain this repair;
explicit later outline batches have their own strict whole-font acceptance.
All metrics, marks, features and native outlines remain protected.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pathops
from fontTools.ttLib import TTFont
from contour_geometry import Segment, read_outline, inspect_outline
from tail_join_geometry import NAMES, TIPS, join_pair, nonendpoint_intersections
from fix_italic_tail_joins import BASELINE
from check_curve_finish import introduced_corners
from ttf2otf import exact_cubic_error
from revision_scope import later_outline_changes


def published(style, fmt):
    folder = 'webfonts' if fmt == 'woff2' else fmt
    return TTFont(io.BytesIO(subprocess.check_output(['git', 'show',
        f'{BASELINE}:fonts/{folder}/VeryPeriSerif-{style}.{fmt}'])))


def path_in(root, style, fmt):
    name = f'VeryPeriSerif-{style}.{fmt}'; folder = 'webfonts' if fmt == 'woff2' else fmt
    return root/name if (root/name).exists() else root/folder/name


def reduced_quadratics(contour):
    """Read actual cubic CFF, reverse it, and verify exact quadratic reduction."""
    result = []
    for segment in reversed(contour):
        p = segment.points[::-1]
        if len(p) == 4:
            a = p[0]+1.5*(p[1]-p[0]); b = p[3]+1.5*(p[2]-p[3])
            assert np.linalg.norm(a-b) < .001, ('CFF is not exact degree elevation', a, b)
            result.append(Segment([p[0], (a+b)/2, p[3]]))
        else:
            result.append(Segment(p))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--root', type=Path, default=Path('build/release'))
    ap.add_argument('--formats', default='ttf,otf,woff2')
    args = ap.parse_args(); cfg = json.loads(Path('data/params.json').read_text())['regular_release']; count = 0
    formats = args.formats.split(',')
    if not set(formats) <= {'ttf', 'otf', 'woff2'}: raise ValueError('Unsupported format')
    result = {'release': cfg['version'], 'baseline_commit': BASELINE, 'fonts': {}, 'partial_optical_batch': True}
    def ck(value, label):
        nonlocal count
        assert value, label
        count += 1
    for style in ('Regular', 'Italic'):
        reference = published(style, 'ttf'); ttf = TTFont(path_in(args.root, style, 'ttf'))
        changed = []
        ck(reference.getGlyphOrder() == ttf.getGlyphOrder(), (style, 'glyph order'))
        for name in ttf.getGlyphOrder():
            if reference['glyf'][name].compile(reference['glyf']) != ttf['glyf'][name].compile(ttf['glyf']): changed.append(name)
        expected = (set(NAMES) if style == 'Italic' else set()) | later_outline_changes('1.111', style)
        ck(set(changed) == expected, (style, 'tail outlines and explicitly declared later revisions', changed))
        ck(reference['hmtx'].metrics == ttf['hmtx'].metrics, (style, 'all advances and bearings retained'))
        for tag in ('cmap', 'GSUB', 'GPOS', 'GDEF'):
            ck(reference.getTableData(tag) == ttf.getTableData(tag), (style, 'unchanged shaping/mark/kerning table', tag))
        if style == 'Italic':
            for name in NAMES:
                a, b = reference['glyf'][name], ttf['glyf'][name]
                ck(a.endPtsOfContours == b.endPtsOfContours and a.flags == b.flags, (name, 'contours and flags'))
                diffs = [(tuple(p), tuple(q)) for p, q in zip(a.coordinates, b.coordinates) if p != q]
                px = TIPS[name]
                ck(set(diffs) == {((px, 0), (px-1, -1)), ((px-7, -3), (px-7, -5))}, (name, 'exact local edit; all other points retained', diffs))
                ck((a.xMin, a.yMin, a.xMax, a.yMax) == (b.xMin, b.yMin, b.xMax, b.yMax), (name, 'bounds retained'))
                ck(not introduced_corners(reference, ttf, name), (name, 'no new hard corners'))
        for fmt in formats:
            path = path_in(args.root, style, fmt); f = TTFont(path)
            row = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'glyphs': {}}
            ck(f.getGlyphOrder() == reference.getGlyphOrder(), (style, fmt, 'glyph order'))
            ck(all(f['hmtx'][n][0] == reference['hmtx'][n][0] for n in f.getGlyphOrder()), (style, fmt, 'advances'))
            for tag in ('cmap', 'GSUB', 'GPOS', 'GDEF'):
                ck(f.getTableData(tag) == reference.getTableData(tag), (style, fmt, 'shaping table', tag))
            if fmt == 'otf':
                old = published(style, 'otf'); ca = old['CFF '].cff.topDictIndex[0].CharStrings; cb = f['CFF '].cff.topDictIndex[0].CharStrings
                program_changes = []
                for n in f.getGlyphOrder():
                    ca[n].decompile(); cb[n].decompile()
                    if ca[n].program != cb[n].program: program_changes.append(n)
                expected_cff=(set(NAMES) if style=='Italic' else set())|later_outline_changes('1.111',style,include_representation=False)
                ck(set(program_changes) == expected_cff, (style, 'only declared CFF geometry changes', program_changes))
                row['changed_charstrings'] = program_changes
            if style == 'Italic':
                for name in NAMES:
                    before = read_outline(reference, name)[0][0]; i, j = join_pair(before, name)
                    old_crossings = nonendpoint_intersections(before[i], before[j])
                    ck(len(old_crossings) == 1, (name, 'regression confirms original exact crossing'))
                    contours, closed = read_outline(f, name)
                    diag, _ = inspect_outline(contours, closed)
                    ck(len(contours) == 1 and all(closed), (name, fmt, 'one closed contour'))
                    ck(not any(e['kind'] in ('self_intersection', 'zero_segment', 'open_contour', 'disconnected') for e in diag), (name, fmt, 'topology', diag))
                    actual = reduced_quadratics(contours[0]) if fmt == 'otf' else contours[0]
                    i, j = join_pair(actual, name, True)
                    crossings = nonendpoint_intersections(actual[i], actual[j])
                    ck(not crossings, (name, fmt, 'no exact nonendpoint crossing', crossings))
                    error = exact_cubic_error(ttf, f, name) if fmt == 'otf' else 0.
                    ck(error < .002, (name, fmt, 'export preserves exact curves', error))
                    def area(font):
                        p = pathops.Path(); font.getGlyphSet()[name].draw(p.getPen()); return abs(p.area)
                    drift = abs(area(f)-area(reference))/area(reference)
                    ck(drift < .001, (name, fmt, 'ink area change', drift))
                    row['glyphs'][name] = {'original_intersection': old_crossings[0], 'exact_crossings_after': [],
                        'relative_ink_area_change': drift, 'exact_cubic_control_error': error,
                        'pointed_counter_join_intentionally_retained': True}
            result['fonts'][style+'/'+fmt] = row
    result.update(passed=count, failed=0)
    dest = Path(f'docs/qa/tail-joins-{cfg["version"]}.json')
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': count, 'failed': 0, 'report': str(dest)}))


if __name__ == '__main__': main()
