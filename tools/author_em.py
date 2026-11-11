#!/usr/bin/env python3
"""Reproduce 1.117 from the immutable 1.116 family and the author's SVG.

The SVG is the cubic master. TTF/WOFF2 use Cu2Qu(.1) and the TrueType grid;
CFF keeps the transformed original cubics at 16.16 precision. No smoothing.
"""
import copy, hashlib, io, json, sys, zipfile
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.pointPen import PointToSegmentPen, SegmentToPointPen
from fontTools.svgLib.path import parse_path
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.misc.timeTools import timestampSinceEpoch

MANIFEST = Path('data/italic-author-em/manifest.json')
NAME = 'uni043C'
TRANSFORM = (1/5.3, 0, 0, -1/5.3, -42.77/5.3, 516)

def config():
    return json.loads(MANIFEST.read_text())

@lru_cache(maxsize=6)
def baseline(style='Italic', fmt='ttf'):
    cfg = config(); raw = Path(cfg['baseline_archive']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == cfg['baseline_sha256']
    folder = 'webfonts' if fmt == 'woff2' else fmt
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return archive.read(f'VeryPeriSerif-1.116/fonts/{folder}/VeryPeriSerif-{style}.{fmt}')

def source_recording():
    cfg = config(); raw = Path(cfg['svg']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == cfg['svg_sha256']
    root = ET.fromstring(raw)
    assert root.attrib['viewBox'] == '0 0 2750 2783'
    assert len(root) == 1 and root[0].tag.endswith('}path')
    assert 'transform' not in root.attrib and 'transform' not in root[0].attrib
    pen = RecordingPen(); parse_path(root[0].attrib['d'], TransformPen(pen, TRANSFORM))
    return pen

def quadratic_glyph():
    pen = TTGlyphPen(None)
    source_recording().replay(ReverseContourPen(Cu2QuPen(pen, max_err=.1, all_quadratic=True)))
    return pen.glyph()

def accepted(font):
    if not font['post'].italicAngle or font['name'].getDebugName(5) != 'Version 1.117':
        return False
    glyph = quadratic_glyph(); glyph.recalcBounds(font['glyf'])
    if glyph.compile(font['glyf']) != font['glyf'][NAME].compile(font['glyf']):
        return False
    from italic_revision import sources
    for name, (master, advance) in sources().items():
        master.recalcBounds(font['glyf'])
        if master.compile(font['glyf']) != font['glyf'][name].compile(font['glyf']):
            return False
    return True

def verify_protected(font, style):
    old = TTFont(io.BytesIO(baseline(style)))
    assert font.getGlyphOrder() == old.getGlyphOrder()
    for name in old.getGlyphOrder():
        if style == 'Italic' and name == NAME:
            assert font['hmtx'][name][0] == old['hmtx'][name][0] == 523
            continue
        assert font['glyf'][name].compile(font['glyf']) == old['glyf'][name].compile(old['glyf']), name
        assert font['hmtx'][name] == old['hmtx'][name], name
    for tag in ('cmap','GSUB','GPOS','GDEF','STAT','meta','cvt ','fpgm','prep','gasp','OS/2'):
        if tag in old:
            assert font.getTableData(tag) == old.getTableData(tag), tag

def convert(src, dst):
    tt = TTFont(src); style = 'Italic' if tt['post'].italicAngle else 'Regular'
    verify_protected(tt, style)
    if style == 'Italic':
        assert accepted(tt)
    otf = TTFont(io.BytesIO(baseline(style,'otf'))); otf.recalcTimestamp = False
    for tag in ('name','hmtx'):
        otf[tag] = copy.deepcopy(tt[tag])
    for field in ('created','modified','fontRevision'):
        setattr(otf['head'], field, getattr(tt['head'], field))
    top = otf['CFF '].cff.topDictIndex[0]; top.version = '1.117'
    if style == 'Italic':
        original = top.CharStrings[NAME]
        pen = T2CharStringPen(523, None, roundTolerance=0)
        pen.round = lambda value: round(value*65536)/65536
        source_recording().replay(pen)
        top.CharStrings[NAME] = pen.getCharString(private=original.private, globalSubrs=original.globalSubrs)
    otf.save(dst)
    return dst

def main():
    cfg = config(); out = Path('build/release'); out.mkdir(parents=True, exist_ok=True)
    # Editable sources in font coordinates, regenerated from the untouched SVG.
    meta = SimpleNamespace(width=523, unicodes=[0x043C])
    cubic = writeGlyphToString(NAME, meta, lambda p: source_recording().replay(SegmentToPointPen(p)))
    (MANIFEST.parent/'uni043C.cubic.glif').write_text(cubic)
    quad = quadratic_glyph()
    quad_glif = writeGlyphToString(NAME, meta, lambda p: quad.drawPoints(p, None))
    (MANIFEST.parent/'uni043C.glif').write_text(quad_glif)
    for style in ('Regular','Italic'):
        font = TTFont(io.BytesIO(baseline(style))); font.recalcTimestamp = False
        if style == 'Italic':
            quad.recalcBounds(font['glyf']); font['glyf'][NAME] = quad
            font['hmtx'][NAME] = (523, quad.xMin)
        digest = hashlib.sha256(b''.join(font['glyf'][n].compile(font['glyf']) for n in font.getGlyphOrder())).hexdigest()[:12]
        for record in font['name'].names:
            if record.nameID == 3:
                record.string = f'1.117;VPER;VeryPeriSerif-{style};{digest}'
            elif record.nameID == 5:
                record.string = 'Version 1.117'
        font['head'].fontRevision = 1.117
        font['head'].modified = timestampSinceEpoch(1794355200)  # 2026-11-11 UTC
        verify_protected(font, style)
        ttf = out/f'VeryPeriSerif-{style}.ttf'; font.save(ttf)
        web = TTFont(ttf); web.recalcTimestamp = False; web.flavor = 'woff2'; web.save(ttf.with_suffix('.woff2'))
        convert(ttf, ttf.with_suffix('.otf'))
    from build_family import validate
    report = {'version':'1.117','source':str(MANIFEST),'checks':validate(out/'VeryPeriSerif-Regular.ttf',out/'VeryPeriSerif-Italic.ttf')}
    report['native_cyrillic_clones'] = cfg['native_cyrillic_clones']
    for style in ('Regular','Italic'):
        report[style.lower()] = {'file':f'VeryPeriSerif-{style}.ttf','version':'1.117',
            'sha256':hashlib.sha256((out/f'VeryPeriSerif-{style}.ttf').read_bytes()).hexdigest()}
    (out/'family-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    build_manifest = {'family':'Very Peri Serif','version':'1.117','method':'Pinned release delta from original author SVG',
        'baseline_archive':cfg['baseline_archive'],'baseline_sha256':cfg['baseline_sha256'],
        'source':cfg['svg'],'source_sha256':cfg['svg_sha256'],'mapping':cfg['mapping'],
        'changed_drawing':{'Italic':[NAME],'Regular':[]},'advance':523,
        'fonts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('VeryPeriSerif-*') if p.suffix in ('.ttf','.otf','.woff2')}}
    (out/'build-manifest.json').write_text(json.dumps(build_manifest,ensure_ascii=False,indent=2)+'\n')
    from build_regular_release import specimen
    release_cfg = json.loads(Path('data/params.json').read_text())['regular_release']
    specimen(out/'VeryPeriSerif-Regular.ttf',out/'specimen.pdf',release_cfg)
    print('Built 1.117: exact author SVG; only italic em drawing and its derived LSB change.')

if __name__ == '__main__':
    main()
