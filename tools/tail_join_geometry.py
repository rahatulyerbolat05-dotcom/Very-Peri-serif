"""Quadratic intersection confirmation for the three pointed Italic tail joins.

Eliminate one parameter with a polynomial resultant, then refine actual Bezier
parameters. This does not depend on the flattened-polyline candidate detector.
"""
import itertools
import numpy as np
from numpy.polynomial import Polynomial as Poly
from contour_geometry import Segment

NAMES = ('uni0446', 'uni0449', 'uni04A3')
TIPS = {'uni0446': 376, 'uni0449': 609, 'uni04A3': 369}


def quadratic_intersections(first, second):
    assert first.degree == second.degree == 2
    # Translate before elimination to keep coefficients well conditioned.
    a = first.points-first.points[0]; b = second.points-first.points[0]
    c2 = a[0]-2*a[1]+a[2]; c1 = 2*(a[1]-a[0])
    bx = [Poly([b[0, axis], 2*(b[1, axis]-b[0, axis]),
                b[0, axis]-2*b[1, axis]+b[2, axis]]) for axis in (0, 1)]
    zero = Poly([0.])
    x = [Poly([c2[0]]), Poly([c1[0]]), -bx[0]]
    y = [Poly([c2[1]]), Poly([c1[1]]), -bx[1]]
    matrix = [[*x, zero], [zero, *x], [*y, zero], [zero, *y]]
    resultant = zero
    for perm in itertools.permutations(range(4)):
        inversions = sum(perm[i] > perm[j] for i in range(4) for j in range(i+1, 4))
        value = Poly([(-1.)**inversions])
        for i, j in enumerate(perm): value *= matrix[i][j]
        resultant += value
    coefficients = resultant.coef
    magnitude = max(abs(coefficients), default=0.)
    if magnitude < 1e-12:
        raise ValueError('Coincident/degenerate conics require a different intersection test')
    coefficients = np.trim_zeros(np.where(abs(coefficients) < magnitude*1e-12, 0., coefficients), 'b')
    result = []
    for u in Poly(coefficients).roots():
        if abs(u.imag) > 1e-7 or not -1e-7 <= u.real <= 1+1e-7: continue
        u = float(u.real)
        for axis in (0, 1):
            equation = np.trim_zeros(np.array([c2[axis], c1[axis], -bx[axis](u)]), 'f')
            for t in np.roots(equation) if len(equation) > 1 else []:
                if abs(t.imag) > 1e-6 or not -1e-6 <= t.real <= 1+1e-6: continue
                z = np.array([float(t.real), u])
                for _ in range(20):
                    residual = first.evaluate(z[0])-second.evaluate(z[1])
                    if np.linalg.norm(residual) < 1e-12: break
                    jacobian = np.column_stack((first.evaluate(z[0], 1), -second.evaluate(z[1], 1)))
                    if abs(np.linalg.det(jacobian)) < 1e-12: break
                    z -= np.linalg.solve(jacobian, residual)
                error = float(np.linalg.norm(first.evaluate(z[0])-second.evaluate(z[1])))
                if error < 1e-8 and np.all(z >= -1e-7) and np.all(z <= 1+1e-7):
                    if any(np.linalg.norm(z-r['parameters']) < 1e-6 for r in result): continue
                    result.append({'parameters': z.tolist(), 'xy': first.evaluate(z[0]).tolist(), 'residual': error})
    return sorted(result, key=lambda r: r['parameters'])


def join_pair(contour, name, revised=False):
    tip = (TIPS[name]-1, -1) if revised else (TIPS[name], 0)
    i = next(i for i, s in enumerate(contour) if np.linalg.norm(s.points[0]-tip) < .001)
    return i-1, i


def nonendpoint_intersections(first, second):
    return [r for r in quadratic_intersections(first, second)
            if not (abs(r['parameters'][0]-1) < 1e-6 and abs(r['parameters'][1]) < 1e-6)]
