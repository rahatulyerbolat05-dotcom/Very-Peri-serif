#!/usr/bin/env python3
"""Dry-run by default. Lossless reduction of explicitly allowlisted new static TTF glyphs."""
import argparse
import copy
import json
from pathlib import Path
import sys
from fontTools.ttLib import TTFont
from exact_nodes import reduce_glyph,canonical_outline
from font_support import sha,write_json


def point_reference_blockers(font):
    reasons=[]
    if any(tag in font for tag in ('fvar','gvar','cvar','VARC','CFF2')):reasons.append('variable data: topology/point indices require coordinated changes')
    if 'DSIG' in font and getattr(font['DSIG'],'usNumSigs',0):reasons.append('existing digital signature must not be carried onto changed font bytes')
    if any(tag.startswith('TSI') for tag in font.keys()):reasons.append('VTT source hint tables may retain point indices')
    if 'GDEF' in font:
        table=font['GDEF'].table
        if getattr(table,'AttachList',None):reasons.append('GDEF AttachList point references')
        carets=getattr(table,'LigCaretList',None)
        if carets and any(getattr(v,'Format',None)==2 for g in carets.LigGlyph for v in g.CaretValue):reasons.append('GDEF CaretValueFormat2 point references')
    if 'GPOS' in font:
        # getConverters recursively exposes all offsets/arrays, including extensions.
        seen=set()
        def walk(obj):
            if obj is None or id(obj) in seen:return
            seen.add(id(obj))
            if obj.__class__.__name__=='Anchor' and getattr(obj,'Format',None)==2:reasons.append('GPOS AnchorFormat2 point references')
            if isinstance(obj,(list,tuple)):
                for child in obj:walk(child)
            elif hasattr(obj,'__dict__'):
                for key,child in vars(obj).items():
                    if not key.startswith('_'):walk(child)
        walk(font['GPOS'].table)
    return sorted(set(reasons))


def protected_component_bases(font):
    protected=set();glyf=font['glyf']
    def descend(name,seen):
        if name in seen:return
        seen.add(name);protected.add(name);g=glyf[name]
        if g.isComposite():
            for c in g.components:descend(c.glyphName,seen)
    for name in font.getGlyphOrder():
        g=glyf[name]
        if g.isComposite() and (any(hasattr(c,'firstPt') or hasattr(c,'secondPt') for c in g.components) or (hasattr(g,'program') and g.program.getBytecode())):
            # FirstPt refers to all previously assembled components, not just one base.
            for c in g.components:descend(c.glyphName,set())
    return protected


def reduce(source,names,report_path,output=None):
    if output and Path(output).suffix.lower()!='.ttf':raise ValueError('The output is a static sfnt TrueType font; use the .ttf extension.')
    original=TTFont(source,lazy=False);font=copy.deepcopy(original)
    if 'glyf' not in font:raise ValueError('Only static TrueType glyf outlines are supported, not CFF/CFF2.')
    blockers=point_reference_blockers(font)
    if blockers:raise ValueError('; '.join(blockers))
    missing=set(names)-set(font.getGlyphOrder())
    if missing:raise ValueError('Unknown allowlisted glyphs: '+str(sorted(missing)))
    protected=protected_component_bases(font);changes={};skipped={}
    before_raw={n:original['glyf'][n].compile(original['glyf']) for n in original.getGlyphOrder()}
    for n in sorted(set(names)):
        if n in protected:skipped[n]='point-attached or hinted composite depends on this base';continue
        old=font['glyf'][n];new,stats=reduce_glyph(old,font['glyf'])
        if not stats:skipped[n]='no provably redundant points, composite, empty, flagged or hinted';continue
        font['glyf'][n]=new
        if canonical_outline(original,n)!=canonical_outline(font,n):raise AssertionError('Geometry drift: '+n)
        changes[n]={'points_before':len(old.coordinates),'points_after':len(new.coordinates),'operations':stats}
    if output:
        dest=Path(output)
        if dest.resolve()==Path(source).resolve():raise ValueError('Never overwrite the supplied source.')
        if dest.exists():raise ValueError('Choose a fresh output path; accepted artifacts are not overwritten.')
        dest.parent.mkdir(parents=True,exist_ok=True);font.flavor=None;font.recalcTimestamp=False;font.recalcBBoxes=False;font.save(dest)
        try:
            actual=TTFont(dest)
            if actual['hmtx'].metrics!=original['hmtx'].metrics:raise AssertionError('Metrics changed')
            if actual.getGlyphOrder()!=original.getGlyphOrder():raise AssertionError('Glyph order changed')
            for n in original.getGlyphOrder():
                if n in changes:
                    if canonical_outline(original,n)!=canonical_outline(actual,n):raise AssertionError('Serialized geometry drift: '+n)
                    a,b=original['glyf'][n],actual['glyf'][n]
                    if [getattr(a,k) for k in ('xMin','yMin','xMax','yMax')]!=[getattr(b,k) for k in ('xMin','yMin','xMax','yMax')]:raise AssertionError('Bounds changed: '+n)
                elif before_raw[n]!=actual['glyf'][n].compile(actual['glyf']):raise AssertionError('Unlisted glyph/hints changed: '+n)
                # Also resolves inherited geometry in every component.
                if canonical_outline(original,n)!=canonical_outline(actual,n):raise AssertionError('Path drift: '+n)
            for t in original.keys():
                if t not in ('GlyphOrder','head','glyf','loca','maxp') and original.getTableData(t)!=actual.getTableData(t):raise AssertionError('Unexpected table change: '+t)
        except BaseException:
            dest.unlink(missing_ok=True);raise
    result={'input':str(source),'input_sha256':sha(source),'output':str(output) if output else None,
            'output_sha256':sha(output) if output else None,'mode':'applied_and_serialized_checked' if output else 'dry_run',
            'scope':'Caller must allowlist only authored/unprotected glyphs; no approximation or smoothing.',
            'changes':changes,'skipped':skipped,'points_removed':sum(v['points_before']-v['points_after'] for v in changes.values())}
    write_json(report_path,result);return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('font',type=Path);ap.add_argument('--glyph-list',type=Path,required=True,help='JSON array of glyph names; caller must select only new/authored glyphs');ap.add_argument('--report',type=Path,required=True);ap.add_argument('--output',type=Path,help='Apply to a fresh TTF path; absent = dry run');args=ap.parse_args()
    try:
        names=json.loads(args.glyph_list.read_text())
        if not isinstance(names,list) or not all(isinstance(n,str) for n in names):raise ValueError('glyph-list must be a JSON array of names')
        r=reduce(args.font,names,args.report,args.output)
    except ValueError as e:ap.error(str(e))
    print(json.dumps({'mode':r['mode'],'glyphs_changed':len(r['changes']),'points_removed':r['points_removed'],'report':str(args.report)}))


if __name__=='__main__':main()
