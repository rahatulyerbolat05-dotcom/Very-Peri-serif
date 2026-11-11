#!/usr/bin/env python3
"""Independent final-file checks for the author's original Vector.svg em.

The source SVG and immutable 1.116 archive are pinned. Only Italic uni043C and
its left bearing may change; version identity is checked separately. Contour
findings are diagnostics, never permission to redraw the author's source.
"""
import argparse
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import ots
import pathops
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.svgLib.path import parse_path
from build_draft_font import native_kern
from contour_geometry import OutlinePen, read_outline, inspect_outline
from ttf2otf import nearest

ARCHIVE = Path('dist/VeryPeriSerif-1.116.zip')
ARCHIVE_SHA = 'ea93f22b17b3faf3e3531c3e8371d9b136144c82a4d1c77b1d519514ea3e8ef4'
SOURCE = Path('data/italic-author-em/Vector.svg')
SOURCE_SHA = '14bcccb7ea410050586e6ddc39e57e085717d28c162fa8a8a639d4a91f48c6c8'
EM = 'uni043C'
VERSION = '1.117'
TOPOLOGY = {'self_intersection', 'zero_segment', 'disconnected', 'open_contour', 'undefined_tangent', 'interior_stationary'}

def sha(raw): return hashlib.sha256(raw).hexdigest()

def source_recording():
    assert sha(SOURCE.read_bytes()) == SOURCE_SHA, 'Original uploaded SVG hash'
    root=ET.fromstring(SOURCE.read_bytes())
    paths=list(root.iter('{http://www.w3.org/2000/svg}path'))
    assert len(paths)==1 and not any('transform' in e.attrib for e in root.iter())
    pen=RecordingPen()
    parse_path(paths[0].attrib['d'], TransformPen(pen,(1/5.3,0,0,-1/5.3,-42.77/5.3,516)))
    return pen

def source_geometry():
    pen=OutlinePen(None);source_recording().replay(pen)
    return pen.contours,pen.closed

def source_ttf():
    pen=TTGlyphPen(None)
    source_recording().replay(ReverseContourPen(Cu2QuPen(pen,max_err=.1,all_quadratic=True)))
    return pen.glyph()

def flattened(curves):
    return [np.concatenate([s.flatten(tolerance=.005)[1][:-1] for s in contour]+[contour[-1].points[-1:]],axis=0).tolist() for contour in curves]

def geometry(font):
    curves,closed=read_outline(font,EM); findings,_=inspect_outline(curves,closed)
    return {'contours':len(curves),'closed':all(closed),
            'topology':[r for r in findings if r['kind'] in TOPOLOGY],
            'diagnostic_candidates':findings}

def unchanged_names(font):
    return sorted((r.nameID,r.platformID,r.platEncID,r.langID,r.toUnicode()) for r in font['name'].names if r.nameID not in (3,5))

def sfnt(raw):
    if raw[:4] in (b'wOF2', b'wOFF'):
        font = TTFont(io.BytesIO(raw)); font.flavor = None; font.recalcTimestamp = False
        stream = io.BytesIO(); font.save(stream); return stream.getvalue()
    return raw


def shaping_font(raw):
    font = hb.Font(hb.Face(sfnt(raw))); hb.ot_font_set_funcs(font); return font


def shape(font, text, features=None, language='ru'):
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); buf.language = language
    hb.shape(font, buf, features or {})
    return [(g.codepoint, p.x_advance, p.y_advance, p.x_offset, p.y_offset)
            for g, p in zip(buf.glyph_infos, buf.glyph_positions)]


def cases():
    words = ['мама мимо музыка память мягкий мир молоко имя земля',
             'мұра үміт әлем мың өмір мейірім', 'мн ми мт мл мш мң мү мм',
             'нм им тм лм шм ңм үм мм', 'м́ м̀ м̈ м̈́ м̄ м̆',
             'Ма́ма · мно́го · мұ́ра · е́м', 'office affine final AVATAR',
             'л л́ · аллея · т б г д п · 0123456789 ₸ ₽ №',
             '№м Ғм қм Xм Хм Kм Км Ķм']
    for word in words:
        for lang in ('ru', 'kk', 'sr', 'mk', 'en'):
            for feature in ({}, {'kern': 0}, {'liga': 0}, {'tnum': 1}, {'ss10': 1}):
                yield word, feature, lang
    for bits in itertools.product((0, 1), repeat=6):
        feature = {f'ss{i+1:02}': bit for i, bit in enumerate(bits)}
        for word in words[:6]:
            yield word, feature, 'ru'


class Vectors:
    def __init__(self, font):
        self.font = font; self.gs = font.getGlyphSet(); self.cache = {}
        self.region = pathops.Path(); pen = self.region.getPen()
        for y0, y1 in ((55, 2000), (-1000, -25)):
            pen.moveTo((-3000, y0)); pen.lineTo((5000, y0)); pen.lineTo((5000, y1)); pen.lineTo((-3000, y1)); pen.closePath()

    def path(self, name):
        if name not in self.cache:
            path = pathops.Path(); self.gs[name].draw(path.getPen(glyphSet=self.gs)); self.cache[name] = path
        return self.cache[name]

    def contact(self, left, right, advance):
        shifted = pathops.Path(); self.path(right).draw(TransformPen(shifted.getPen(), (1, 0, 0, 1, advance, 0)))
        overlap = pathops.op(self.path(left), shifted, pathops.PathOp.INTERSECTION)
        full = abs(overlap.area)
        body = abs(pathops.op(overlap, self.region, pathops.PathOp.INTERSECTION).area) if full else 0.
        return full, body


def pair_contacts(font, old):
    before, after = Vectors(old), Vectors(font)
    partners = [n for n in old.getGlyphOrder() if old['hmtx'][n][0] > 0 and old['glyf'][n].numberOfContours]
    pairs = sorted({pair for n in partners for pair in ((EM, n), (n, EM))})
    body_regressions = []; baseline_contacts = []; inherited_contacts = []; checked = 0
    for left, right in pairs:
        for kern in (False, True):
            oldadvance = old['hmtx'][left][0] + (native_kern(old, left, right) if kern else 0)
            newadvance = font['hmtx'][left][0] + (native_kern(font, left, right) if kern else 0)
            previous, oldbody = before.contact(left, right, oldadvance)
            current, newbody = after.contact(left, right, newadvance); checked += 1
            row = {'left': left, 'right': right, 'kern': kern, 'advance_before': oldadvance, 'advance_after': newadvance,
                   'old_full_area': previous, 'new_full_area': current, 'old_body_area': oldbody, 'new_body_area': newbody}
            if newbody > .1 and newbody > oldbody + .1:
                body_regressions.append(row)
            elif current > .1 and current > previous + .1:
                baseline_contacts.append(row)
            elif current > .1:
                inherited_contacts.append(row)
    return {'method': 'PathOps intersections of actual serialized outlines; all visible positive-advance glyph partners, both orders, kern on/off. Body excludes y[-25,55] where foot contacts may be intentional. New baseline-only contacts remain explicit review items.',
            'partners': len(partners), 'pairs_and_modes': checked,
            'body_collision_regressions': body_regressions, 'new_baseline_only_contacts': baseline_contacts,
            'inherited_or_reduced_contacts': inherited_contacts}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('build/release'))
    ap.add_argument('--report',type=Path,default=Path('docs/qa/author-em.json'))
    args=ap.parse_args();passed=0;failures=[];warnings=[]
    def ck(ok,label):
        nonlocal passed
        if ok: passed+=1
        else: failures.append(label)
    rawzip=ARCHIVE.read_bytes();assert sha(rawzip)==ARCHIVE_SHA,'Frozen release archive hash'
    with zipfile.ZipFile(io.BytesIO(rawzip)) as archive:
        rawbase={(style,fmt):archive.read(f'VeryPeriSerif-1.116/fonts/{"webfonts" if fmt=="woff2" else fmt}/VeryPeriSerif-{style}.{fmt}') for style,fmt in itertools.product(('Regular','Italic'),('ttf','otf','woff2'))}
    def path_for(style,fmt):
        path=args.root/f'VeryPeriSerif-{style}.{fmt}'
        if not path.exists():path=args.root/('webfonts' if fmt=='woff2' else fmt)/path.name
        return path
    paths={key:path_for(*key) for key in rawbase}
    fonts={key:TTFont(path) for key,path in paths.items()}
    baseline={key:TTFont(io.BytesIO(raw)) for key,raw in rawbase.items()}
    sourcecurves,sourceclosed=source_geometry(); sourcepoly=flattened(sourcecurves)
    sourcefindings,_=inspect_outline(sourcecurves,sourceclosed)
    ck(len(sourcecurves)==1 and all(sourceclosed),'Author SVG single closed contour')
    ck(not [r for r in sourcefindings if r['kind'] in TOPOLOGY],'Author SVG topology')
    tt=fonts['Italic','ttf'];oldtt=baseline['Italic','ttf'];expected=source_ttf();expected.recalcBounds(tt['glyf'])
    ck(expected.compile(tt['glyf'])==tt['glyf'][EM].compile(tt['glyf']),'Independent source-to-TTF conversion matches')
    ck(tt['hmtx'][EM][0]==523,'Original em advance 523')
    ck(tt['hmtx'][EM][1]==tt['glyf'][EM].xMin,'Derived em left bearing matches glyph xMin')
    testcases=list(cases())
    report={'version':VERSION,'baseline_version':'1.116','baseline_archive':str(ARCHIVE),'baseline_archive_sha256':ARCHIVE_SHA,
            'source':str(SOURCE),'source_sha256':SOURCE_SHA,'transform':[1/5.3,0,0,-1/5.3,-42.77/5.3,516],
            'source_diagnostic_candidates':sourcefindings,'fonts':{}}
    for (style,fmt),font in fonts.items():
        print('Checking',style,fmt,flush=True);base=baseline[style,fmt];path=paths[style,fmt];key=style+' '+fmt
        row={'path':str(path),'sha256':sha(path.read_bytes())};report['fonts'][key]=row
        ck(font.getGlyphOrder()==base.getGlyphOrder(),{'font':key,'glyph_order':False})
        ck(font.getBestCmap()==base.getBestCmap(),{'font':key,'cmap':False})
        ck(unchanged_names(font)==unchanged_names(base),{'font':key,'protected_name_records':False})
        ck(font['name'].getDebugName(5)=='Version '+VERSION,{'font':key,'version_name':font['name'].getDebugName(5)})
        ck(abs(font['head'].fontRevision-float(VERSION))<1/65536,{'font':key,'fontRevision':font['head'].fontRevision})
        ck(font['head'].macStyle==base['head'].macStyle,{'font':key,'style_flags':False})
        allowed={'GlyphOrder','head','name','DSIG','glyf','loca','maxp','hmtx','hhea','CFF '}
        ck(set(font.keys())==set(base.keys()),{'font':key,'table_inventory':False})
        for tag in sorted(set(base.keys())-allowed):
            ck(font.getTableData(tag)==base.getTableData(tag),{'font':key,'protected_table':tag})
        for name in base.getGlyphOrder():
            current=font['hmtx'][name];previous=base['hmtx'][name]
            ck(current==previous or (style=='Italic' and name==EM and current[0]==previous[0]),{'font':key,'protected_metrics':name})
        for attr in ('ascent','descent','lineGap','advanceWidthMax','caretSlopeRise','caretSlopeRun','caretOffset','metricDataFormat','reserved0','reserved1','reserved2','reserved3'):
            ck(getattr(font['hhea'],attr)==getattr(base['hhea'],attr),{'font':key,'protected_hhea':attr})
        if fmt in ('ttf','woff2'):
            changed=[]
            for name in base.getGlyphOrder():
                same=font['glyf'][name].compile(font['glyf'])==base['glyf'][name].compile(base['glyf'])
                if not same:changed.append(name)
                ck(same or (style=='Italic' and name==EM),{'font':key,'protected_glyph_and_hints':name})
            row['changed_glyphs']=changed;ck(changed==([EM] if style=='Italic' else []),{'font':key,'changed_glyph_set':changed})
        if fmt=='woff2':
            for tag in ('glyf','hmtx','cmap','GSUB','GPOS','GDEF','name'):
                ck(font.getTableData(tag)==fonts[style,'ttf'].getTableData(tag),{'font':key,'WOFF2_roundtrip':tag})
        if fmt=='otf':
            top=font['CFF '].cff.topDictIndex[0];cs=top.CharStrings;oldcs=base['CFF '].cff.topDictIndex[0].CharStrings;changed=[]
            for name in base.getGlyphOrder():
                cs[name].decompile();oldcs[name].decompile();same=cs[name].program==oldcs[name].program
                if not same:changed.append(name)
                ck(same or (style=='Italic' and name==EM),{'font':key,'protected_CFF_program':name})
            row['changed_charstrings']=changed;ck(changed==([EM] if style=='Italic' else []),{'font':key,'changed_CFF_set':changed})
            ck(top.version==VERSION,{'font':key,'CFF_version':top.version})
            for attr in ('FamilyName','FullName','ItalicAngle','Weight','Notice'):
                ck(getattr(top,attr)==getattr(base['CFF '].cff.topDictIndex[0],attr),{'font':key,'protected_CFF_metadata':attr})
        result=ots.sanitize(str(path),os.devnull,capture_output=True)
        row['ots_returncode']=result.returncode;ck(result.returncode==0,{'font':key,'OTS':str(result.stderr)})
        hf=shaping_font(path.read_bytes());oldhf=shaping_font(rawbase[style,fmt]);bad=[]
        for case in testcases:
            if shape(hf,*case)!=shape(oldhf,*case):bad.append({'text':case[0],'features':case[1],'language':case[2]})
        row['shaping_cases']=len(testcases);row['shaping_mismatches']=bad
        ck(not bad,{'font':key,'shaping_mismatches':bad[:12]})
        if style=='Italic':
            curves,closed=read_outline(font,EM);poly=flattened(curves)
            error=max(nearest(poly,sourcepoly),nearest(sourcepoly,poly))
            row['source_Hausdorff_error']=error;ck(error<1.,{'font':key,'source_drift_over_1u':error})
            if fmt=='otf':
                structure=[len(s.points) for c in curves for s in c];expectedstructure=[len(s.points) for c in sourcecurves for s in c]
                ck(structure==expectedstructure,{'font':key,'source_cubic_structure':structure})
                if structure==expectedstructure:
                    controlerror=max(float(np.max(np.abs(a.points-b.points))) for a,b in zip(curves[0],sourcecurves[0]))
                    row['source_cubic_control_error']=controlerror;ck(controlerror<.002,{'font':key,'source_CFF_control_error':controlerror})
            geo=geometry(font);row['geometry']=geo
            ck(geo['contours']==1 and geo['closed'],{'font':key,'closed_single_contour':False})
            ck(not geo['topology'],{'font':key,'topology':geo['topology']})
            warnings.append({'font':key,'contour_diagnostic_count':len(geo['diagnostic_candidates']),'interpretation':'Author source contains intentional corners and sub-unit shoulder/foot segments; no generic smoothing gate.'})
    print('Checking vector pair contacts',flush=True)
    contacts=pair_contacts(tt,oldtt);report['pair_contacts']=contacts
    ck(not contacts['body_collision_regressions'],{'body_collision_regressions':contacts['body_collision_regressions']})
    if contacts['new_baseline_only_contacts']:warnings.append({'new_baseline_only_contacts_need_visual_review':contacts['new_baseline_only_contacts']})
    report.update(passed=passed,failed=len(failures),failures=failures,warnings=warnings,
                  optical_status='Author-supplied design. Source fidelity and technical diagnostics do not constitute global optical acceptance.')
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':passed,'failed':len(failures),'warnings':len(warnings),'report':str(args.report)}))
    for fail in failures[:15]:print('FAIL',fail)
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
