#!/usr/bin/env python3
"""Independent serialized-font acceptance of ss10 and preservation of 1.113."""
import argparse
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from weakref import WeakKeyDictionary

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ots
import uharfbuzz as hb
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import readGlyphFromString
from italic_el_alternate import NAME, SOURCE, RECORD, legacy_view,unpromoted_view
from build_draft_font import native_kern
from check_tail_joins import path_in
from contour_geometry import read_outline, inspect_outline
from ttf2otf import exact_cubic_error
from contour_contacts import Auditor

_SHAPERS=WeakKeyDictionary()


def shape(font, text, features=None, language='ru'):
    hf=_SHAPERS.get(font)
    if hf is None:
        source=font
        if font.flavor:
            source=copy.deepcopy(font)
            source.flavor=None  # decode the container once for all feature modes
        buffer=io.BytesIO();source.save(buffer)
        hf=hb.Font(hb.Face(buffer.getvalue()));_SHAPERS[font]=hf
    b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); b.language = language
    hb.shape(hf, b, features or {})
    return [(font.getGlyphName(g.codepoint),p.x_advance,p.x_offset,p.y_offset)
            for g,p in zip(b.glyph_infos,b.glyph_positions)]


def old_font(style, fmt):
    folder = 'webfonts' if fmt == 'woff2' else fmt
    raw = subprocess.check_output(['git','show',f'v1.113:fonts/{folder}/VeryPeriSerif-{style}.{fmt}'])
    return TTFont(io.BytesIO(raw))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('build/release'))
    ap.add_argument('--formats',default='ttf,otf,woff2')
    args = ap.parse_args()
    version = json.loads(Path('data/params.json').read_text())['regular_release']['version']
    record = json.loads(RECORD.read_text()); checks = 0; report = {}
    def ck(value, label):
        nonlocal checks
        assert value, label
        checks += 1
    for style in ('Regular','Italic'):
        for fmt in args.formats.split(','):
            path = path_in(args.root,style,fmt); current = unpromoted_view(TTFont(path))
            current.recalcTimestamp = False
            old = old_font(style,fmt); old.recalcTimestamp = False
            base = legacy_view(current)
            ck(base.getGlyphOrder() == old.getGlyphOrder(), (style,fmt,'existing glyph order'))
            ck(current.getGlyphOrder() == old.getGlyphOrder()+([NAME] if style=='Italic' else []),
               (style,fmt,'only one unencoded glyph added'))
            for tag in old.keys():
                if tag not in ('GlyphOrder','head','name','glyf','loca','CFF '):
                    ck(base.getTableData(tag) == old.getTableData(tag), (style,fmt,'unchanged base table',tag))
            if fmt == 'otf':
                a,b=[f['CFF '].cff.topDictIndex[0].CharStrings for f in (old,current)]
                for n in old.getGlyphOrder():
                    a[n].decompile(); b[n].decompile()
                    ck(a[n].program == b[n].program,(style,fmt,'retained CFF',n))
            else:
                for n in old.getGlyphOrder():
                    ck(old['glyf'][n].compile(old['glyf']) == current['glyf'][n].compile(current['glyf']),
                       (style,fmt,'retained outline and hints',n))
            ck(current.getBestCmap() == old.getBestCmap(), (style,fmt,'unchanged Unicode mapping'))
            ck(current['name'].getDebugName(5) == 'Version '+version,(style,fmt,'current version'))
            ck(ots.sanitize(str(path),'/dev/null',capture_output=True).returncode == 0,(style,fmt,'OTS'))
            row={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'glyphs':len(current.getGlyphOrder())}
            if style == 'Italic':
                ck(current['hmtx'][NAME] == (392,10),(fmt,'approved alternate metrics'))
                ck(NAME not in current.getBestCmap().values(),(fmt,'alternate is unencoded'))
                if fmt != 'otf':
                    pen=TTGlyphPointPen(None)
                    readGlyphFromString(SOURCE.read_text(),SimpleNamespace(),pen)
                    ck(current['glyf'][NAME].getCoordinates(current['glyf']) == pen.glyph().getCoordinates(current['glyf']),
                       (fmt,'exact approved GLIF'))
                else:
                    ttf=unpromoted_view(TTFont(path_in(args.root,style,'ttf')))
                    ck(exact_cubic_error(ttf,current,NAME)<.002,'exact CFF controls')
                diag,_=inspect_outline(*read_outline(current,NAME))
                forbidden={'tangent_break','self_intersection','zero_segment','stationary_point','short_segment','transverse_step'}
                ck(not any(p['kind'] in forbidden for p in diag),(fmt,'no seam, corner or topology defect'))
                ck(current['name'].getDebugName(record['feature_name_id']) == 'Cyrillic el: rounded arch and exit',
                   (fmt,'named stylistic set'))
                ck(current['GDEF'].table.GlyphClassDef.classDefs[NAME] == 1,(fmt,'alternate is a mark base'))
                for language in ('ru','kk','sr','mk'):
                    ck(shape(current,'л',{'ss10':True},language)[0][0] == NAME,(fmt,language,'ss10 active'))
                    ck(shape(current,'л',{'ss10':False},language) == shape(old,'л',language=language),
                       (fmt,language,'default el unchanged'))
                    accented=shape(current,'л́',{'ss10':True},language)
                    off=shape(current,'л́',{'ss10':True,'mark':False,'mkmk':False},language)
                    ck(accented[0][0] == NAME and accented[-1][1] == 0 and accented != off,
                       (fmt,language,'stress attaches to alternate'))
                ck(shape(current,'л',{'aalt':1})[0][0] == NAME,(fmt,'available in alternates menu'))
                # Every pre-existing set combination remains compatible with ss10.
                for flags in itertools.product((0,1),repeat=6):
                    mode={f'ss{i+1:02d}':v for i,v in enumerate(flags)}
                    mode['ss10']=1
                    ck(shape(current,'л',mode)[0][0] == NAME,(fmt,'set combination',flags))
                for text in ('лилия · аллея · люблю','гүл · әлем · ләззат','office affine AVATAR','я г ғ ч щ ң'):
                    ck(shape(current,text) == shape(old,text),(fmt,'default shaping preserved',text))
                # Directly access every visible glyph through a temporary cmap,
                # including unencoded alternates, then exercise the actual GPOS.
                if fmt == 'ttf':
                    probe=copy.deepcopy(current); order=probe.getGlyphOrder()
                    for table in probe['cmap'].tables:
                        if table.isUnicode():
                            table.cmap.update({0xE000+i:n for i,n in enumerate(order)})
                    buf=io.BytesIO();probe.save(buf);hf=hb.Font(hb.Face(buf.getvalue()))
                    auditor=Auditor(current); pairs=0
                    visible=[n for n in order if current['hmtx'][n][0]>0 and current['glyf'][n].numberOfContours]
                    for a,b in sorted({(NAME,n) for n in visible}|{(n,NAME) for n in visible}):
                        text=''.join(chr(0xE000+order.index(n)) for n in (a,b))
                        def total(on):
                            buffer=hb.Buffer();buffer.add_str(text);buffer.direction='ltr';buffer.script='cyrl';buffer.language='ru'
                            hb.shape(hf,buffer,{'kern':on})
                            return sum(p.x_advance for p in buffer.glyph_positions)
                        kern=total(True)-total(False)
                        ck(kern == native_kern(current,a,b),('actual alternate GPOS',a,b))
                        auditor.check(a,b,current['hmtx'][a][0]+kern,(a,b))
                        pairs+=1
                    row['all_visible_pairs_checked']=pairs
                row['geometry_candidates']=diag
            else:
                ck(shape(current,'л',{'ss10':1}) == shape(current,'л'),(fmt,'Regular unaffected'))
            report[style+'/'+fmt]=row
    result={'version':version,'baseline':'v1.113','passed':checks,'failed':0,'fonts':report,
            'scope':'Arched/previous el sources and preserved base layout, normalized to pre-promotion identities; actual default promotion is independently checked by check_el_default.py. Not whole-family optical acceptance.'}
    dest=Path(f'docs/qa/el-alternate-{version}.json')
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':checks,'failed':0,'report':str(dest)}))


if __name__ == '__main__':
    main()
