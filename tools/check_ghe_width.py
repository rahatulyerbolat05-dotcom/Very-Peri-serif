#!/usr/bin/env python3
"""Independent acceptance of the widened Italic ghe against release 1.109."""
import hashlib, io, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
import pathops
import uharfbuzz as hb
from family_finish import base_tables
from family_curve_audit import inspect
from italic_rules_measure import polys, runs
from check_family import CHARS
from check_curve_finish import introduced_corners
from revision_scope import later_outline_changes

BASELINE = '4ffae31c961c4ec2108224c522d815b24433f456'
NAMES = ('uni0433', 'uni0493')


def anchors(font):
    return {name: [(a.XCoordinate, a.YCoordinate) if a else None for a in record.BaseAnchor]
            for table in base_tables(font)
            for name, record in zip(table.BaseCoverage.glyphs, table.BaseArray.BaseRecord)}


def main():
    cfg = json.loads(Path('data/params.json').read_text())
    version = cfg['regular_release']['version']; width = cfg['premium_review']['italic_ghe_width']
    report = {'version': version, 'baseline_commit': BASELINE, 'styles': {}}; count = 0
    def ck(ok, label):
        nonlocal count
        assert ok, label
        count += 1
    for style in ('Regular', 'Italic'):
        old = TTFont(io.BytesIO(subprocess.check_output(['git', 'show', f'{BASELINE}:fonts/ttf/VeryPeriSerif-{style}.ttf'])))
        path = Path(f'build/release/VeryPeriSerif-{style}.ttf'); new = TTFont(path)
        ck(new.getGlyphOrder() == old.getGlyphOrder(), (style, 'glyph order'))
        changed = [n for n in new.getGlyphOrder() if new['glyf'][n].compile(new['glyf']) != old['glyf'][n].compile(old['glyf'])]
        metrics = [n for n in new.getGlyphOrder() if new['hmtx'][n] != old['hmtx'][n]]
        expected = set(NAMES) if style == 'Italic' else set()
        ck(set(changed) == expected | later_outline_changes('1.110', style), (style, 'ghe and explicitly declared later outline revisions', changed))
        ck(set(metrics) == expected, (style, 'only declared advance changes', metrics))
        row = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'changed_outlines': changed, 'changed_metrics': metrics}
        if style == 'Italic':
            before_anchors, after_anchors = anchors(old), anchors(new)
            for name in NAMES:
                a, b = old['glyf'][name], new['glyf'][name]
                ck(new['hmtx'][name] == (old['hmtx'][name][0]+20, old['hmtx'][name][1]), (name, 'advance and bearing'))
                ck((b.xMin, b.yMin, b.xMax, b.yMax) == (a.xMin, a.yMin, a.xMax+20, a.yMax), (name, 'flourish span and height'))
                ck(a.numberOfContours == b.numberOfContours == 1, (name, 'merged single contour'))
                expected_anchors = [(p[0]+10, p[1]) if p else None for p in before_anchors[name]]
                ck(after_anchors[name] == expected_anchors, (name, 'all mark anchors shift with the stem'))
                diag = inspect(new, name, .35, rough=False)
                ck(not diag['micro'] and not diag['waves'] and not any(p['degrees'] >= 5 for p in diag['kinks']), (name, 'curve quality', diag))
                ck(not introduced_corners(old,new,name,(10,0) if name=='uni0493' else (0,0)), (name,'no new hard corners'))
                def area(font):
                    p = pathops.Path(); font.getGlyphSet()[name].draw(p.getPen()); return abs(p.area)
                ck(1 < area(new)/area(old) < 1.04, (name, 'modest ink increase without thickening the stem'))
            original, actual = polys(old, 'uni0433', 0), polys(new, 'uni0433', 0)
            for y in (205.1, 225.1, 245.1, 265.1, 285.1, 305.1):
                a, b = runs(original, y), runs(actual, y)
                ck(len(a) == len(b) == 1 and all(abs(x-z-10) < .05 for x,z in zip(b[0],a[0])), ('exact translated stem profile', y))
            family = json.loads(Path('build/release/family-validation.json').read_text())
            ck('uni0433' not in family['native_cyrillic_clones'], 'Authored ghe is independently kerned')
            rows = json.loads(Path('build/premium/italic-pairs.json').read_text())
            evaluated = {(r['left'], r['right']) for r in rows}
            cm = new.getBestCmap()
            for name in NAMES:
                for ch in CHARS:
                    for pair in ((name, cm[ord(ch)]), (cm[ord(ch)], name)):
                        ck(pair in evaluated, ('width-related Cyrillic pair evaluated', pair))
            data = path.read_bytes(); hf = hb.Font(hb.Face(data)); hb.ot_font_set_funcs(hf)
            def shape(text, language='ru', features=None):
                b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); b.language = language
                hb.shape(hf, b, features or {})
                return [new.getGlyphName(g.codepoint) for g in b.glyph_infos]
            ck(shape('г') == ['uni0433'], 'Default Cyrillic ghe')
            ck(shape('г', 'sr') == shape('г', 'mk') == ['imacron'], 'Native local forms preserved')
            ck(shape('г', features={'ss04': True}) == ['uni0433.ss04'], 'Printed alternate preserved')
            row.update(advance_before=288, advance_after=width['advance'], stem_translation_x=10,
                       diagonal_stem_weight_preserved=True, mark_anchor_dx=10)
        report['styles'][style] = row
    report.update(passed=count, failed=0)
    Path(f'docs/qa/ghe-width-{version}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__': main()
