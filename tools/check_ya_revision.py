#!/usr/bin/env python3
"""Accept the author's ya corrections against the published 1.108 files."""
import hashlib, io, json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from italic_el_alternate import legacy_font as TTFont  # base-glyph regression; ss10 has its own gate
import pathops
from family_curve_audit import contours, tangent_out, angle
from polish_audit import segments
from polish_outlines import hausdorff
from check_curve_finish import introduced_corners
from revision_scope import later_outline_changes

BASELINE = '6e8abaf7b461761707ce648be59eba4fe62a44eb'
NAME = 'uni044F'


def curvature(curve, end):
    a, c, b = curve[1:4]
    v = (2*(b[0]-c[0]), 2*(b[1]-c[1])) if end else (2*(c[0]-a[0]), 2*(c[1]-a[1]))
    d = (2*(b[0]-2*c[0]+a[0]), 2*(b[1]-2*c[1]+a[1]))
    return abs(v[0]*d[1]-v[1]*d[0]) / math.hypot(*v)**3


def crown_curvatures(font):
    curves = segments(contours(font, NAME)[0])
    i = next(i for i, curve in enumerate(curves) if curve[1] == (215, 516))
    return [curvature(curves[i-1], True), curvature(curves[i], False)]


def jump_at(font, xy):
    curves = segments(contours(font, NAME)[0])
    i = next(i for i, curve in enumerate(curves) if curve[1] == xy)
    return abs(angle(tangent_out(curves[i-1], True), tangent_out(curves[i], False)))


def main():
    version = json.loads(Path('data/params.json').read_text())['regular_release']['version']
    sources = json.loads(Path('data/curve-finish/manifest.json').read_text())['glyphs']
    report = {'version': version, 'baseline_commit': BASELINE, 'styles': {}}
    checks = 0
    def ck(ok, context):
        nonlocal checks
        assert ok, context
        checks += 1
    for style in ('Regular', 'Italic'):
        raw = Path(f'build/release/VeryPeriSerif-{style}.ttf').read_bytes()
        new = TTFont(io.BytesIO(raw))
        old = TTFont(io.BytesIO(subprocess.check_output(['git', 'show', f'{BASELINE}:fonts/ttf/VeryPeriSerif-{style}.ttf'])))
        ck(new.getGlyphOrder() == old.getGlyphOrder(), (style, 'glyph order'))
        changed = [n for n in new.getGlyphOrder() if new['glyf'][n].compile(new['glyf']) != old['glyf'][n].compile(old['glyf'])]
        refinements = {n:r for n,r in sources[style].items()
                       if r.get('input_advance_and_lsb',r['advance_and_lsb']) != r['advance_and_lsb']}
        ck(set(changed) == {NAME}|set(refinements)|later_outline_changes('1.109', style), (style, 'ya, declared width and later outline refinements', changed))
        expected_metrics = dict(old['hmtx'].metrics)
        expected_metrics.update({n:tuple(r['advance_and_lsb']) for n,r in refinements.items()})
        ck(new['hmtx'].metrics == expected_metrics, (style, 'all other advances and bearings'))
        a, b = old['glyf'][NAME], new['glyf'][NAME]
        ck((a.xMin, a.yMin, a.xMax, a.yMax) == (b.xMin, b.yMin, b.xMax, b.yMax), (style, 'ya bounds'))
        ck(a.numberOfContours == b.numberOfContours == 2, (style, 'contours'))
        before, after = contours(old, NAME), contours(new, NAME)
        ck(before[1] == after[1], (style, 'counter unchanged'))
        ck(not introduced_corners(old, new, NAME), (style, 'new hard corners'))
        deviation = float(hausdorff(a, b, old['glyf']))
        ck(deviation < 3, (style, 'local contour displacement', deviation))
        def area(font):
            p = pathops.Path(); font.getGlyphSet()[NAME].draw(p.getPen())
            return abs(p.area)
        drift = abs(area(new)-area(old))/area(old)
        ck(drift < .005, (style, 'ink area change', drift))
        row = {'sha256': hashlib.sha256(raw).hexdigest(), 'changed_glyphs': changed,
               'outline_deviation': round(deviation, 3), 'relative_ink_area_change': drift}
        if style == 'Regular':
            def without_top(points):
                start = points.index((215., 516., True)); end = points.index((318., 401., True))
                return points[:start+1] + points[end:]
            ck(without_top(before[0]) == without_top(after[0]), 'Regular only upper-right bowl arc changes')
            previous, current = crown_curvatures(old), crown_curvatures(new)
            ck(abs(previous[1]/previous[0]-1) > .5, 'Regression detects old crown curvature jump')
            ck(abs(current[1]/current[0]-1) < .1, ('Regular crown curvature continuity', current))
            curves = segments(after[0]); active = False
            jumps = []
            for i, curve in enumerate(curves):
                if curve[1] == (215, 516): active = True
                if active:
                    ck(curve[0] == 'Q', 'Regular upper arc has no flat line segment')
                    ck(angle(tangent_out(curve, False), tangent_out(curve, True)) < 0, 'Regular upper arc remains convex')
                    jump = abs(curvature(curve, False)/curvature(curves[i-1], True)-1)
                    ck(jump < .1, ('Regular complete upper arc curvature continuity', curve[1], jump))
                    jumps.append(jump)
                if active and curve[3] == (318, 401): break
            row['crown_curvatures_before'] = previous; row['crown_curvatures_after'] = current
            row['upper_arc_relative_curvature_jumps'] = jumps
        else:
            ck(jump_at(old, (273, 100)) > 8, 'Regression detects old short stem kink')
            ck(jump_at(old, (398, 170)) > 25, 'Regression detects old terminal corner')
            ck(jump_at(new, (273, 100)) < 1, 'Italic stem tangent')
            ck(jump_at(new, (398, 170)) < 1, 'Italic terminal tangent')
            ck((271., 95., True) not in after[0], 'Italic short intermediate line removed')
            row['stem_break_degrees'] = jump_at(new, (273, 100))
            row['terminal_break_degrees'] = jump_at(new, (398, 170))
        report['styles'][style] = row
    report.update(passed=checks, failed=0)
    Path(f'docs/qa/ya-{version}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__': main()
