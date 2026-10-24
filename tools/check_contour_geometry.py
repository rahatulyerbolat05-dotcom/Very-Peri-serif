#!/usr/bin/env python3
"""Synthetic controls, invariance tests and an author-rejected historical glyph.

These verify detection of particular phenomena, not aesthetic precision on every
glyph. Corner fixtures deliberately produce candidates and are not defects.
"""
import argparse
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from contour_geometry import Segment, OutlinePen, digest, inspect_contour, inspect_outline, read_outline, normalized
from polish_audit import segments


def line(a, b): return Segment([a, b])


def smooth_wave(period=32, amplitude=1, start=0, cycles=2):
    # Cubic Hermite interpolation of a sine: shared analytic endpoint slopes.
    knots = np.linspace(start, start+period*cycles, cycles*8+1)
    result = []
    for a, b in zip(knots, knots[1:]):
        y = lambda x: amplitude*math.sin(2*math.pi*(x-start)/period)
        dy = lambda x: amplitude*2*math.pi/period*math.cos(2*math.pi*(x-start)/period)
        h = (b-a)/3
        result.append(Segment([(a, y(a)), (a+h, y(a)+h*dy(a)),
                               (b-h, y(b)-h*dy(b)), (b, y(b))]))
    return result


def kind(contour, name, closed=False):
    return [r for r in inspect_contour(contour, closed)[0] if r['kind'] == name]


class GeometryTests(unittest.TestCase):
    def test_all_offcurve_implicit_points(self):
        raw = [(0, 100, False), (100, 100, False), (100, 0, False), (0, 0, False)]
        parsed = segments(raw)
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0][1], (0, 50))
        for i in range(4):
            shifted = raw[i:]+raw[:i]
            self.assertEqual(len(segments(shifted)), 4)
        self.assertEqual(len(segments(list(reversed(raw)))), 4)

    def test_reader_components_and_alloffcurve(self):
        g = Glyph(); g.numberOfContours = 1
        g.coordinates = GlyphCoordinates([(0, 100), (100, 100), (100, 0), (0, 0)])
        g.endPtsOfContours = [3]; g.flags = bytearray([0]*4)
        b = FontBuilder(1000, isTTF=True); b.setupGlyphOrder(['.notdef', 'base', 'component'])
        p = TTGlyphPen({'base': g}); p.addComponent('base', (2, 0, 0, 1, 30, 40))
        b.setupGlyf({'.notdef': Glyph(), 'base': g, 'component': p.glyph()})
        b.setupHorizontalMetrics({n: (500, 0) for n in b.font.getGlyphOrder()})
        for name in ('base', 'component'):
            c, closed = read_outline(b.font, name)
            self.assertEqual(len(c), 1); self.assertEqual(len(c[0]), 4); self.assertEqual(closed, [True])
        c, _ = read_outline(b.font, 'component')
        np.testing.assert_allclose(c[0][0].points[0], (30, 90))

    def test_full_angle_range_including_old_boundaries(self):
        for degrees in (1.5, 5, 12, 12.01, 30, 90, 179, 180):
            for length in (1, 20):
                with self.subTest(degrees=degrees, length=length):
                    a = math.radians(degrees)
                    c = [line((0, 0), (length, 0)), line((length, 0), (length+length*math.cos(a), length*math.sin(a)))]
                    r = kind(c, 'tangent_break')
                    self.assertEqual(len(r), 1)
                    self.assertAlmostEqual(r[0]['metrics']['degrees'], degrees, places=4)

    def test_closing_join_and_reversed_contours(self):
        c = [line((0, 0), (10, 0)), line((10, 0), (5, 10)), line((5, 10), (0, 0))]
        expected = sorted(r['metrics']['degrees'] for r in kind(c, 'tangent_break', True))
        self.assertEqual(len(expected), 3)
        for i in range(3):
            for values in (c[i:]+c[:i], [Segment(s.points[::-1]) for s in reversed(c[i:]+c[:i])]):
                self.assertEqual(sorted(r['metrics']['degrees'] for r in kind(values, 'tangent_break', True)), expected)

    def test_smooth_nodes_do_not_hide_wave(self):
        c = smooth_wave()
        self.assertEqual(kind(c, 'tangent_break'), [])
        self.assertGreaterEqual(len(kind(c, 'curvature_wave')), 2)

    def test_closed_wave_survives_start_change_and_reversal(self):
        c = smooth_wave()+[line((64, 0), (64, -20)), line((64, -20), (-10, -20)),
                           line((-10, -20), (-10, 0)), line((-10, 0), (0, 0))]
        for i in (0, 3, 8, 16):
            rotated = c[i:]+c[:i]
            for values in (rotated, [Segment(s.points[::-1]) for s in reversed(rotated)]):
                self.assertGreaterEqual(len(kind(values, 'curvature_wave', True)), 2)

    def test_clean_closed_quadratic_round(self):
        c = [Segment([(0, 50), (0, 100), (50, 100)]),
             Segment([(50, 100), (100, 100), (100, 50)]),
             Segment([(100, 50), (100, 0), (50, 0)]),
             Segment([(50, 0), (0, 0), (0, 50)])]
        self.assertEqual(inspect_contour(c, True)[0], [])

    def test_wave_scales_and_rotation(self):
        # Controlled regression variants, not a statistical held-out benchmark.
        for period, amp, deg in ((11, .8, 37), (73, 2, 113), (141, 4, 211)):
            c = smooth_wave(period, amp)
            a = math.radians(deg); matrix = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            c = [Segment(s.points @ matrix.T + (73, -29)) for s in c]
            self.assertTrue(kind(c, 'curvature_wave'), (period, amp, deg))
            self.assertEqual(kind(c, 'tangent_break'), [])

    def test_clean_quadratic_and_degree_elevated_cubic(self):
        q = Segment([(0, 0), (50, 30), (100, 0)])
        p = q.points; c = Segment([p[0], p[0]+2*(p[1]-p[0])/3, p[2]+2*(p[1]-p[2])/3, p[2]])
        ts = np.linspace(0, 1, 101)
        np.testing.assert_allclose(q.evaluate(ts), c.evaluate(ts), atol=1e-12)
        np.testing.assert_allclose(q.curvature(ts), c.curvature(ts), atol=1e-12)
        for seg in (q, c):
            self.assertFalse(kind([seg], 'curvature_wave'))
            self.assertFalse(kind([seg], 'tangent_break'))
            self.assertFalse(kind([seg], 'curvature_jump'))

    def test_curvature_jump_with_exactly_matching_tangents(self):
        a = Segment([(0, 0), (50, 0), (100, 50)])
        b = Segment([(100, 50), (110, 60), (150, 50)])
        self.assertEqual(kind([a, b], 'tangent_break'), [])
        self.assertTrue(kind([a, b], 'curvature_jump'))

    def test_zero_endpoint_and_interior_stationary_point(self):
        repeated = Segment([(0, 0), (0, 0), (10, 0), (10, 10)])
        np.testing.assert_allclose(repeated.tangent(False), (1, 0))
        c = [line((-10, 0), (0, 0)), repeated]
        self.assertEqual(kind(c, 'tangent_break'), [])
        self.assertTrue(kind(c, 'singular_endpoint'))
        self.assertTrue(kind([Segment([(0, 0), (10, 0), (0, 0)])], 'interior_stationary'))

    def test_micro_and_degenerate_segment(self):
        self.assertTrue(kind([line((0, 0), (2, 0))], 'short_segment'))
        self.assertTrue(kind([line((0, 0), (0, 0))], 'zero_segment'))

    def test_topology_crossing(self):
        c = [line((0, 0), (20, 20)), line((20, 20), (0, 20)),
             line((0, 20), (20, 0)), line((20, 0), (0, 0))]
        self.assertTrue(kind(c, 'self_intersection', True))

    def test_translation_invariant_signature(self):
        a = [[Segment([(0, 0), (50, 20), (100, 0)])]]
        b = [[Segment(a[0][0].points+(20, -10))]]
        self.assertEqual(normalized(a)[1], normalized(b)[1])
        b[0][0].points[1, 1] += .1
        self.assertNotEqual(normalized(a)[1], normalized(b)[1])

    def test_missing_component_is_an_error(self):
        from fontTools.pens.basePen import MissingComponentError
        with self.assertRaises(MissingComponentError):
            OutlinePen({}).addComponent('missing', (1, 0, 0, 1, 0, 0))

    def test_review_hashes_and_whole_form_gate(self):
        from contour_audit import apply_decisions, summarize
        def report():
            return {'detector_sha256': 'engine', 'cases': [{'id': 'case', 'style': 'Regular',
                'geometry_sha256': 'shape', 'status': 'unreviewed', 'evidence': []}], 'errors': [],
                'shapes': {'shape': {'contours': [[1]], 'uses': [['Regular/TTF', 'x']]}},
                'fonts': {'Regular/TTF': {'style': 'Regular'}}}
        r = report(); apply_decisions(r, {'decisions': {'case': {'geometry_sha256': 'old-shape',
            'detector_sha256': 'engine', 'status': 'intentional', 'reason': 'old review'}}}); summarize(r)
        self.assertEqual(r['cases'][0]['status'], 'unreviewed'); self.assertEqual(r['stale_decisions'], ['case'])
        ledger = {'decisions': {'case': {'geometry_sha256': 'shape', 'detector_sha256': 'engine',
                                      'status': 'intentional', 'reason': 'specific intentional corner'}}}
        r = report(); apply_decisions(r, ledger); summarize(r)
        self.assertEqual(r['summary']['unresolved'], 0)
        self.assertEqual(r['summary']['unreviewed_whole_forms'], 1)
        form_id = digest(['Regular', 'shape', 'engine', 'whole-form'])[:24]
        ledger['forms'] = {form_id: {'geometry_sha256': 'shape', 'detector_sha256': 'engine',
                                     'status': 'reviewed', 'reason': 'complete form inspected'}}
        r = report(); apply_decisions(r, ledger); summarize(r)
        self.assertEqual(r['summary']['unreviewed_whole_forms'], 0)
        ledger['decisions']['case']['reason'] = ''
        with self.assertRaises(ValueError): apply_decisions(report(), ledger)

    def test_historical_rejected_ya_foot(self):
        old = TTFont(io.BytesIO(subprocess.check_output(['git', 'show', 'aa705fd:fonts/ttf/VeryPeriSerif-Regular.ttf'])))
        current = TTFont('fonts/ttf/VeryPeriSerif-Regular.ttf')
        found = []
        for f in (old, current):
            c, closed = read_outline(f, 'uni044F'); rows, _ = inspect_outline(c, closed)
            found.append([r for r in rows if r['kind'] == 'curvature_wave' and 245 <= r['xy'][0] <= 350 and -20 <= r['xy'][1] <= 120])
        self.assertTrue(found[0], 'Must catch the full rejected 1.106 foot, not only a node angle')
        self.assertFalse(found[1], 'The accepted convex replacement must not retain that wave')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', default='build/contour-audit/detector-checks.json'); args = ap.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeometryTests))
    import hashlib
    report = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'geometry_source_sha256': hashlib.sha256(Path('tools/contour_geometry.py').read_bytes()).hexdigest(),
              'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'skipped': len(result.skipped), 'scope': __doc__,
              'failure_details': [str(test)+'\n'+detail for test, detail in result.failures+result.errors]}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    if not result.wasSuccessful(): raise SystemExit(1)


if __name__ == '__main__': main()
