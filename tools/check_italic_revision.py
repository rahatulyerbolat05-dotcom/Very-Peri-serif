#!/usr/bin/env python3
"""Independent 1.116 acceptance against actual published 1.115 binaries.

Only the author-accepted upper crowns and я ear may change. м and every original
spacing/mark/layout table are protected directly; no legacy projection is used.
Run for build outputs or published fonts: python -I tools/check_italic_revision.py
  --root build/release   (or --root fonts).
"""
import argparse
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
from functools import lru_cache
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import ots
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ufoLib.glifLib import readGlyphFromString
from shapely.geometry import LineString,box
from shapely.ops import unary_union
from contour_geometry import read_outline,inspect_outline
from ttf2otf import exact_cubic_error

BASELINE='0330c598b690e4e9ddc6aec53a57218bba476035'
VERSION='1.116'
CAPS={'uni043D','uni0439','uni0446','uni044B','uni0448','uni0449',
      'uni04A3','uni04AF','uni04B1','uni0436','uni0447'}
ALLOWED=CAPS|{'uni044F'}
CFF_ALLOWED=ALLOWED|{'uni0442.srb'}  # unchanged TTF composite of the revised ш + native macron
PROTECTED=('cmap','GSUB','GPOS','GDEF','STAT','meta','cvt ','fpgm','prep','gasp','OS/2','hhea','post')
TOPOLOGY={'self_intersection','zero_segment','disconnected','open_contour','undefined_tangent','interior_stationary'}


def frozen(style,fmt):
    folder='webfonts' if fmt=='woff2' else fmt
    return subprocess.check_output(['git','show',f'{BASELINE}:fonts/{folder}/VeryPeriSerif-{style}.{fmt}'])


def output_path(root,style,fmt):
    filename=f'VeryPeriSerif-{style}.{fmt}'
    direct=root/filename
    folder='webfonts' if fmt=='woff2' else fmt
    return direct if direct.exists() else root/folder/filename


@lru_cache(maxsize=12)
def shaping_font(raw):
    if raw[:4] in (b'wOF2',b'wOFF'):
        # Decode the actual webfont, rather than feeding an unsupported WOFF2
        # container directly into HarfBuzz. Tables are compared separately.
        decoded=TTFont(io.BytesIO(raw));decoded.flavor=None;decoded.recalcTimestamp=False
        stream=io.BytesIO();decoded.save(stream);raw=stream.getvalue()
    font=hb.Font(hb.Face(raw));hb.ot_font_set_funcs(font)
    return font


def shape(raw,text,features=None,language='ru'):
    font=shaping_font(raw);buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties();buf.language=language
    hb.shape(font,buf,features or {})
    return [(g.codepoint,p.x_advance,p.y_advance,p.x_offset,p.y_offset)
            for g,p in zip(buf.glyph_infos,buf.glyph_positions)]


def shape_cases():
    texts=['н ң й ц ш щ ы ү ұ ж ч м я','мама · мир · молоко · мягкий · имя · земля',
           'қаңтар · мың · үміт · ұмыт · қиял · әлем','м́ я́ н́ ш́ ң́ ы́ й́ ү́ ұ́',
           'я̈́ м̈́ · н̀ ң̄ ш̆','office affine final AVATAR','Нн Мм Яя Тт Пп Ии',
           'л л́ л̀ л̄ · луна · аллея','0123456789 ₸ ₽ № 12 500','б г д п т',
           '№м Ғм қм Xм Хм Kм Км Ķм']
    for text in texts:
        for lang in ('ru','kk'):yield text,{},lang
    for text in texts[:5]+texts[-4:]:
        for bits in itertools.product((0,1),repeat=6):
            yield text,{f'ss{i+1:02}':v for i,v in enumerate(bits)},'ru'
    for lang in ('sr','mk'):
        for text in texts:yield text,{},lang
    for text in texts:
        for features in ({'kern':0},{'liga':0},{'tnum':1},{'ss10':1}):yield text,features,'ru'


def cropped_outline(contours,ceiling=430.):
    lines=[]
    for contour in contours:
        for segment in contour:
            _,points=segment.flatten(.005)
            crop=LineString(points).intersection(box(-5000,-5000,5000,ceiling))
            if not crop.is_empty:lines.append(crop)
    return unary_union(lines)


def geometry(font,old,name):
    curves,closed=read_outline(font,name);diag,_=inspect_outline(curves,closed)
    previous,pc=read_outline(old,name);before,_=inspect_outline(previous,pc)
    oldcorners=[r for r in before if r['kind']=='tangent_break']
    introduced=[]
    for finding in diag:
        if finding['kind']!='tangent_break':continue
        inherited=any(np.linalg.norm(np.asarray(finding['xy'])-r['xy'])<.05 and
                      abs(finding['metrics']['degrees']-r['metrics']['degrees'])<.05 for r in oldcorners)
        if not inherited:introduced.append(finding)
    return {'contours':len(curves),'closed':all(closed),
            'topology_candidates':[r for r in diag if r['kind'] in TOPOLOGY],
            'introduced_tangent_breaks':introduced,
            'below_y430_hausdorff':float(cropped_outline(curves).hausdorff_distance(cropped_outline(previous))),
            'diagnostic_candidates':diag}


def name_records(font):
    return sorted((r.nameID,r.platformID,r.platEncID,r.langID,r.toUnicode())
                  for r in font['name'].names if r.nameID not in (3,5))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('build/release'))
    ap.add_argument('--report',type=Path,default=Path('docs/qa/italic-revision-1.116.json'))
    args=ap.parse_args();passed=0;failures=[];warnings=[]
    def ck(ok,label):
        nonlocal passed
        if ok:passed+=1
        else:failures.append(label)
    manifest=json.loads(Path('data/italic-revision-1.116.json').read_text())
    ck(manifest['baseline_commit']==BASELINE,'frozen baseline commit')
    ck(manifest['version']==VERSION,'accepted release version')
    records=manifest['glyphs'];ck(set(records)==ALLOWED,{'source_glyph_set':list(records)})
    for name,record in records.items():
        ck(hashlib.sha256(Path(record['path']).read_bytes()).hexdigest()==record['sha256'],{'source_hash':name})
    report={'release':VERSION,'baseline_version':'1.115','baseline_commit':BASELINE,
            'root':str(args.root),'allowed_italic_glyphs':sorted(ALLOWED),
            'allowed_italic_CFF_glyphs':sorted(CFF_ALLOWED),
            'accepted_sources':records,
            'protected_em':'uni043C outline, hints, advance, bearings and all original kerning retained exactly',
            'fonts':{}}
    cases=list(shape_cases())
    for style in ('Regular','Italic'):
        oldraw={fmt:frozen(style,fmt) for fmt in ('ttf','otf','woff2')}
        baseline={fmt:TTFont(io.BytesIO(raw)) for fmt,raw in oldraw.items()}
        paths={fmt:output_path(args.root,style,fmt) for fmt in baseline}
        missing=[str(p) for p in paths.values() if not p.exists()]
        if missing:failures.append({'style':style,'missing_outputs':missing});continue
        fonts={fmt:TTFont(path) for fmt,path in paths.items()};ttf=fonts['ttf'];oldtt=baseline['ttf']
        ck(ttf.getGlyphOrder()==oldtt.getGlyphOrder(),{'style':style,'glyph_order':False})
        changed=[]
        for name in oldtt.getGlyphOrder():
            same=ttf['glyf'][name].compile(ttf['glyf'])==oldtt['glyf'][name].compile(oldtt['glyf'])
            if not same:changed.append(name)
            ck(same or style=='Italic' and name in ALLOWED,{'style':style,'unexpected_glyph_or_hint_change':name})
        ck(set(changed)==(ALLOWED if style=='Italic' else set()),{'style':style,'changed_glyphs':changed})
        if style=='Italic':
            for name,record in records.items():
                pen=TTGlyphPointPen(None);meta=SimpleNamespace()
                readGlyphFromString(Path(record['path']).read_text(),meta,pen)
                source=pen.glyph();source.recalcBounds(ttf['glyf'])
                ck(round(meta.width)==ttf['hmtx'][name][0],{'source_width':name})
                ck(source.compile(ttf['glyf'])==ttf['glyf'][name].compile(ttf['glyf']),{'exact_accepted_master':name})
        expected_shapes=[shape(oldraw['ttf'],*case) for case in cases]
        for fmt,font in fonts.items():
            print(f'Checking {style}/{fmt}',flush=True)
            path=paths[fmt];base=baseline[fmt];raw=path.read_bytes()
            row={'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'baseline_sha256':hashlib.sha256(oldraw[fmt]).hexdigest(),'changed_glyphs':changed if fmt!='otf' else [],'glyphs':{}}
            report['fonts'][style+'/'+fmt]=row
            ck(font.getGlyphOrder()==base.getGlyphOrder(),{'style':style,'format':fmt,'glyph_order':False})
            ck(font['hmtx'].metrics==base['hmtx'].metrics,{'style':style,'format':fmt,'hmtx_changed':False})
            ck(font.getBestCmap()==base.getBestCmap(),{'style':style,'format':fmt,'cmap_changed':False})
            ck(name_records(font)==name_records(base),{'style':style,'format':fmt,'non_version_names_changed':False})
            ck(font['name'].getDebugName(5)=='Version '+VERSION,{'style':style,'format':fmt,'version_name':font['name'].getDebugName(5)})
            ck(abs(font['head'].fontRevision-float(VERSION))<.00001,{'style':style,'format':fmt,'head_version':font['head'].fontRevision})
            ck(font['head'].macStyle==base['head'].macStyle,{'style':style,'format':fmt,'style_flags':False})
            for tag in PROTECTED:
                ck((tag in font)==(tag in base),{'style':style,'format':fmt,'table_presence':tag})
                if tag in font and tag in base:
                    ck(font.getTableData(tag)==base.getTableData(tag),{'style':style,'format':fmt,'protected_table_changed':tag})
            ots_result=ots.sanitize(str(path),os.devnull,capture_output=True)
            row['ots_returncode']=ots_result.returncode
            ck(ots_result.returncode==0,{'style':style,'format':fmt,'OTS':str(ots_result.stderr)})
            shape_failures=[]
            for case,expected in zip(cases,expected_shapes):
                actual=shape(raw,*case)
                if actual!=expected:shape_failures.append({'text':case[0],'features':case[1],'language':case[2]})
            row['shaping_cases']=len(cases);row['shaping_cases_changed']=len(shape_failures)
            ck(not shape_failures,{'style':style,'format':fmt,'shaping_changed':shape_failures[:15]})
            if fmt=='woff2':
                for tag in ('glyf','hmtx','cmap','GSUB','GPOS','GDEF','name'):
                    ck(font.getTableData(tag)==ttf.getTableData(tag),{'style':style,'WOFF2_roundtrip':tag})
            if fmt=='otf':
                cff=font['CFF '].cff;top=cff.topDictIndex[0]
                ck(cff.fontNames==base['CFF '].cff.fontNames,{'style':style,'CFF_PostScript_names':False})
                ck(top.FamilyName==base['CFF '].cff.topDictIndex[0].FamilyName and top.FullName==base['CFF '].cff.topDictIndex[0].FullName,{'style':style,'CFF_family_names':False})
                ck(top.version==VERSION,{'style':style,'CFF_version':top.version})
                oldcs=base['CFF '].cff.topDictIndex[0].CharStrings;cs=top.CharStrings;cffchanged=[]
                for name in base.getGlyphOrder():
                    oldcs[name].decompile();cs[name].decompile();same=oldcs[name].program==cs[name].program
                    if not same:cffchanged.append(name)
                    ck(same or style=='Italic' and name in CFF_ALLOWED,{'style':style,'unexpected_CFF_program_change':name})
                ck(set(cffchanged)==(CFF_ALLOWED if style=='Italic' else set()),{'style':style,'changed_CFF_set':cffchanged})
                row['changed_glyphs']=cffchanged
                if style=='Italic':
                    ck(ttf['glyf']['uni0442.srb'].getComponentNames(ttf['glyf'])==['uni0448','uni0304'],
                       'Serbian te remains the original sha/macron composite')
                    error=exact_cubic_error(ttf,font,'uni0442.srb')
                    row['derived_composite_exact_CFF_error']={'uni0442.srb':error}
                    ck(error<.002,{'derived_glyph':'uni0442.srb','exact_CFF_error':error})
            if style=='Italic':
                for name in sorted(ALLOWED):
                    print('  Geometry',name,flush=True)
                    geo=geometry(font,base,name);row['glyphs'][name]=geo
                    ck(geo['closed'],{'format':fmt,'open_glyph':name})
                    ck(not geo['topology_candidates'],{'format':fmt,'glyph':name,'topology':geo['topology_candidates']})
                    upper=[r for r in geo['introduced_tangent_breaks'] if r['xy'][1]>=450 and r['metrics']['degrees']>2]
                    ck(not upper,{'format':fmt,'glyph':name,'new_upper_corners':upper})
                    ck(geo['below_y430_hausdorff']<.8,{'format':fmt,'glyph':name,'below430_drift':geo['below_y430_hausdorff']})
                    if fmt=='otf':
                        error=exact_cubic_error(ttf,font,name);geo['exact_cubic_control_error']=error
                        ck(error<.002,{'glyph':name,'exact_CFF_error':error})
    report.update(passed=passed,failed=len(failures),failures=failures,warnings=warnings,
                  optical_status='Only the author-selected crowns and ya ear are in this revision; global optical audit remains separate.')
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':passed,'failed':len(failures),'warnings':len(warnings),'report':str(args.report)}))
    for failure in failures[:25]:print('FAIL',failure)
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
