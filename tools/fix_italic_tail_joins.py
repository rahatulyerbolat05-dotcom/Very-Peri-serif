#!/usr/bin/env python3
"""Reproducible two-point repair from the reviewed 1.110 sources; no smoothing.

--write installs the three GLIFs and updates their manifest records. Every other
point, contour flag, metric, bowl and descender terminal is retained verbatim.
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from contour_geometry import read_outline
from tail_join_geometry import NAMES, TIPS, join_pair, nonendpoint_intersections
from polish_outlines import hausdorff

BASELINE = '0e188acf468be06e90c88e27e85dc9f8f6aa6a48'


def baseline_font():
    return TTFont(io.BytesIO(subprocess.check_output(['git', 'show', BASELINE+':fonts/ttf/VeryPeriSerif-Italic.ttf'])))


def repair(font, name):
    g = copy.deepcopy(font['glyf'][name]); px = TIPS[name]
    edits = {(px, 0): (px-1, -1), (px-7, -3): (px-7, -5)}
    count = 0
    for i, point in enumerate(g.coordinates):
        if tuple(point) in edits:
            g.coordinates[i] = edits[tuple(point)]; count += 1
    assert count == 2, ('Expected the original pointed tail join', name, count)
    g.recalcBounds(font['glyf'])
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--write', action='store_true'); args = ap.parse_args()
    old = baseline_font(); new = copy.deepcopy(old)
    baseline_manifest = json.loads(subprocess.check_output(['git', 'show', BASELINE+':data/curve-finish/manifest.json']))
    manifest_path = Path('data/curve-finish/manifest.json'); manifest = json.loads(manifest_path.read_text())
    original = TTFont(io.BytesIO(subprocess.check_output(['git', 'show', manifest['baseline_commit']+':fonts/ttf/VeryPeriSerif-Italic.ttf'])))
    result = {}
    for name in NAMES:
        new['glyf'][name] = repair(old, name)
        c = read_outline(old, name)[0][0]; d = read_outline(new, name)[0][0]
        a, b = join_pair(c, name); x, y = join_pair(d, name, True)
        before = nonendpoint_intersections(c[a], c[b]); after = nonendpoint_intersections(d[x], d[y])
        assert len(before) == 1 and not after, (name, before, after)
        record = copy.deepcopy(baseline_manifest['glyphs']['Italic'][name]); path = Path(record['path'])
        old_raw = subprocess.check_output(['git', 'show', BASELINE+':'+str(path)])
        root = ET.fromstring(old_raw); px = TIPS[name]; count = 0
        for point in root.findall('.//point'):
            xy = (float(point.attrib['x']), float(point.attrib['y']))
            if xy == (px, 0): point.set('x', str(px-1)); point.set('y', '-1'); count += 1
            elif xy == (px-7, -3): point.set('y', '-5'); count += 1
        assert count == 2
        serialized = ET.tostring(root, encoding='utf-8', xml_declaration=True)+b'\n'
        raw = serialized.replace(b"encoding='utf-8'", b"encoding='UTF-8'").replace(b' />', b'/>')
        assert hashlib.sha256(path.read_bytes()).hexdigest() in (record['sha256'], hashlib.sha256(raw).hexdigest(), hashlib.sha256(serialized).hexdigest()), ('Unexpected concurrent source change', path)
        record['sha256'] = hashlib.sha256(raw).hexdigest()
        record['outline_deviation'] = round(float(hausdorff(original['glyf'][name], new['glyf'][name], original['glyf'])), 4)
        record['repairs'].append({'repair': 'remove literal self-crossing loop at pointed tail/body join',
            'baseline_commit': BASELINE, 'tip_before': [px, 0], 'tip_after': [px-1, -1],
            'control_before': [px-7, -3], 'control_after': [px-7, -5],
            'confirmed_intersection_before': before[0], 'recipe': 'tools/fix_italic_tail_joins.py'})
        if args.write:
            path.write_bytes(raw); manifest['glyphs']['Italic'][name] = record
        result[name] = {'before': before, 'after': after, 'changed_points': 2}
    if args.write:
        manifest['release'] = '1.111'
        manifest.setdefault('outline_revisions', {})['1.111'] = {
            'baseline_version': '1.110', 'baseline_commit': BASELINE,
            'glyphs': {'Regular': [], 'Italic': list(NAMES)}}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
