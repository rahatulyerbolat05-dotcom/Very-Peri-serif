#!/usr/bin/env python3
"""Replace the author's reported che construction step by one convex quadratic."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from curve_finish import load_source
from polish_outlines import hausdorff

BASELINE = '7e666222dbf743efff98c3dad22dd10051d1c82b'
NAME = 'uni0447'
START, CONTROL, END = (212, 267), (142, 267), (160, 340)


def old_font(style='Italic', fmt='ttf'):
    folder = 'webfonts' if fmt == 'woff2' else fmt
    return TTFont(io.BytesIO(subprocess.check_output(['git', 'show',
        f'{BASELINE}:fonts/{folder}/VeryPeriSerif-{style}.{fmt}'])))


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--write', action='store_true'); args = ap.parse_args()
    manifest_path = Path('data/curve-finish/manifest.json'); manifest = json.loads(manifest_path.read_text())
    previous = json.loads(subprocess.check_output(['git', 'show', BASELINE+':data/curve-finish/manifest.json']))
    record = previous['glyphs']['Italic'][NAME]; path = Path(record['path'])
    original = subprocess.check_output(['git', 'show', BASELINE+':'+str(path)])
    root = ET.fromstring(original); contour = root.find('outline/contour'); points = list(contour)
    xy = lambda p: (int(p.attrib['x']), int(p.attrib['y']))
    i = next(i for i,p in enumerate(points) if xy(p) == START)
    j = next(i for i,p in enumerate(points) if xy(p) == END)
    assert [xy(p) for p in points[i+1:j]] == [(180,267),(168,287),(165,292),(162,300),(152,301)]
    for p in points[i+1:j]: contour.remove(p)
    point = ET.Element('point', {'x': str(CONTROL[0]), 'y': str(CONTROL[1])}); point.tail = points[i+1].tail
    contour.insert(i+1, point); points[j].set('type', 'qcurve')
    raw = ET.tostring(root, encoding='utf-8', xml_declaration=True)+b'\n'
    raw = raw.replace(b"encoding='utf-8'", b"encoding='UTF-8'").replace(b' />', b'/>')
    current_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert current_sha in (record['sha256'], hashlib.sha256(raw).hexdigest()), 'Unexpected concurrent che source change'
    record['sha256'] = hashlib.sha256(raw).hexdigest()
    # Bounds and spacing are intentionally unchanged; the precise source check
    # below is repeated by the independent acceptance after the family build.
    original_font = TTFont(io.BytesIO(subprocess.check_output(['git','show',manifest['baseline_commit']+':fonts/ttf/VeryPeriSerif-Italic.ttf'])))
    if args.write: path.write_bytes(raw)
    else:
        print(raw.decode()); return
    glyph = load_source(NAME, record); glyph.recalcBounds(original_font['glyf'])
    assert [glyph.xMin,glyph.yMin,glyph.xMax,glyph.yMax] == record['bounds']
    record['outline_deviation'] = round(float(hausdorff(original_font['glyf'][NAME],glyph,original_font['glyf'])),4)
    record['repairs'].append({'repair':'replace transverse construction step and whole inner transition with one convex quadratic',
        'baseline_commit':BASELINE, 'start':START, 'control':CONTROL, 'end':END,
        'removed_points':[(180,267),(168,287),(165,292),(162,300),(152,301)],
        'recipe':'tools/fix_italic_che.py', 'source_nodes_removed':4})
    manifest['glyphs']['Italic'][NAME] = record; manifest['release'] = '1.112'
    manifest.setdefault('outline_revisions',{})['1.112'] = {'baseline_version':'1.111', 'baseline_commit':BASELINE,
                                                         'glyphs':{'Regular':[],'Italic':[NAME]}}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Installed convex che transition:', START, CONTROL, END)


if __name__ == '__main__': main()
