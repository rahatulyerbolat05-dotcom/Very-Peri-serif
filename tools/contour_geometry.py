"""Independent line/quadratic/cubic geometry for exported-font inspection.

BasePen resolves implicit TrueType points, all-off-curve contours and transformed
components. Coordinates are normalized to 1000 UPM, never written back to a font.
Findings nominate review sites; intentional corners are not automatically defects.
"""
from dataclasses import dataclass
import hashlib
import json
import math

import numpy as np
from fontTools.pens.basePen import BasePen
from shapely.geometry import LinearRing, Polygon
from shapely.validation import explain_validity

RULES = {'angle_degrees': 1.5, 'micro_length': 3.0, 'flatness': 0.035,
         'sample_step': 1.0, 'curvature_floor': 0.0002,
         'jump_absolute': 0.003, 'jump_relative': 0.35,
         'scales': [4, 12, 32, 80], 'merge_arc_distance': 8.0}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def cross(a, b):
    return a[..., 0]*b[..., 1]-a[..., 1]*b[..., 0]


@dataclass
class Segment:
    points: np.ndarray

    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)
        if self.points.shape not in ((2, 2), (3, 2), (4, 2)):
            raise ValueError('Unsupported Bezier segment')
        if not np.isfinite(self.points).all():
            raise ValueError('Non-finite outline coordinate')

    @property
    def degree(self):
        return len(self.points)-1

    def evaluate(self, t, derivative=0):
        p = self.points.copy()
        for _ in range(derivative):
            p = (len(p)-1)*np.diff(p, axis=0)
        t = np.asarray(t, dtype=float)
        if not len(p):
            return np.zeros(t.shape+(2,))
        p = np.broadcast_to(p, t.shape+p.shape).copy()
        for k in range(p.shape[-2]-1, 0, -1):
            p = (1-t[..., None, None])*p[..., :k, :]+t[..., None, None]*p[..., 1:k+1, :]
        return p[..., 0, :]

    def tangent(self, end=False):
        origin = self.points[-1] if end else self.points[0]
        candidates = self.points[-2::-1] if end else self.points[1:]
        for point in candidates:
            v = origin-point if end else point-origin
            if np.linalg.norm(v) > 1e-10:
                return v/np.linalg.norm(v)
        return None

    def curvature(self, t):
        a, b = self.evaluate(t, 1), self.evaluate(t, 2)
        speed = np.linalg.norm(a, axis=-1)
        with np.errstate(invalid='ignore', divide='ignore'):
            return np.where(speed > 1e-10, cross(a, b)/speed**3, np.nan)

    def flatten(self, tolerance=None):
        """Bound control-to-chord distance and length: avoid skipping tiny loops."""
        tolerance = RULES['flatness'] if tolerance is None else tolerance
        result = [(0., self.points[0])]
        def split(p, a, b, depth):
            chord = p[-1]-p[0]; length = np.linalg.norm(chord)
            excess = float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()-length)
            flat = float(np.max(np.abs(cross(p-p[0], chord)))/length) if length else float(np.max(np.linalg.norm(p-p[0], axis=1)))
            if (flat <= tolerance and excess <= tolerance) or depth >= 20:
                if depth >= 20 and max(flat, excess) > tolerance:
                    raise ValueError('Adaptive subdivision did not converge')
                result.append((b, p[-1])); return
            rows = [p]
            while len(rows[-1]) > 1:
                rows.append((rows[-1][:-1]+rows[-1][1:])/2)
            mid = (a+b)/2
            split(np.array([r[0] for r in rows]), a, mid, depth+1)
            split(np.array([r[-1] for r in rows[::-1]]), mid, b, depth+1)
        split(self.points, 0., 1., 0)
        return np.array([t for t, _ in result]), np.array([p for _, p in result])


class OutlinePen(BasePen):
    def __init__(self, glyph_set, upm=1000):
        super().__init__(glyph_set)
        self.skipMissingComponents = False
        self.scale = 1000/upm
        self.contours = []
        self.closed = []
        self.current = None

    def _point(self, p):
        return np.asarray(p, dtype=float)*self.scale

    def _moveTo(self, p):
        if self.current is not None:
            raise ValueError('Unterminated contour')
        self.current = []; self.start = self.cursor = self._point(p)

    def _lineTo(self, p):
        p = self._point(p); self.current.append(Segment([self.cursor, p])); self.cursor = p

    def _qCurveToOne(self, c, p):
        c, p = self._point(c), self._point(p)
        self.current.append(Segment([self.cursor, c, p])); self.cursor = p

    def _curveToOne(self, a, b, p):
        a, b, p = self._point(a), self._point(b), self._point(p)
        self.current.append(Segment([self.cursor, a, b, p])); self.cursor = p

    def _closePath(self):
        if np.linalg.norm(self.cursor-self.start) > 1e-10:
            self.current.append(Segment([self.cursor, self.start]))
        self.contours.append(self.current); self.closed.append(True); self.current = None

    def _endPath(self):
        self.contours.append(self.current); self.closed.append(False); self.current = None


def read_outline(font, name):
    gs = font.getGlyphSet(); pen = OutlinePen(gs, font['head'].unitsPerEm)
    gs[name].draw(pen)
    if pen.current is not None:
        raise ValueError('Open pen state after drawing')
    if 'glyf' in font:
        expected = len(font['glyf'][name].getCoordinates(font['glyf'])[1])
        if expected != len(pen.contours):
            raise ValueError(f'Contour coverage mismatch: expected {expected}, read {len(pen.contours)}')
    return pen.contours, pen.closed


def serialize(contours):
    return [[s.points.tolist() for s in c] for c in contours]


def normalized(contours):
    points = [s.points for c in contours for s in c]
    origin = np.vstack(points).min(axis=0) if points else np.zeros(2)
    data = [[np.round(s.points-origin, 10).tolist() for s in c] for c in contours]
    return origin, digest(data)


def sample_contour(contour, step=None):
    step = step or RULES['sample_step']
    positions, xy, curvature, seg_ids, parameters = [], [], [], [], []
    starts, lengths = [], []; distance = 0.
    for i, seg in enumerate(contour):
        ts, pts = seg.flatten()
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        length = float(arc[-1]); starts.append(distance); lengths.append(length)
        if length > 1e-10:
            s = np.linspace(0, length, max(2, math.ceil(length/step)), endpoint=False)
            t = np.interp(s, arc, ts)
            positions.extend(distance+s); xy.extend(seg.evaluate(t)); curvature.extend(seg.curvature(t))
            seg_ids.extend([i]*len(t)); parameters.extend(t)
        distance += length
    return {'s': np.asarray(positions), 'xy': np.asarray(xy).reshape(-1, 2),
            'k': np.asarray(curvature), 'segment': np.asarray(seg_ids),
            't': np.asarray(parameters), 'starts': starts, 'lengths': lengths, 'length': distance}


def angle(a, b):
    return math.degrees(math.atan2(abs(float(cross(a, b))), float(np.dot(a, b))))


def inspect_contour(contour, closed=True):
    """Absolute candidates, with no baseline immunity or automatic corner waiver."""
    findings = []; sample = sample_contour(contour); n = len(contour)
    def add(kind, i, s, xy, **metrics):
        findings.append({'kind': kind, 'segment': int(i), 's': round(float(s), 5),
                         'xy': [round(float(v), 5) for v in xy], 'metrics': metrics})
    if not n:
        add('empty_contour', 0, 0, (0, 0)); return findings, sample
    if not closed:
        add('open_contour', 0, 0, contour[0].points[0])
    breaks = []
    for i, seg in enumerate(contour):
        start, length = sample['starts'][i], sample['lengths'][i]
        if length <= 1e-9:
            add('zero_segment', i, start, seg.points[0])
        elif length <= RULES['micro_length']:
            add('short_segment', i, start+length/2, seg.evaluate(.5), length=round(length, 5))
        previous = contour[i-1]
        has_join = closed or i > 0
        if has_join and np.linalg.norm(previous.points[-1]-seg.points[0]) > 1e-7:
            add('disconnected', i, start, seg.points[0])
        a, b = previous.tangent(True), seg.tangent(False)
        if has_join and (a is None or b is None):
            add('undefined_tangent', i, start, seg.points[0]); breaks.append(start)
        degrees = angle(a, b) if a is not None and b is not None else 180.
        if has_join and degrees+1e-9 >= RULES['angle_degrees']:
            add('tangent_break', i, start, seg.points[0], degrees=round(degrees, 5),
                incoming=a.tolist(), outgoing=b.tolist()); breaks.append(start)
        # One-sided endpoint limits; zero-derivative cases are separately visible.
        kl, kr = float(previous.curvature(1.)), float(seg.curvature(0.))
        if has_join and (not math.isfinite(kl) or not math.isfinite(kr)):
            add('singular_endpoint', i, start, seg.points[0])
        elif has_join and degrees < RULES['angle_degrees']:
            jump = abs(kl-kr); relative = jump/(.002+max(abs(kl), abs(kr)))
            if jump >= RULES['jump_absolute'] and relative >= RULES['jump_relative']:
                add('curvature_jump', i, start, seg.points[0], incoming=round(kl, 7),
                    outgoing=round(kr, 7), absolute=round(jump, 7), relative=round(relative, 5))
        # Cubic loops/cusps can live inside one segment. Find stationary points
        # from polynomial derivatives rather than hoping a uniform sample hits one.
        p = seg.points
        if seg.degree == 2:
            coeff = np.array([2*(p[2]-2*p[1]+p[0]), 2*(p[1]-p[0])])
        elif seg.degree == 3:
            coeff = np.array([3*(-p[0]+3*p[1]-3*p[2]+p[3]),
                              6*(p[0]-2*p[1]+p[2]), 3*(p[1]-p[0])])
        else:
            coeff = np.array([p[1]-p[0]])
        for axis in (0, 1):
            values = np.trim_zeros(coeff[:, axis], 'f')
            for t in np.roots(values) if len(values) > 1 else []:
                if abs(t.imag) < 1e-9 and 1e-7 < t.real < 1-1e-7:
                    t = float(t.real)
                    if np.linalg.norm(seg.evaluate(t, 1)) < 1e-7:
                        add('interior_stationary', i, start+length*t, seg.evaluate(t), t=round(t, 7))
                        break
    # Group signed curvature across segment boundaries, not just at on-curve nodes.
    s, k, pts = sample['s'], sample['k'], sample['xy']; perimeter = sample['length']
    if len(s) >= 4 and perimeter:
        # Rotate after the strongest corner so a contour's arbitrary start does
        # not split a wave. With no corners, merge equal signs around closure.
        origin = int(np.searchsorted(s, breaks[0])) % len(s) if breaks else 0
        ids = np.roll(np.arange(len(s)), -origin)
        arc = (s[ids]-s[origin]) % perimeter
        break_arcs = sorted((b-s[origin]) % perimeter for b in breaks)
        groups = []
        for j, idx in enumerate(ids):
            value = k[idx]; sign = 1 if value > RULES['curvature_floor'] else -1 if value < -RULES['curvature_floor'] else 0
            if not math.isfinite(value): sign = 0
            ds = float((s[(idx+1)%len(s)]-s[idx]) % perimeter)
            cut = j == 0 or any(arc[j-1] < b <= arc[j]+1e-7 for b in break_arcs)
            if groups and groups[-1]['sign'] == sign and not cut:
                g = groups[-1]; g['ids'].append(int(idx)); g['length'] += ds
                g['turn'] += value*ds if sign else 0
            else:
                groups.append({'sign': sign, 'ids': [int(idx)], 'length': ds,
                               'turn': float(value*ds) if sign else 0., 'cut': cut})
        # A true inflection passes through zero curvature. Small neutral spans
        # must not conceal the sign change on a broad, shallow wave.
        compact = []
        for g in groups:
            if not g['sign'] and g['length'] <= 4 and not g['cut']:
                if compact:
                    compact[-1]['length'] += g['length']; compact[-1]['ids'].extend(g['ids'])
                continue
            if compact and g['sign'] == compact[-1]['sign'] and not g['cut']:
                compact[-1]['length'] += g['length']; compact[-1]['turn'] += g['turn']; compact[-1]['ids'].extend(g['ids'])
            else:
                compact.append(g)
        groups = compact
        if closed and not breaks and len(groups) > 1 and groups[0]['sign'] == groups[-1]['sign']:
            groups[0]['ids'] = groups[-1]['ids']+groups[0]['ids']
            groups[0]['length'] += groups[-1]['length']; groups[0]['turn'] += groups[-1]['turn']; groups.pop()
        if closed and not breaks and groups:
            groups[0]['cut'] = False
        for i, g in enumerate(groups):
            if not g['sign'] or len(groups) < 3 or (not closed and i in (0, len(groups)-1)):
                continue
            a, b = groups[i-1], groups[(i+1)%len(groups)]
            if g['cut'] or b['cut'] or a['sign'] != -g['sign'] or b['sign'] != -g['sign']:
                continue
            if min(abs(a['turn']), abs(b['turn'])) < math.radians(.5) or abs(g['turn']) < math.radians(1):
                continue
            scales = [w for w in RULES['scales'] if g['length'] <= 2*w]
            if scales:
                idx = g['ids'][len(g['ids'])//2]
                add('curvature_wave', sample['segment'][idx], s[idx], pts[idx],
                    span=round(g['length'], 4), turn_degrees=round(math.degrees(g['turn']), 4), scales=scales)
        # Near-straight local edges are candidates, never an assumption that a
        # gentle optical curve must be straight. Do not erase nearby corner data.
        for w in (32, 80):
            stride = max(1, int(w/4))
            for i in range(0, len(s), stride):
                d = (s-s[i]) % perimeter
                chosen = np.flatnonzero(d <= w)
                chosen = chosen[np.argsort(d[chosen])]
                if len(chosen) < 4 or (not closed and s[i]+w > perimeter): continue
                if any(1e-7 < (v-s[i]) % perimeter < w-1e-7 for v in breaks): continue
                q = pts[chosen]; chord = q[-1]-q[0]; extent = np.linalg.norm(chord)
                if extent < .9*w: continue
                values = k[chosen]
                if not np.isfinite(values).all() or float(np.sum(np.abs(values)))*RULES['sample_step'] > math.radians(6): continue
                sag = np.abs(cross(q-q[0], chord))/extent
                if float(max(sag)) >= .4:
                    j = int(chosen[int(np.argmax(sag))])
                    add('near_straight_bend', sample['segment'][j], s[j], pts[j],
                        deviation=round(float(max(sag)), 5), window=w)
        # Approximate topology from error-bounded flattening; exact intersections
        # still require confirmation. No contour-count/design assumptions.
        poly = []
        for seg in contour:
            _, points = seg.flatten(); poly.extend(points[:-1])
        if closed and len(poly) >= 3:
            ring = LinearRing(poly)
            if not ring.is_simple:
                reason = explain_validity(Polygon(poly))
                import re
                numbers = re.search(r'\[([^\]]+)\]', reason)
                xy = np.fromstring(numbers[1], sep=' ') if numbers else pts[0]
                if len(xy) != 2: xy = pts[0]
                idx = int(np.argmin(np.linalg.norm(pts-xy, axis=1)))
                add('self_intersection', sample['segment'][idx], s[idx], xy, method='flattened polygon', reason=reason)
    # The stationary-root test can find the same zero from both coordinate axes.
    unique = {}
    for item in findings:
        unique[(item['kind'], item['segment'], item['s'], tuple(item['xy']))] = item
    return list(unique.values()), sample


def cluster(findings, samples):
    """Merge detector evidence along one contour, never across close branches."""
    groups = []
    for ci, sample in enumerate(samples):
        raw = sorted([r for r in findings if r['contour'] == ci], key=lambda r: r['s'])
        current = []
        for r in raw:
            if current and (r['s']-current[-1]['s'] > RULES['merge_arc_distance'] or r['s']-current[0]['s'] > 16):
                groups.append(current); current = []
            current.append(r)
        if current: groups.append(current)
        # Merge across the contour's start when the combined interval is small.
        own = [g for g in groups if g[0]['contour'] == ci]
        if len(own) > 1 and sample['length']-own[-1][0]['s']+own[0][-1]['s'] <= 16 and sample['length']-own[-1][-1]['s']+own[0][0]['s'] <= RULES['merge_arc_distance']:
            own[-1].extend(own[0]); groups.remove(own[0])
    return groups


def inspect_outline(contours, closed):
    findings, samples = [], []
    for ci, (contour, is_closed) in enumerate(zip(contours, closed)):
        raw, sample = inspect_contour(contour, is_closed)
        for item in raw: item['contour'] = ci
        findings.extend(raw); samples.append(sample)
    return findings, samples
