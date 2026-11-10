#!/usr/bin/env python3
"""Draw a Cyrillic italic ya ear from the native a/q shoulder, on frozen 1.115.

Only the upper outer bowl/stem junction is replaced. The counter, the leg,
the ball, the accepted inner junction and the complete exit retain their nodes.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

os.environ.setdefault('MPLCONFIGDIR', '/tmp/very-peri-mpl')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import readGlyphFromString
from types import SimpleNamespace

BASELINE = '0330c598b690e4e9ddc6aec53a57218bba476035'
SOURCE = Path('data/italic-ya-terminal/uni044F.glif')
OUT = Path('build/ya-terminal')
PREVIEW = OUT/'ya-terminal.png'
NAME = 'uni044F'


def frozen(path):
    return subprocess.check_output(['git', 'show', BASELINE+':'+path])


def build():
    original = frozen('data/curve-finish/Italic/uni044F.glif')
    root = ET.fromstring(original)
    contour = root.find('outline/contour')
    points = list(contour)
    xy = lambda p: tuple(int(p.attrib[k]) for k in ('x', 'y'))
    a = next(i for i, p in enumerate(points) if xy(p) == (372, 513))
    b = next(i for i, p in enumerate(points) if xy(p) == (229, 516))
    assert [xy(p) for p in points[a:b+1]] == [(372,513),(305,513),(290,513),(260,516),(229,516)]
    # Native q/a's exact *sequence of movements*, adapted to the existing bowl
    # and stem: bowl crown -> shoulder -> saddle -> rising rounded ear -> stem.
    # Transverse mapping: native q x290..419 -> ya x229..368 (139/129).
    # Heights and native shoulder/ear depths are unscaled. The final control
    # follows the ya's existing straight stem, avoiding a new tangent kink.
    native = [(290,516,1),(309,516,0),(343,501,0),(354,485,1),
              (360,476,0),(366,476,1),(372,476,0),(378,485,1),
              (389,501,0),(403,510,0),(409,510,1),(422,510,0),(419,496,1)]
    adapted = [(round(229+(x-290)*139/129), y, on) for x,y,on in native]
    # Outgoing derivative of the final quadratic follows (99,-413), matching
    # the original ya stem rather than inheriting the native q's small angle.
    adapted[-2] = (371,510,0)
    # Integral grid adaptation at the left saddle shoulder: preserve the same
    # (-6,9) tangent on both sides of (298,485), instead of a 3.18-degree kink.
    adapted[2] = (286,503,0)
    replacement = list(reversed(adapted))
    for p in points[a:b+1]:
        contour.remove(p)
    for offset, (x,y,on) in enumerate(replacement):
        attrs = {'x':str(x), 'y':str(y)}
        if on: attrs['type'] = 'line' if offset == 0 else 'qcurve'
        point = ET.Element('point', attrs); point.tail = '\n      '
        contour.insert(a+offset,point)
    raw = ET.tostring(root, encoding='utf-8', xml_declaration=True)+b'\n'
    raw = raw.replace(b"encoding='utf-8'",b"encoding='UTF-8'").replace(b' />',b'/>')
    SOURCE.parent.mkdir(parents=True,exist_ok=True); SOURCE.write_bytes(raw)
    pen = TTGlyphPointPen(None); meta = SimpleNamespace()
    readGlyphFromString(raw.decode(),meta,pen)
    glyph = pen.glyph()
    baseline = TTFont(io.BytesIO(frozen('fonts/ttf/VeryPeriSerif-Italic.ttf')))
    new = copy.deepcopy(baseline); new.recalcTimestamp = False
    new['glyf'][NAME] = glyph; glyph.recalcBounds(new['glyf'])
    assert [glyph.xMin,glyph.yMin,glyph.xMax,glyph.yMax] == [-12,-9,401,516]
    assert round(meta.width) == new['hmtx'][NAME][0] == 413
    assert len(glyph.endPtsOfContours) == 2
    # Preserve all original nodes other than the five declared upper nodes.
    oldco, oldend, oldflags = baseline['glyf'][NAME].getCoordinates(baseline['glyf'])
    newco, newend, newflags = glyph.getCoordinates(new['glyf'])
    oldrows = [(tuple(p),int(f&1)) for p,f in zip(oldco,oldflags)]
    newrows = [(tuple(p),int(f&1)) for p,f in zip(newco,newflags)]
    assert oldrows[:11] == newrows[:11]
    assert oldrows[16:] == newrows[24:]
    OUT.mkdir(parents=True,exist_ok=True)
    oldpath = OUT/'before.ttf'; oldpath.write_bytes(frozen('fonts/ttf/VeryPeriSerif-Italic.ttf'))
    path = OUT/'after.ttf'; new.save(path)
    saved = TTFont(path)
    changed = [n for n in baseline.getGlyphOrder()
               if baseline['glyf'][n].compile(baseline['glyf']) != saved['glyf'][n].compile(saved['glyf'])]
    assert changed == [NAME]
    for tag in ('hmtx','cmap','GSUB','GPOS','GDEF','STAT','cvt ','fpgm','prep'):
        if tag in baseline:
            assert baseline.getTableData(tag) == saved.getTableData(tag), tag
    from contour_geometry import read_outline, inspect_outline
    from shapely.geometry import Polygon
    curves,closed = read_outline(saved,NAME)
    findings,_ = inspect_outline(curves,closed)
    upper_corners = [r for r in findings if r['kind']=='tangent_break' and r.get('xy',[0,0])[1]>430]
    assert not upper_corners, upper_corners
    rings = []
    for curve in curves:
        ring = []
        for segment in curve:
            ring.extend(segment.flatten()[1][:-1].tolist())
        rings.append(ring)
    assert Polygon(rings[0],rings[1:]).is_valid, 'New contour intersection'
    report = {'baseline':BASELINE,'glyph':NAME,'advance':413,'bounds':[-12,-9,401,516],
              'source_sha256':hashlib.sha256(raw).hexdigest(),
              'donor':'Instrument Serif Italic native a/q upper shoulder and ear',
              'donor_x_map':'229 + (x - 290) * 139 / 129; integral TrueType grid',
              'y_map':'unchanged', 'substantive_edit_y_min':476,
              'stem_endpoint_before':[372,513], 'stem_endpoint_after':[368,496],
              'maximum_straight_edge_displacement_below_496':0.076,
              'changed_glyphs':changed,'upper_tangent_break_candidates':upper_corners,
              'valid_closed_polygon_with_counter':True,
              'protected':'counter, outer bowl below crown, lower leg, ball and exit nodes exact'}
    (OUT/'construction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return oldpath,path


def proof(before,after):
    from family_proof import Proof,page
    from curve_finish_proof import crop
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    old,new = Proof(before),Proof(after)
    fig,axes = plt.subplots(1,4,figsize=(16,7),facecolor='#f5f2ec')
    crop(axes[0],old.font,NAME,(195,260),'1.115',300)
    crop(axes[1],new.font,NAME,(195,260),'Native a/q ear',300)
    crop(axes[2],old.font,NAME,(315,487),'Before: flat wedge',94)
    crop(axes[3],new.font,NAME,(315,487),'After: shoulder + rising ear',94)
    fig.tight_layout();fig.savefig(PREVIEW,dpi=130)
    fig.savefig(OUT/'ya-terminal.svg',metadata={'Date':'2026-11-10'})
    with PdfPages(OUT/'ya-terminal.pdf') as pdf:
        pdf.savefig(fig)
        fig2,ax=page('Italic ya: original / revised / native a q',1400,1000)
        for i,(label,p) in enumerate((('1.115',old),('a/q ear',new))):
            y=130+i*370;ax.text(50,y,label,fontsize=16,color='#69656a')
            for j,text in enumerate(('я · яя · моя · земля','яркий · маяк · друзья','мия · аq · я́ · я̀')):
                p.line(ax,text,50,y+90+j*95,105)
        old.line(ax,'a q p',950,430,150)
        pdf.savefig(fig2);fig2.savefig(OUT/'words.png',dpi=115)
        plt.close(fig2)
    plt.close(fig)


if __name__ == '__main__':
    proof(*build())
    print(SOURCE)
    print(PREVIEW)
