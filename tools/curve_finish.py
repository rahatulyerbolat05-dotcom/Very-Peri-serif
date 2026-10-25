#!/usr/bin/env python3
"""Install explicitly reviewed curve sources after provisional generation.

GLIFs use final font coordinates, after spacing and grid polish. Installing them
before kerning keeps contour profiles and collision checks on the actual shape.
Native Instrument glyphs and hint programs are never replaced.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import TTFont

MANIFEST=Path('data/curve-finish/manifest.json')


def check_input_metrics(actual, record):
    # Historic provisional generators can quantize a control-point box one
    # unit differently after a Regular source update. Accept only explicitly
    # recorded input pairs; the reviewed GLIF and final metrics stay exact.
    incoming=record.get('input_advance_and_lsb',record['advance_and_lsb'])
    return list(actual) in [incoming]+record.get('additional_input_advance_and_lsb',[])


def load_source(name, record):
    path=Path(record['path']);raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==record['sha256'],('Curve source hash',name)
    pen=TTGlyphPointPen(None);meta=SimpleNamespace()
    readGlyphFromString(raw.decode(),meta,pen)
    glyph=pen.glyph()
    assert round(meta.width)==record['advance_and_lsb'][0],('Curve source advance',name)
    return glyph


def apply(font, style):
    if not MANIFEST.exists():return {}
    records=json.loads(MANIFEST.read_text())['glyphs'][style]
    native=TTFont(f'reference/instrument-serif/fonts/ttf/InstrumentSerif-{style}.ttf')
    result={}
    for name,record in records.items():
        assert name in font['glyf'],('Missing generated curve base',style,name)
        assert name not in native.getGlyphOrder(),('Native glyph must stay unchanged',name)
        assert check_input_metrics(font['hmtx'][name],record),('Curve finish metrics',style,name)
        g=load_source(name,record);g.recalcBounds(font['glyf'])
        assert g.numberOfContours==record['contours'],('Curve source contour count',name)
        assert [g.xMin,g.yMin,g.xMax,g.yMax]==record['bounds'],('Curve source bounds',name)
        font['glyf'][name]=g
        font['hmtx'][name]=tuple(record['advance_and_lsb'])
        result[name]={'path':record['path'],'sha256':record['sha256'],'reviewed_outline':True}
    return result
