"""Widen the Cyrillic ghe flourishes while retaining the native diagonal stem."""
import math
import json
from pathlib import Path
from polish_outlines import contours_of, to_glyph
from family_finish import base_tables


def widened_body(font, delta=20, name='uni0433'):
    """Source recipe from unmodified 1.109: protect the stem, extend flourishes."""
    assert font['hmtx']['uni0433'][0] == 288, 'Use the original source, not an already widened font'
    points = contours_of(font['glyf'][name], font['glyf'])
    slope = math.tan(math.radians(13))
    def smooth(t):
        t = max(0, min(1, t))
        return t*t*(3-2*t)
    for contour in points:
        for point in contour:
            x, y, _ = point; u = x-slope*y
            extra = (-delta/2*smooth((52-u)/112) if u < 52 else
                     delta/2*smooth((u-118)/112) if u > 118 else 0)
            if name == 'uni0493' and 236 <= y <= 266:
                extra = 0  # Translate the accepted crossbar with its stem.
            point[0] = round(x+delta/2+extra)
    if name == 'uni0493':
        # Share the inner flourish curves exactly; retain the accepted terminal
        # caps, avoiding a full Boolean/quadratic roundtrip of the body.
        reference = contours_of(widened_body(font, delta), font['glyf'])[0]
        contour = points[0]
        for ya, yb in ((459,332),(47,174)):
            i = next(i for i,p in enumerate(reference) if p[2] and p[1] == ya)
            j = next(i for i,p in enumerate(reference) if p[2] and p[1] == yb)
            a = contour.index(reference[j]); b = contour.index(reference[i])
            assert a < b and i < j
            contour[a+1:b] = list(reversed(reference[i+1:j]))
    glyph = to_glyph(points)
    glyph.recalcBounds(font['glyf'])
    return glyph


def finish(font, native_aliases, anchor_info):
    """Adapt anchor placement and kerning classification to the reviewed sources."""
    cfg = json.loads(Path('data/params.json').read_text())['premium_review'].get('italic_ghe_width')
    if not cfg: return {}
    names = ('uni0433', 'uni0493'); dx = cfg['anchor_dx']
    for name in names:
        assert font['hmtx'][name][0] == cfg['advance'], ('Ghe width source missing', name)
    # It is now an authored Cyrillic outline, with contour-based kerning.
    # Native dotlessi and Serbian/Macedonian imacron remain protected.
    native_aliases.pop('uni0433', None)
    for table in base_tables(font):
        records = dict(zip(table.BaseCoverage.glyphs, table.BaseArray.BaseRecord))
        for name in names:
            assert name in records, ('Ghe anchors missing', name)
            for anchor in records[name].BaseAnchor:
                if anchor: anchor.XCoordinate += dx
            anchor_info[name] = {'donor': 'dotlessi', 'anchor_dx': dx,
                                 'reviewed_wider_cyrillic_body': True}
    return {'advance_before': cfg['advance']-cfg['delta'], 'advance_after': cfg['advance'],
            'anchor_dx': dx, 'independent_kerning': list(names),
            'native_local_and_printed_forms_preserved': True}
